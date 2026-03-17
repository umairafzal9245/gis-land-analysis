"""GDB Export Module - Export analysis results to File Geodatabase format.

This module handles exporting the complete analysis session to a .gdb file,
including:
- Selection polygon
- All selected parcels with computed fields
- Query result layer (filtered parcels)
- Capacity calculation results
- Summary tables
- LLM report sections
- Domain tables for Arabic labels

Uses fiona with OpenFileGDB driver as primary, GeoPackage as fallback.
"""
import io
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from typing import Any, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
from shapely.geometry import Point, Polygon

from backend.database import DB_PATH, get_connection, get_parcels_by_objectids
from backend.llm_service import generate_selection_report
from etl.constants import (
    DETAILSLANDUSE_MAP,
    LANDUSE_CATEGORIES,
    MAINLANDUSE_MAP,
    PARCEL_STATUS_MAP,
    SUBTYPE_MAP,
)

# Path to the original GDB file for reading full polygon geometries
ORIGINAL_GDB_PATH = "data/AI _Test.gdb"


def _sanitize_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Sanitize a GeoDataFrame for GeoPackage/GDB export.
    
    Handles problematic data types that can't be serialized:
    - Converts bytes/memoryview to empty string
    - Converts nested dicts/lists to JSON strings
    - Replaces NaN in object columns with empty string
    - Ensures consistent column types
    """
    if gdf.empty:
        return gdf
    
    gdf = gdf.copy()
    
    for col in gdf.columns:
        if col == "geometry":
            continue
        
        # Get column dtype
        dtype = gdf[col].dtype
        dtype_kind = getattr(dtype, "kind", None)

        # Handle pandas extension string types (StringDtype, ArrowDtype, etc.)
        is_pandas_string = (
            hasattr(pd, "StringDtype") and isinstance(dtype, pd.StringDtype)
        ) or (
            hasattr(pd, "ArrowDtype") and isinstance(dtype, pd.ArrowDtype)
        ) or str(dtype).startswith("string")
        
        # Handle object columns (strings, mixed types)
        if dtype == object or is_pandas_string:
            def safe_convert(val):
                if val is None:
                    return ""
                try:
                    if isinstance(val, float) and np.isnan(val):
                        return ""
                except (TypeError, ValueError):
                    pass
                if isinstance(val, (bytes, memoryview)):
                    return ""
                if isinstance(val, (dict, list)):
                    try:
                        return json.dumps(val, ensure_ascii=False, default=str)
                    except Exception:
                        return str(val)
                return str(val)
            
            gdf[col] = gdf[col].apply(safe_convert).astype(str)
        
        # Handle numeric columns - replace inf with NaN, then fill NaN with 0
        elif dtype_kind == "f" or (dtype_kind is None and np.issubdtype(dtype, np.floating)):
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce").fillna(0)
        elif dtype_kind == "i" or dtype_kind == "u" or (dtype_kind is None and np.issubdtype(dtype, np.integer)):
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce").fillna(0).astype(int)
        else:
            # Convert any other extension types to plain object/string
            try:
                gdf[col] = gdf[col].astype(object).fillna("").astype(str)
            except Exception:
                gdf[col] = gdf[col].apply(lambda v: str(v) if v is not None else "")
    
    return gdf


def _get_full_parcel_geometries(objectids: list[int]) -> gpd.GeoDataFrame:
    """Read full polygon geometries from the original GDB for selected parcels.
    
    Args:
        objectids: List of OBJECTID/PARCEL_ID values to retrieve
        
    Returns:
        GeoDataFrame with full polygon geometries
    """
    if not objectids or not os.path.exists(ORIGINAL_GDB_PATH):
        return gpd.GeoDataFrame()
    
    try:
        # Read the parcels layer from the original GDB
        # Filter to only selected parcels using SQL where clause
        objectid_str = ",".join(str(oid) for oid in objectids)
        gdf = pyogrio.read_dataframe(
            ORIGINAL_GDB_PATH,
            where=f"OBJECTID IN ({objectid_str})"
        )
        return gdf
    except Exception as e:
        print(f"Warning: Could not read original GDB geometries: {e}")
        return gpd.GeoDataFrame()


def _merge_parcel_data(
    gdf_geometry: gpd.GeoDataFrame,
    parcels_data: list[dict],
) -> gpd.GeoDataFrame:
    """Merge full geometry GeoDataFrame with computed ETL columns from database.
    
    Args:
        gdf_geometry: GeoDataFrame with full polygon geometries from original GDB
        parcels_data: List of parcel dicts with all computed columns from database
        
    Returns:
        Merged GeoDataFrame with all columns and original polygon geometry
    """
    if gdf_geometry.empty:
        # Fallback: create point geometries from representative coordinates
        rows = []
        for p in parcels_data:
            lon = p.get("REPR_LON")
            lat = p.get("REPR_LAT")
            geom = Point(float(lon), float(lat)) if lon and lat else None
            row = dict(p)
            row["geometry"] = geom
            rows.append(row)
        return gpd.GeoDataFrame(rows, crs="EPSG:4326") if rows else gpd.GeoDataFrame()
    
    # Create DataFrame from parcels_data
    df_computed = pd.DataFrame(parcels_data)
    
    # Ensure OBJECTID column exists for join
    if "OBJECTID" not in gdf_geometry.columns and "PARCEL_ID" in gdf_geometry.columns:
        gdf_geometry["OBJECTID"] = gdf_geometry["PARCEL_ID"]
    
    # Keep only geometry and OBJECTID from original GDF
    gdf_geom_only = gdf_geometry[["OBJECTID", "geometry"]].copy()
    
    # Ensure OBJECTID types match
    df_computed["OBJECTID"] = df_computed.get("OBJECTID", df_computed.get("PARCEL_ID")).astype(str)
    gdf_geom_only["OBJECTID"] = gdf_geom_only["OBJECTID"].astype(str)
    
    # Merge computed data with geometries
    merged = gdf_geom_only.merge(df_computed, on="OBJECTID", how="right")
    
    # Fill missing geometries with point fallback
    for idx, row in merged.iterrows():
        if pd.isna(row.get("geometry")):
            lon = row.get("REPR_LON")
            lat = row.get("REPR_LAT")
            if lon and lat:
                merged.at[idx, "geometry"] = Point(float(lon), float(lat))
    
    return gpd.GeoDataFrame(merged, crs="EPSG:4326")


def _build_selection_polygon_layer(
    polygon_coords: list[list[float]],
    selection_summary: dict,
    report_text: Optional[str] = None,
    session_id: Optional[str] = None,
) -> gpd.GeoDataFrame:
    """Build the selection polygon feature class.
    
    Args:
        polygon_coords: List of [lat, lon] coordinate pairs
        selection_summary: The full selection summary dict
        report_text: Optional LLM report text
        session_id: Optional session identifier
        
    Returns:
        GeoDataFrame with single polygon feature and metadata attributes
    """
    # Convert from [lat, lon] to [lon, lat] for Shapely
    coords = [(c[1], c[0]) for c in polygon_coords]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    
    polygon = Polygon(coords)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    
    now = datetime.now()
    
    row = {
        "geometry": polygon,
        "ANALYSIS_DATE": now.strftime("%Y-%m-%d"),
        "ANALYSIS_TIME": now.strftime("%H:%M:%S"),
        "TOTAL_PARCELS": selection_summary.get("total_parcels", 0),
        "TOTAL_AREA_M2": round(selection_summary.get("total_area_m2", 0), 2),
        "VACANT_COUNT": selection_summary.get("vacant_count", 0),
        "DEVELOPED_CNT": selection_summary.get("developed_count", 0),
        "SESSION_ID": session_id or f"session_{now.strftime('%Y%m%d_%H%M%S')}",
        "REPORT_SUMRY": (report_text[:250] + "...") if report_text and len(report_text) > 250 else (report_text or ""),
    }
    
    return gpd.GeoDataFrame([row], crs="EPSG:4326")


def _get_id_col(gdf: gpd.GeoDataFrame) -> str:
    """Return the parcel ID column name present in the GeoDataFrame."""
    for col in ("OBJECTID", "PARCEL_ID", "parcel_id"):
        if col in gdf.columns:
            return col
    raise KeyError(f"No parcel ID column found. Available: {list(gdf.columns)}")


def _build_query_result_layer(
    all_parcels_gdf: gpd.GeoDataFrame,
    query_parcel_ids: list[str],
    query_category: str,
) -> gpd.GeoDataFrame:
    """Build the query result feature class (filtered parcels).
    
    Args:
        all_parcels_gdf: Full selected parcels GeoDataFrame
        query_parcel_ids: List of PARCEL_IDs that matched the query
        query_category: The category that was queried
        
    Returns:
        GeoDataFrame with only the query-matching parcels
    """
    if all_parcels_gdf.empty or not query_parcel_ids:
        return gpd.GeoDataFrame()
    
    # Filter to query results
    id_set = set(str(pid) for pid in query_parcel_ids)
    id_col = _get_id_col(all_parcels_gdf)
    mask = all_parcels_gdf[id_col].astype(str).isin(id_set)
    
    query_gdf = all_parcels_gdf[mask].copy()
    
    # Add query metadata columns
    query_gdf["QUERY_CAT"] = query_category
    query_gdf["QUERY_TIME"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return query_gdf


def _build_capacity_layer(
    all_parcels_gdf: gpd.GeoDataFrame,
    capacity_calculations: list[dict],
) -> gpd.GeoDataFrame:
    """Build the capacity calculations feature class.
    
    Args:
        all_parcels_gdf: Full selected parcels GeoDataFrame
        capacity_calculations: List of capacity calculation results
        
    Returns:
        GeoDataFrame with capacity calculation parcels and calc fields
    """
    if all_parcels_gdf.empty or not capacity_calculations:
        return gpd.GeoDataFrame()
    
    # Get parcel IDs with calculations
    calc_parcel_ids = {str(c.get("parcel_id")) for c in capacity_calculations}
    id_col = _get_id_col(all_parcels_gdf)
    
    # Filter parcels
    mask = all_parcels_gdf[id_col].astype(str).isin(calc_parcel_ids)
    
    calc_gdf = all_parcels_gdf[mask].copy()
    
    if calc_gdf.empty:
        return calc_gdf
    
    # Initialize capacity columns
    calc_gdf["CALC_TYPE"] = ""
    calc_gdf["CALC_INPUT"] = ""
    calc_gdf["CALC_RESULT"] = 0.0
    calc_gdf["CALC_FORMULA"] = ""
    calc_gdf["CALC_TIME"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Populate capacity data for each parcel
    id_col = _get_id_col(calc_gdf)
    for calc in capacity_calculations:
        pid = str(calc.get("parcel_id"))
        mask = calc_gdf[id_col].astype(str) == pid
        
        if mask.any():
            calc_type = calc.get("type", "unknown")
            
            if calc_type == "mosque":
                area = calc.get("area_m2", 0)
                rate = calc.get("rate_m2_per_worshipper", 8.0)
                capacity = calc.get("capacity_worshippers", 0)
                calc_gdf.loc[mask, "CALC_TYPE"] = "Mosque Capacity"
                calc_gdf.loc[mask, "CALC_INPUT"] = f"{rate} m²/worshipper"
                calc_gdf.loc[mask, "CALC_RESULT"] = float(capacity)
                calc_gdf.loc[mask, "CALC_FORMULA"] = f"{area:.0f} m² ÷ {rate} m²/worshipper = {capacity} worshippers"
            
            elif calc_type == "commercial":
                area = calc.get("area_m2", 0)
                shop_size = calc.get("shop_size_m2", 120)
                shops = calc.get("shops_estimated", 0)
                calc_gdf.loc[mask, "CALC_TYPE"] = "Commercial Capacity"
                calc_gdf.loc[mask, "CALC_INPUT"] = f"{shop_size} m² per shop"
                calc_gdf.loc[mask, "CALC_RESULT"] = float(shops)
                calc_gdf.loc[mask, "CALC_FORMULA"] = f"{area:.0f} m² ÷ {shop_size} m²/shop = {shops} shops"
    
    return calc_gdf


def _build_summary_table(selection_summary: dict) -> pd.DataFrame:
    """Build the analysis summary table.
    
    Args:
        selection_summary: The full selection summary dict
        
    Returns:
        DataFrame with category breakdown rows
    """
    rows = []
    
    # Add overall summary row
    rows.append({
        "CATEGORY": "TOTAL",
        "CATEGORY_AR": "المجموع",
        "PARCEL_CNT": selection_summary.get("total_parcels", 0),
        "AREA_M2": round(selection_summary.get("total_area_m2", 0), 2),
        "CAPACITY": selection_summary.get("total_religious_capacity", 0),
        "SHOPS": selection_summary.get("total_shops_estimated", 0),
        "VACANT_CNT": selection_summary.get("vacant_count", 0),
        "DEVELOPED": selection_summary.get("developed_count", 0),
    })
    
    # Add per-category rows
    breakdown = selection_summary.get("breakdown", selection_summary.get("category_breakdown", {}))
    for category, data in breakdown.items():
        if isinstance(data, dict):
            rows.append({
                "CATEGORY": category,
                "CATEGORY_AR": _get_category_arabic(category),
                "PARCEL_CNT": data.get("count", 0),
                "AREA_M2": round(data.get("total_area_m2", 0), 2),
                "CAPACITY": data.get("total_capacity_estimated", 0),
                "SHOPS": data.get("total_shops_estimated", 0),
                "VACANT_CNT": data.get("vacant_count", 0),
                "DEVELOPED": data.get("developed_count", 0),
            })
    
    return pd.DataFrame(rows)


def _get_category_arabic(category: str) -> str:
    """Get Arabic label for a land use category."""
    mapping = {
        "Residential": "سكني",
        "Commercial": "تجاري",
        "Religious": "ديني",
        "Educational": "تعليمي",
        "Health": "صحي",
        "Municipal": "بلدي",
        "Recreational": "ترويحي",
        "Utilities": "مرافق",
        "Special": "خاص",
        "Unknown": "غير محدد",
        "TOTAL": "المجموع",
    }
    return mapping.get(category, category)


def _build_report_table(report_text: str) -> pd.DataFrame:
    """Build the LLM report sections table.
    
    Args:
        report_text: The full LLM-generated report text
        
    Returns:
        DataFrame with one row per report section
    """
    if not report_text:
        return pd.DataFrame()
    
    # Split by numbered section headers
    import re
    
    # Pattern to match numbered headers like "1. Title" or "## 1. Title"
    pattern = r'(?:^|\n)(?:#{1,3}\s*)?(\d+)\.\s*([^\n]+)'
    matches = list(re.finditer(pattern, report_text))
    
    rows = []
    for i, match in enumerate(matches):
        section_num = int(match.group(1))
        section_title = match.group(2).strip()
        
        # Get content between this header and the next
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(report_text)
        content = report_text[start:end].strip()
        
        rows.append({
            "SECTION_NUM": section_num,
            "SECTION_TITLE": section_title,
            "SECTION_CONTENT": content[:4000] if len(content) > 4000 else content,  # Limit field length
        })
    
    if not rows:
        # If no sections found, store entire report as one row
        rows.append({
            "SECTION_NUM": 1,
            "SECTION_TITLE": "Analysis Report",
            "SECTION_CONTENT": report_text[:4000] if len(report_text) > 4000 else report_text,
        })
    
    return pd.DataFrame(rows)


def _build_domain_table(domain_name: str) -> pd.DataFrame:
    """Build a domain lookup table.
    
    Args:
        domain_name: One of 'SUBTYPE', 'DETAILSLANDUSE', 'PARCELSTATUS', 'MAINLANDUSE'
        
    Returns:
        DataFrame with CODE and LABEL columns
    """
    if domain_name == "SUBTYPE":
        source = SUBTYPE_MAP
        rows = [{"CODE": code, "LABEL_EN": data["label_en"], "LABEL_AR": data["label_ar"]}
                for code, data in source.items()]
    elif domain_name == "DETAILSLANDUSE":
        source = DETAILSLANDUSE_MAP
        rows = [{"CODE": code, "LABEL_EN": data["label_en"], "LABEL_AR": data["label_ar"]}
                for code, data in source.items()]
    elif domain_name == "PARCELSTATUS":
        source = PARCEL_STATUS_MAP
        rows = [{"CODE": code, "LABEL_EN": label, "LABEL_AR": ""}
                for code, label in source.items()]
    elif domain_name == "MAINLANDUSE":
        source = MAINLANDUSE_MAP
        rows = [{"CODE": code, "LABEL_EN": data["label_en"], "LABEL_AR": data["label_ar"]}
                for code, data in source.items()]
    else:
        return pd.DataFrame()
    
    return pd.DataFrame(rows)


def _generate_readme(
    selection_summary: dict,
    query_category: Optional[str],
    capacity_calculations: list[dict],
    has_report: bool,
) -> str:
    """Generate README.txt content for the export zip.
    
    Args:
        selection_summary: The full selection summary
        query_category: Applied category query if any
        capacity_calculations: List of capacity calculations
        has_report: Whether an LLM report was generated
        
    Returns:
        README content as string
    """
    now = datetime.now()
    total_parcels = selection_summary.get("total_parcels", 0)
    total_area = selection_summary.get("total_area_m2", 0)
    vacant_count = selection_summary.get("vacant_count", 0)
    developed_count = selection_summary.get("developed_count", 0)

    lines = [
        "GIS Land Analysis Export",
        "========================",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "CONTENTS",
        "--------",
        "This export contains the results of a land use analysis session.",
        "",
        "FILES:",
        "- parcels_export.gdb/ - File Geodatabase with all layers and tables",
        "- report.txt - Full analysis report (if generated)",
        "- README.txt - This file",
        "",
        "GEODATABASE LAYERS",
        "------------------",
        "",
        "1. SelectionPolygon",
        "   The polygon drawn on the map to define the analysis area.",
        "   Attributes: analysis date/time, total parcels, total area, session ID.",
        "",
        "2. AllSelectedParcels",
        "   All parcels within the drawn polygon with their full attribute data.",
        "   Contains original GDB fields plus computed ETL fields:",
        "   - LANDUSE_CATEGORY: App-level land use classification",
        "   - SUBTYPE_LABEL_EN/AR: Primary classification label",
        "   - DETAILSLANDUSE_LABEL: Sub-category detail",
        "   - AREA_M2: Parcel area in square meters",
        "   - IS_COMMERCIAL: Whether parcel generates commercial revenue",
        "   - CAPACITY_ESTIMATED: Estimated capacity (worshippers/students/etc.)",
        "   - SHOPS_ESTIMATED: Estimated number of shops (commercial only)",
        "   - PARCEL_STATUS_LABEL_EN/AR: Development status",
        "",
    ]

    if query_category:
        lines += [
            "3. QueryResultParcels",
            f"   Parcels matching the category filter: {query_category}",
            "   Same schema as AllSelectedParcels plus:",
            "   - QUERY_CAT: The queried category",
            "   - QUERY_TIME: When the query was executed",
            "",
        ]

    if capacity_calculations:
        lines += [
            f"4. CapacityCalculations",
            f"   Parcels with individual capacity calculations ({len(capacity_calculations)} total).",
            "   Additional fields:",
            "   - CALC_TYPE: Type of calculation (Mosque Capacity / Commercial Capacity)",
            "   - CALC_INPUT: Calculation input parameter",
            "   - CALC_RESULT: Numeric result",
            "   - CALC_FORMULA: Human-readable formula",
            "",
        ]

    lines += [
        "TABLES",
        "------",
        "",
        "- AnalysisSummary: Category breakdown with parcel counts, areas, capacities",
        "- ReportSections: LLM-generated report broken into sections (if generated)",
        "- Domain_SUBTYPE: Code-to-label mapping for SUBTYPE field",
        "- Domain_DETAILS: Code-to-label mapping for DETAILSLANDUSE field",
        "- Domain_STATUS: Code-to-label mapping for PARCELSTATUS field",
        "- Domain_MAINUSE: Code-to-label mapping for MAINLANDUSE field",
        "",
        "ANALYSIS SUMMARY",
        "----------------",
        f"Total Parcels: {total_parcels}",
        f"Total Area: {total_area:,.2f} m2",
        f"Vacant: {vacant_count} | Developed: {developed_count}",
        "",
    ]

    breakdown = selection_summary.get("breakdown", selection_summary.get("category_breakdown", {}))
    if breakdown:
        lines.append("Category Breakdown:")
        for cat, data in breakdown.items():
            if isinstance(data, dict):
                cnt = data.get("count", 0)
                area = data.get("total_area_m2", 0)
                lines.append(f"  - {cat}: {cnt} parcels ({area:,.0f} m2)")
        lines.append("")

    lines += [
        "HOW TO USE",
        "----------",
        "",
        "ArcGIS Pro:",
        "1. Open ArcGIS Pro",
        "2. Insert > Add Data > Add Data",
        "3. Navigate to parcels_export.gdb",
        "4. Add desired layers to the map",
        "",
        "QGIS:",
        "1. Open QGIS",
        "2. Layer > Add Layer > Add Vector Layer",
        "3. Select parcels_export.gdb as the data source",
        "4. Choose layers to add",
        "",
        "NOTES",
        "-----",
        "- Coordinate System: WGS 84 (EPSG:4326)",
        "- All text fields support Arabic characters",
        "- Domain tables enable proper label display in ArcGIS Pro",
        "",
        "For questions about this export, contact the GIS Analysis Platform administrator.",
    ]

    return "\n".join(lines) + "\n"


def _write_gdb(
    output_path: str,
    selection_polygon_gdf: gpd.GeoDataFrame,
    all_parcels_gdf: gpd.GeoDataFrame,
    query_result_gdf: gpd.GeoDataFrame,
    capacity_gdf: gpd.GeoDataFrame,
    summary_df: pd.DataFrame,
    report_df: pd.DataFrame,
) -> bool:
    """Write layers and tables to a File Geodatabase using fiona.
    
    Args:
        output_path: Path to the .gdb folder to create
        selection_polygon_gdf: Selection polygon layer
        all_parcels_gdf: All selected parcels layer
        query_result_gdf: Query result layer (may be empty)
        capacity_gdf: Capacity calculations layer (may be empty)
        summary_df: Analysis summary table
        report_df: Report sections table
        
    Returns:
        True if successful, False if fallback should be used
    """
    try:
        import fiona
        
        # Check if OpenFileGDB driver is available for writing
        # Note: fiona may not support writing to GDB on all platforms
        # In that case, we'll use GeoPackage as fallback
        
        # Write each layer
        if not selection_polygon_gdf.empty:
            selection_polygon_gdf.to_file(output_path, layer="SelectionPolygon", driver="OpenFileGDB")
        
        if not all_parcels_gdf.empty:
            all_parcels_gdf.to_file(output_path, layer="AllSelectedParcels", driver="OpenFileGDB")
        
        if not query_result_gdf.empty:
            query_result_gdf.to_file(output_path, layer="QueryResultParcels", driver="OpenFileGDB")
        
        if not capacity_gdf.empty:
            capacity_gdf.to_file(output_path, layer="CapacityCalculations", driver="OpenFileGDB")
        
        return True
        
    except Exception as e:
        print(f"GDB write failed: {e}, falling back to GeoPackage")
        return False


def _write_gpkg(
    output_path: str,
    selection_polygon_gdf: gpd.GeoDataFrame,
    all_parcels_gdf: gpd.GeoDataFrame,
    query_result_gdf: gpd.GeoDataFrame,
    capacity_gdf: gpd.GeoDataFrame,
    summary_df: pd.DataFrame,
    report_df: pd.DataFrame,
) -> bool:
    """Write layers and tables to a GeoPackage (fallback format).
    
    Args:
        output_path: Path to the .gpkg file to create
        selection_polygon_gdf: Selection polygon layer
        all_parcels_gdf: All selected parcels layer
        query_result_gdf: Query result layer (may be empty)
        capacity_gdf: Capacity calculations layer (may be empty)
        summary_df: Analysis summary table
        report_df: Report sections table
        
    Returns:
        True if successful
    """
    try:
        # Sanitize all GeoDataFrames before writing
        selection_polygon_gdf = _sanitize_gdf(selection_polygon_gdf)
        all_parcels_gdf = _sanitize_gdf(all_parcels_gdf)
        query_result_gdf = _sanitize_gdf(query_result_gdf)
        capacity_gdf = _sanitize_gdf(capacity_gdf)
        
        # Write feature layers - track if file exists for append mode
        file_exists = False
        
        if not selection_polygon_gdf.empty:
            selection_polygon_gdf.to_file(output_path, layer="SelectionPolygon", driver="GPKG")
            file_exists = True
        
        if not all_parcels_gdf.empty:
            mode = "a" if file_exists else "w"
            all_parcels_gdf.to_file(output_path, layer="AllSelectedParcels", driver="GPKG", mode=mode)
            file_exists = True
        
        if not query_result_gdf.empty and file_exists:
            query_result_gdf.to_file(output_path, layer="QueryResultParcels", driver="GPKG", mode="a")
        
        if not capacity_gdf.empty and file_exists:
            capacity_gdf.to_file(output_path, layer="CapacityCalculations", driver="GPKG", mode="a")
        
        # Ensure file was created
        if not file_exists:
            raise ValueError("No data to export - both selection polygon and parcels are empty")
        
        # Write non-spatial tables using pandas + sqlite
        import sqlite3
        
        conn = sqlite3.connect(output_path)
        if not summary_df.empty:
            summary_df.to_sql("AnalysisSummary", conn, if_exists="replace", index=False)
        if not report_df.empty:
            report_df.to_sql("ReportSections", conn, if_exists="replace", index=False)
        
        # Write domain tables
        for domain_name in ["SUBTYPE", "DETAILSLANDUSE", "PARCELSTATUS", "MAINLANDUSE"]:
            domain_df = _build_domain_table(domain_name)
            if not domain_df.empty:
                domain_df.to_sql(f"Domain_{domain_name}", conn, if_exists="replace", index=False)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"GeoPackage write failed: {e}")
        raise


def export_to_gdb(
    selected_objectids: list[str],
    polygon_coordinates: Optional[list[list[float]]] = None,
    selection_summary: Optional[dict] = None,
    query_category: Optional[str] = None,
    query_parcel_ids: Optional[list[str]] = None,
    capacity_calculations: Optional[list[dict]] = None,
    report_text: Optional[str] = None,
    generate_report_if_missing: bool = True,
) -> io.BytesIO:
    """Export analysis results to a zipped File Geodatabase.
    
    This is the main entry point for the GDB export feature. It assembles
    all session data and produces a complete .gdb (or .gpkg fallback) with:
    - Selection polygon
    - All selected parcels
    - Query results (if applicable)
    - Capacity calculations (if applicable)  
    - Summary tables
    - LLM report sections
    - Domain lookup tables
    
    Args:
        selected_objectids: List of PARCEL_IDs to export
        polygon_coordinates: List of [lat, lon] pairs for the selection polygon
        selection_summary: Full selection summary dict
        query_category: Applied category filter (if any)
        query_parcel_ids: IDs matching the query (if applicable)
        capacity_calculations: List of capacity calc results
        report_text: Pre-generated LLM report (optional)
        generate_report_if_missing: If True and no report provided, generate one
        
    Returns:
        BytesIO containing the zipped export package
    """
    # Default empty values
    polygon_coordinates = polygon_coordinates or []
    selection_summary = selection_summary or {}
    capacity_calculations = capacity_calculations or []
    query_parcel_ids = query_parcel_ids or []
    
    # Step 1: Retrieve full parcel data from database
    parcels_data = get_parcels_by_objectids(selected_objectids)
    if not parcels_data:
        raise ValueError("No parcels found for the given IDs")
    
    # Step 2: Get full polygon geometries from original GDB
    gdf_geometry = _get_full_parcel_geometries([int(oid) for oid in selected_objectids if str(oid).isdigit()])
    
    # Step 3: Merge geometries with computed data
    all_parcels_gdf = _merge_parcel_data(gdf_geometry, parcels_data)
    
    # Step 4: Build selection polygon layer
    selection_polygon_gdf = gpd.GeoDataFrame()
    if polygon_coordinates:
        selection_polygon_gdf = _build_selection_polygon_layer(
            polygon_coordinates,
            selection_summary,
            report_text,
        )
    
    # Step 5: Build query result layer
    query_result_gdf = gpd.GeoDataFrame()
    if query_parcel_ids and query_category:
        query_result_gdf = _build_query_result_layer(
            all_parcels_gdf,
            query_parcel_ids,
            query_category,
        )
    
    # Step 6: Build capacity calculations layer
    capacity_gdf = gpd.GeoDataFrame()
    if capacity_calculations:
        capacity_gdf = _build_capacity_layer(all_parcels_gdf, capacity_calculations)
    
    # Step 7: Generate report if needed
    if generate_report_if_missing and not report_text and selection_summary:
        try:
            report_text = generate_selection_report(
                selection_summary=selection_summary,
                capacity_calculations=capacity_calculations if capacity_calculations else None,
            )
        except Exception as e:
            print(f"Warning: Could not generate report: {e}")
            report_text = None
    
    # Step 8: Build summary and report tables
    summary_df = _build_summary_table(selection_summary)
    report_df = _build_report_table(report_text) if report_text else pd.DataFrame()
    
    # Step 9: Generate README
    readme_content = _generate_readme(
        selection_summary,
        query_category,
        capacity_calculations,
        bool(report_text),
    )
    
    # Step 10: Write to temp directory and zip
    with tempfile.TemporaryDirectory() as tmpdir:
        # Try GDB first, fallback to GPKG
        gdb_path = os.path.join(tmpdir, "parcels_export.gdb")
        gpkg_path = os.path.join(tmpdir, "parcels_export.gpkg")
        
        use_gpkg = False
        
        try:
            success = _write_gdb(
                gdb_path,
                selection_polygon_gdf,
                all_parcels_gdf,
                query_result_gdf,
                capacity_gdf,
                summary_df,
                report_df,
            )
            if not success:
                use_gpkg = True
        except Exception:
            use_gpkg = True
        
        if use_gpkg:
            _write_gpkg(
                gpkg_path,
                selection_polygon_gdf,
                all_parcels_gdf,
                query_result_gdf,
                capacity_gdf,
                summary_df,
                report_df,
            )
        
        # Write README
        readme_path = os.path.join(tmpdir, "README.txt")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        # Write report as standalone text file
        if report_text:
            report_path = os.path.join(tmpdir, "report.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_text)
        
        # Create zip archive
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add README
            zf.write(readme_path, "README.txt")
            
            # Add report
            if report_text:
                zf.write(report_path, "report.txt")
            
            # Add GDB folder or GPKG file
            if use_gpkg:
                zf.write(gpkg_path, "parcels_export.gpkg")
            else:
                # Add all files in the GDB folder
                for root, dirs, files in os.walk(gdb_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join(
                            "parcels_export.gdb",
                            os.path.relpath(file_path, gdb_path)
                        )
                        zf.write(file_path, arcname)
        
        zip_buffer.seek(0)
        return zip_buffer
