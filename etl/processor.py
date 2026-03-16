"""ETL Processor - SUBTYPE-based classification pipeline.

This processor uses SUBTYPE as the single source of truth for all parcel
classification, category assignment, and capacity rate calculations.
"""

import sqlite3
import warnings
import os

import pandas as pd
import geopandas as gpd
import pyogrio
import dotenv

from etl.constants import SUBTYPE_MAP, PARCEL_STATUS_MAP, METRIC_CRS, QUERYABLE_CATEGORIES

dotenv.load_dotenv()
DB_PATH = os.getenv("SQLITE_DB_PATH", "data/gis_database.db")
GDB_PATH = os.getenv("GDB_PATH", "data/AI _Test.gdb")


def auto_detect_layer(gdb_path: str) -> str:
    """Finds the most likely parcel/boundary layer in the GDB."""
    layers = pyogrio.list_layers(gdb_path)
    print(f"Available layers: {[l[0] for l in layers]}")

    for layer in layers:
        name = layer[0]
        if "parcel" in name.lower() or "boundary" in name.lower():
            return name

    if layers:
        return layers[0][0]
    raise ValueError("No layers found in the Geodatabase.")


def classify_by_subtype(subtype_val) -> dict:
    """Look up SUBTYPE in SUBTYPE_MAP to get classification data."""
    if pd.isnull(subtype_val):
        subtype_val = 0

    try:
        subtype_key = int(float(subtype_val))
    except (ValueError, TypeError):
        subtype_key = 0

    if subtype_key in SUBTYPE_MAP:
        return SUBTYPE_MAP[subtype_key]

    # Fallback for unknown codes
    return {
        "label_en": f"Unknown ({subtype_key})",
        "label_ar": f"غير معروف ({subtype_key})",
        "LANDUSE_CATEGORY": "Unknown",
        "IS_COMMERCIAL": False,
        "CAPACITY_RATE": 0,
        "CAPACITY_UNIT": "",
    }


def get_parcel_status_label(status_val) -> str:
    """Map PARCELSTATUS code to label."""
    if pd.isnull(status_val):
        return "Unknown"

    try:
        status_key = int(float(status_val))
    except (ValueError, TypeError):
        return "Unknown"

    return PARCEL_STATUS_MAP.get(status_key, "Unknown")


