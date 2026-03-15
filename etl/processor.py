import sqlite3
import pandas as pd
import geopandas as gpd
import pyogrio
import os
import dotenv

from etl.constants import (
    DETAILSLANDUSE_MAP, 
    SUBTYPE_MAP, 
    MAINLANDUSE_MAP, 
    PARCEL_STATUS_MAP, 
    METRIC_CRS
)

dotenv.load_dotenv()
DB_PATH = os.getenv("SQLITE_DB_PATH", "data/gis_database.db")
GDB_PATH = os.getenv("DB_PATH", "data/AI _Test.gdb")

def auto_detect_layer(layers):
    """Finds the most likely parcel/boundary layer, or returns the first polygonal one."""
    for layer in layers:
        name = layer[0]
        # Favor layers with parcel or boundary in the name
        if "parcel" in name.lower() or "boundary" in name.lower():
            return name
        
    # Fallback to the first layer if no match is found
    if layers:
        return layers[0][0]
    raise ValueError("No layers found in the Geodatabase.")

def get_dynamic_category(val):
    """If a code is not in constants.py, auto-classify based on its starting digit."""
    if pd.isnull(val):
        return ["Unknown", 1.0, "Unknown", "غير معروف"]
    
    # Check constants map first
    constants_map = {float(k): v for k, v in DETAILSLANDUSE_MAP.items()}
    item = constants_map.get(float(val))
    if item:
        return [item["category"], item["capacity_rate"], item["label_en"], item["label_ar"]]
    
    # Dynamic logic for new datasets loaded on the fly
    val_str = str(int(val))
    if val_str.startswith('100') or val_str.startswith('4'):
        return ["Commercial", 120, f"Commercial {val_str}", f"تجاري {val_str}"]
    elif val_str.startswith('101'):
        return ["Residential", 10, f"Residential {val_str}", f"سكني {val_str}"]
    elif val_str.startswith('301'):
        return ["Mosque", 8, f"Mosque {val_str}", f"مسجد {val_str}"]
    elif val_str.startswith('303') or val_str.startswith('304'):
        return ["Educational", 6, f"Educational {val_str}", f"تعليمي {val_str}"]
    elif val_str.startswith('306'):
        return ["Park", 15, f"Park {val_str}", f"حديقة {val_str}"]
    elif val_str.startswith('2'):
        return ["Industrial", 50, f"Industrial {val_str}", f"صناعي {val_str}"]
    
    return ["Unknown", 1.0, f"Code {val_str}", f"رمز {val_str}"]

def get_dynamic_subtype(val):
    if pd.isnull(val):
        return ["Unknown", "غير معروف"]
    constants_map = {float(k): v for k, v in SUBTYPE_MAP.items()}
    item = constants_map.get(float(val))
    if item:
        return [item["label_en"], item["label_ar"]]
    return [f"Type {int(val)}", f"النوع {int(val)}"]

def get_dynamic_mainland(val):
    if pd.isnull(val):
        return "Unknown"
    constants_map = {float(k): v for k, v in MAINLANDUSE_MAP.items()}
    item = constants_map.get(float(val))
    if item:
        return item["label_en"]
    return f"Category {int(val)}"