def process_data():
    """Main ETL pipeline following the SUBTYPE-based classification approach."""
    print(f"[ETL] Connecting to Geodatabase: {GDB_PATH}")
    if not os.path.exists(GDB_PATH):
        raise FileNotFoundError(f"Database not found: {GDB_PATH}")

    # Read the data using pyogrio
    layer_name = auto_detect_layer(GDB_PATH)
    print(f"[ETL] Using layer: {layer_name}")

    gdf = gpd.read_file(GDB_PATH, layer=layer_name, engine="pyogrio")
    print(f"[ETL] Loaded {len(gdf)} parcels with {len(gdf.columns)} columns")

    # =========================================================================
    # Step 1 — Geometry reprojection
    # Reproject from EPSG:4326 to EPSG:32637 and compute area in m²
    # =========================================================================
    print(f"[ETL] Step 1: Reprojecting to {METRIC_CRS} and computing area...")
    gdf_metric = gdf.to_crs(METRIC_CRS)
    gdf["AREA_M2"] = gdf_metric.geometry.area

    # =========================================================================
    # Step 2 — Compute representative point (NOT centroid)
    # representative_point() is guaranteed to fall inside the polygon.
    # Reproject to WGS84 first so REPR_LON/REPR_LAT are always in degrees
    # (longitude, latitude) regardless of the source CRS. Without this, a
    # UTM/metric source CRS would store easting/northing in metres, breaking
    # all geographic point-in-polygon queries at query time.
    # =========================================================================
    print("[ETL] Step 2: Computing representative points in WGS84...")
    gdf_wgs84 = gdf.to_crs('EPSG:4326')
    rep_points = gdf_wgs84.geometry.representative_point()
    gdf["REPR_LON"] = rep_points.x  # longitude (degrees)
    gdf["REPR_LAT"] = rep_points.y  # latitude  (degrees)

    # =========================================================================
    # Step 3 — SUBTYPE-based classification
    # SUBTYPE is the single source of truth for all classification
    # =========================================================================
    print("[ETL] Step 3: Classifying parcels by SUBTYPE...")
    if "SUBTYPE" not in gdf.columns:
        raise ValueError("SUBTYPE column not found in the dataset")

    classifications = gdf["SUBTYPE"].apply(classify_by_subtype)

    gdf["LANDUSE_CATEGORY"] = classifications.apply(lambda x: x["LANDUSE_CATEGORY"])
    gdf["IS_COMMERCIAL"] = classifications.apply(lambda x: x["IS_COMMERCIAL"])
    gdf["CAPACITY_RATE"] = classifications.apply(lambda x: x["CAPACITY_RATE"])
    gdf["SUBTYPE_LABEL_EN"] = classifications.apply(lambda x: x["label_en"])
    gdf["SUBTYPE_LABEL_AR"] = classifications.apply(lambda x: x["label_ar"])

    # =========================================================================
    # Step 4 — Development status
    # Map PARCELSTATUS through PARCEL_STATUS_MAP
    # =========================================================================
    print("[ETL] Step 4: Mapping parcel status...")
    if "PARCELSTATUS" in gdf.columns:
        gdf["PARCEL_STATUS_LABEL"] = gdf["PARCELSTATUS"].apply(get_parcel_status_label)
    else:
        gdf["PARCEL_STATUS_LABEL"] = "Unknown"

    # =========================================================================
    # Step 5 — Capacity estimation
    # CAPACITY_ESTIMATED = AREA_M2 / CAPACITY_RATE (where rate > 0)
    # SHOPS_ESTIMATED = AREA_M2 / 120 for commercial, use COMMERCIALUNITS if present
    # =========================================================================
    print("[ETL] Step 5: Estimating capacities...")

    # Capacity estimation: only where CAPACITY_RATE > 0
    gdf["CAPACITY_ESTIMATED"] = 0.0
    valid_rate_mask = gdf["CAPACITY_RATE"] > 0
    gdf.loc[valid_rate_mask, "CAPACITY_ESTIMATED"] = (
        gdf.loc[valid_rate_mask, "AREA_M2"] / gdf.loc[valid_rate_mask, "CAPACITY_RATE"]
    )
    gdf["CAPACITY_ESTIMATED"] = gdf["CAPACITY_ESTIMATED"].fillna(0).astype(int)

    # Shops estimation: AREA_M2 / 120 for commercial parcels
    gdf["SHOPS_ESTIMATED"] = 0
    commercial_mask = gdf["IS_COMMERCIAL"] == True
    gdf.loc[commercial_mask, "SHOPS_ESTIMATED"] = (
        gdf.loc[commercial_mask, "AREA_M2"] / 120
    ).fillna(0).astype(int)

    # Override SHOPS_ESTIMATED with actual COMMERCIALUNITS if available
    if "COMMERCIALUNITS" in gdf.columns:
        valid_units = pd.to_numeric(gdf["COMMERCIALUNITS"], errors="coerce").fillna(0)
        has_units = valid_units > 0
        gdf.loc[has_units, "SHOPS_ESTIMATED"] = valid_units[has_units].astype(int)

    # =========================================================================
    # Step 6 — Build the block summary
    # Group by BLOCK_ID and compute aggregated statistics
    # =========================================================================
    print("[ETL] Step 6: Building block summary...")

    if "BLOCK_ID" not in gdf.columns:
        gdf["BLOCK_ID"] = "Unknown"

    # Create helper columns for aggregation
    gdf["_VACANT"] = (gdf["PARCEL_STATUS_LABEL"] == "Vacant").astype(int)
    gdf["_DEVELOPED"] = (gdf["PARCEL_STATUS_LABEL"] == "Developed").astype(int)
    gdf["_MOSQUE_CAPACITY"] = gdf.apply(
        lambda r: r["CAPACITY_ESTIMATED"] if r["LANDUSE_CATEGORY"] == "Mosque" else 0,
        axis=1
    )

    # Category counts for each category
    category_pivot = pd.crosstab(gdf["BLOCK_ID"], gdf["LANDUSE_CATEGORY"])

    # Ensure all queryable categories exist
    for cat in QUERYABLE_CATEGORIES + ["Unknown"]:
        if cat not in category_pivot.columns:
            category_pivot[cat] = 0

    category_pivot = category_pivot.rename(columns={
        "Mosque": "mosque_count",
        "Commercial": "commercial_count",
        "Residential": "residential_count",
        "Park": "park_count",
        "Educational": "educational_count",
        "Government": "government_count",
        "Unknown": "unknown_count",
    })

    block_summary = gdf.groupby("BLOCK_ID").agg(
        total_parcels=("BLOCK_ID", "count"),
        total_area_m2=("AREA_M2", "sum"),
        vacant_count=("_VACANT", "sum"),
        developed_count=("_DEVELOPED", "sum"),
        total_mosque_capacity=("_MOSQUE_CAPACITY", "sum"),
        total_shops_estimated=("SHOPS_ESTIMATED", "sum"),
    ).reset_index()

    # Merge category counts
    block_summary = block_summary.merge(
        category_pivot.reset_index(),
        on="BLOCK_ID",
        how="left"
    )

    # Fill NaN counts with 0
    count_cols = ["mosque_count", "commercial_count", "residential_count",
                  "park_count", "educational_count", "government_count", "unknown_count"]
    for col in count_cols:
        if col in block_summary.columns:
            block_summary[col] = block_summary[col].fillna(0).astype(int)

    # =========================================================================
    # Step 7 — Build the searchable index
    # Lightweight table for fast queries
    # =========================================================================
    print("[ETL] Step 7: Building parcel search index...")

    # Determine the best ID column available
    id_col = None
    for candidate in ["OBJECTID", "PARCEL_ID", "GLOBALID"]:
        if candidate in gdf.columns:
            id_col = candidate
            break
    if id_col is None:
        gdf["PARCEL_ID"] = range(1, len(gdf) + 1)
        id_col = "PARCEL_ID"

    search_columns = [
        id_col,
        "LANDUSE_CATEGORY",
        "SUBTYPE_LABEL_EN",
        "REPR_LAT",
        "REPR_LON",
        "BLOCK_ID",
        "AREA_M2",
        "CAPACITY_ESTIMATED",
        "SHOPS_ESTIMATED",
        "IS_COMMERCIAL",
        "PARCEL_STATUS_LABEL",
    ]

    parcel_search_index = gdf[search_columns].copy()
    parcel_search_index = parcel_search_index.rename(columns={id_col: "PARCEL_ID"})

    # =========================================================================
    # Write to SQLite Database
    # =========================================================================
    print(f"[ETL] Writing to SQLite: {DB_PATH}")

    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    # Prepare parcels table (drop geometry and helper columns)
    drop_cols = ["geometry", "_VACANT", "_DEVELOPED", "_MOSQUE_CAPACITY"]
    df_parcels = gdf.drop(columns=[c for c in drop_cols if c in gdf.columns], errors="ignore")

    # Convert object columns to string for SQLite compatibility
    for col in df_parcels.select_dtypes(include=["object", "string"]).columns:
        df_parcels[col] = df_parcels[col].astype(str)

    df_parcels.to_sql("parcels", conn, if_exists="replace", index=False)
    print(f"[ETL] ✓ parcels table: {len(df_parcels)} rows")

    block_summary.to_sql("block_summary", conn, if_exists="replace", index=False)
    print(f"[ETL] ✓ block_summary table: {len(block_summary)} rows")

    parcel_search_index.to_sql("parcel_search_index", conn, if_exists="replace", index=False)
    print(f"[ETL] ✓ parcel_search_index table: {len(parcel_search_index)} rows")

    # Create indices for faster queries
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_category ON parcel_search_index(LANDUSE_CATEGORY)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_block ON parcel_search_index(BLOCK_ID)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_commercial ON parcel_search_index(IS_COMMERCIAL)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_parcel ON parcel_search_index(PARCEL_ID)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_parcels_block ON parcels(BLOCK_ID)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_parcels_parcel ON parcels(PARCEL_ID)")
    conn.commit()
    print("[ETL] ✓ Indices created")

    conn.close()

    print(f"[ETL] Done. Database -> {DB_PATH}")
    return df_parcels, block_summary, parcel_search_index


if __name__ == "__main__":
    process_data()