def process_data():
    print(f"Connecting to Geodatabase: {GDB_PATH} ...")
    if not os.path.exists(GDB_PATH):
        print(f"Error: Database {GDB_PATH} not found.")
        return

    # 1. Fetch Layers Dynamically at runtime
    layers = pyogrio.list_layers(GDB_PATH)
    print("Available layers detected:", [l[0] for l in layers])

    layer_name = auto_detect_layer(layers)
    print(f"Auto-selected working layer: {layer_name}")
    
    gdf = gpd.read_file(GDB_PATH, layer=layer_name)
    print(f"Loaded {len(gdf)} parcels dynamically.")

    # 2. Geometry reprojection to Metric (EPSG:32637)
    print(f"Reprojecting geometry to {METRIC_CRS} and calculating precise Area (M2)...")
    gdf_metric = gdf.to_crs(METRIC_CRS)
    gdf["AREA_M2"] = gdf_metric.geometry.area
    
    # Safely compute centroid (ignoring CRS warning since we just want coordinates)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rep_points = gdf.geometry.representative_point()
        gdf["REPR_LON"] = rep_points.x
        gdf["REPR_LAT"] = rep_points.y

    # 3. Apply Dynamic Three-Column Classification on the fly
    print("Applying dynamic standard classifications...")
    
    if "DETAILSLANDUSE" in gdf.columns:
        gdf[["LANDUSE_CATEGORY", "CAPACITY_RATE", "DETAIL_LABEL_EN", "DETAIL_LABEL_AR"]] = \
            pd.DataFrame(gdf["DETAILSLANDUSE"].apply(get_dynamic_category).tolist(), index=gdf.index)
    else:
        print("Warning: DETAILSLANDUSE column missing. Using fallback values.")
        gdf[["LANDUSE_CATEGORY", "CAPACITY_RATE", "DETAIL_LABEL_EN", "DETAIL_LABEL_AR"]] = ["Unknown", 1.0, "Unknown", "غير معروف"]

    if "SUBTYPE" in gdf.columns:
        gdf[["SUBTYPE_LABEL_EN", "SUBTYPE_LABEL_AR"]] = \
            pd.DataFrame(gdf["SUBTYPE"].apply(get_dynamic_subtype).tolist(), index=gdf.index)
    else:
        gdf[["SUBTYPE_LABEL_EN", "SUBTYPE_LABEL_AR"]] = ["Unknown", "غير معروف"]

    if "MAINLANDUSE" in gdf.columns:
        gdf["MAINLANDUSE_LABEL_EN"] = gdf["MAINLANDUSE"].apply(get_dynamic_mainland)
    else:
        gdf["MAINLANDUSE_LABEL_EN"] = "Unknown"

    if "PARCELSTATUS" in gdf.columns:
        status_map = {float(k): v for k, v in PARCEL_STATUS_MAP.items()}
        gdf["PARCEL_STATUS_LABEL"] = gdf["PARCELSTATUS"].apply(
            lambda val: status_map.get(float(val), "Unknown") if pd.notnull(val) else "Unknown"
        )
    else:
        gdf["PARCEL_STATUS_LABEL"] = "Unknown"

    # 4. Capacity and unit estimation
    print("Calculating intelligent estimates (Capacities/Shops)...")
    capped_rate = gdf["CAPACITY_RATE"].replace(0, 1)
    gdf["CAPACITY_ESTIMATED"] = (gdf["AREA_M2"] / capped_rate).fillna(0).astype(int)
    
    gdf["SHOPS_ESTIMATED"] = 0
    mask_commercial = gdf["LANDUSE_CATEGORY"] == "Commercial"
    gdf.loc[mask_commercial, "SHOPS_ESTIMATED"] = (gdf.loc[mask_commercial, "AREA_M2"] / 120).fillna(0).astype(int)

    # 5. Overrides
    for col, estimated_col in [("RESIDENTIALUNITS", "CAPACITY_ESTIMATED"), ("COMMERCIALUNITS", "SHOPS_ESTIMATED")]:
        if col in gdf.columns:
            valid = pd.to_numeric(gdf[col], errors='coerce').fillna(0) > 0
            gdf.loc[valid, estimated_col] = pd.to_numeric(gdf.loc[valid, col], errors='coerce')

    # 6. Building block summary robustly
    print("Building aggregated Block Summary...")
    if "BLOCK_ID" not in gdf.columns: gdf["BLOCK_ID"] = "Unknown"
    if "SUBDIVISIONPLAN_ID" not in gdf.columns: gdf["SUBDIVISIONPLAN_ID"] = "Unknown"

    gdf["IS_VACANT"] = (gdf["PARCEL_STATUS_LABEL"] == "Vacant").astype(int)
    gdf["IS_DEVELOPED"] = (gdf["PARCEL_STATUS_LABEL"] == "Developed").astype(int)
    gdf["IS_MOSQUE"] = (gdf["LANDUSE_CATEGORY"] == "Mosque").astype(int)
    gdf["MOSQUE_CAPACITY"] = gdf["CAPACITY_ESTIMATED"] * gdf["IS_MOSQUE"]

    dominant_plan = gdf.groupby("BLOCK_ID")["SUBDIVISIONPLAN_ID"].apply(
        lambda x: x.mode().iloc[0] if not x.mode().empty else "Unknown"
    ).reset_index()

    cat_counts = pd.crosstab(gdf["BLOCK_ID"], gdf["LANDUSE_CATEGORY"], dropna=False).add_prefix("CAT_")
    main_counts = pd.crosstab(gdf["BLOCK_ID"], gdf["MAINLANDUSE_LABEL_EN"], dropna=False).add_prefix("MAIN_")

    block_summary = gdf.groupby("BLOCK_ID").agg(
        TOTAL_PARCELS=("BLOCK_ID", "count"),
        TOTAL_AREA_M2=("AREA_M2", "sum"),
        VACANT_COUNT=("IS_VACANT", "sum"),
        DEVELOPED_COUNT=("IS_DEVELOPED", "sum"),
        TOTAL_MOSQUE_CAPACITY=("MOSQUE_CAPACITY", "sum"),
        TOTAL_SHOPS=("SHOPS_ESTIMATED", "sum"),
    )

    block_summary = block_summary.join(cat_counts).join(main_counts).reset_index()
    block_summary = block_summary.merge(dominant_plan, on="BLOCK_ID", how="left")

    # 7. Write to robust SQLite Database
    print(f"Dumping records to Local SQLite: {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    
    drop_cols = ["geometry", "IS_VACANT", "IS_DEVELOPED", "IS_MOSQUE", "MOSQUE_CAPACITY"]
    df_parcels = pd.DataFrame(gdf.drop(columns=[c for c in drop_cols if c in gdf.columns], errors="ignore"))
    
    for col in df_parcels.select_dtypes(include=['object', 'string', 'str']):
        df_parcels[col] = df_parcels[col].astype(str)

    df_parcels.to_sql("parcels", conn, if_exists="replace", index=False)
    print("[ETL] parcels")
    block_summary.to_sql("block_summary", conn, if_exists="replace", index=False)
    print("[ETL] block_summary")
    
    # Process extra layers dynamically
    for layer in layers:
        layer_name_clean = layer[0]
        if layer_name_clean != layer_name:
            try:
                extra_df = gpd.read_file(GDB_PATH, layer=layer_name_clean)
                extra_df = pd.DataFrame(extra_df.drop(columns=["geometry"], errors="ignore"))
                for col in extra_df.select_dtypes(include=['object', 'string', 'str']):
                    extra_df[col] = extra_df[col].astype(str)
                table_name = layer_name_clean.lower()
                extra_df.to_sql(table_name, conn, if_exists="replace", index=False)
                print(f"[ETL] {table_name}")
            except Exception as e:
                pass # Usually skips silently if layer reading fails

    conn.close()
    
    print(f"[ETL] Done. Database -> {DB_PATH}")

if __name__ == "__main__":
    process_data()
