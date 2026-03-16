"""Spatial analysis, polygon selection, and query engine.

This module handles three core responsibilities:
1. Polygon/bbox selection with two-step algorithm (bbox pre-filter + point-in-polygon)
2. Category-based query filtering within selections
3. Individual parcel capacity calculations (mosque, commercial)
"""
import math
import sqlite3
from typing import Optional

from shapely.geometry import Point, Polygon

from backend.database import (
    DB_PATH,
    get_connection,
    get_parcels_in_bbox,
    get_parcels_by_objectids,
    search_parcels_by_category,
)


# =============================================================================
# Responsibility 1: Polygon and Bounding Box Selection
# =============================================================================


def select_parcels_in_polygon(
    vertices: list[list[float]],
    db_path: str = DB_PATH
) -> dict:
    """Select parcels within a polygon using two-step algorithm.
    
    Algorithm:
    1. Build Shapely Polygon from vertices (lat/lon order)
    2. Bbox pre-filter: get parcels from parcel_search_index within bounds
    3. Point-in-polygon: test each candidate's representative point
    4. Compute complete selection summary
    
    Args:
        vertices: List of [lat, lon] coordinate pairs forming the polygon.
                  The polygon is automatically closed if needed.
        db_path: Path to the SQLite database.
        
    Returns:
        Selection summary with selected_objectids, counts, areas, and breakdowns.
    """
    if len(vertices) < 3:
        return _empty_selection_summary()
    
    # Step 1: Build Shapely Polygon from vertices
    # Convert from [lat, lon] to [lon, lat] for Shapely (x=lon, y=lat)
    coords = [(v[1], v[0]) for v in vertices]
    
    # Close polygon if not already closed
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    
    polygon = Polygon(coords)
    if not polygon.is_valid:
        # Try to fix invalid polygon
        polygon = polygon.buffer(0)
    
    # Step 2: Bbox pre-filter
    min_lon, min_lat, max_lon, max_lat = polygon.bounds
    
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM parcel_search_index
            WHERE REPR_LAT >= ? AND REPR_LAT <= ?
              AND REPR_LON >= ? AND REPR_LON <= ?
            """,
            (min_lat, max_lat, min_lon, max_lon)
        ).fetchall()
        candidates = [dict(row) for row in rows]
    
    # Step 3: Point-in-polygon test
    matching_parcels = []
    for parcel in candidates:
        lat = parcel.get("REPR_LAT")
        lon = parcel.get("REPR_LON")
        if lat is not None and lon is not None:
            point = Point(lon, lat)  # Shapely uses (x=lon, y=lat)
            # Use covers() not contains(): covers() returns True when the point lies
            # on the polygon boundary, so parcels on the edge are correctly included.
            if polygon.covers(point):
                matching_parcels.append(parcel)
    
    # Step 4: Compute selection summary
    return _build_selection_summary(matching_parcels)


def select_parcels_in_bbox(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    db_path: str = DB_PATH
) -> dict:
    """Select parcels within a bounding box.
    
    Args:
        min_lat: Minimum latitude
        max_lat: Maximum latitude  
        min_lon: Minimum longitude
        max_lon: Maximum longitude
        
    Returns:
        Selection summary with selected_objectids, counts, areas, and breakdowns.
    """
    parcels = get_parcels_in_bbox(min_lat, max_lat, min_lon, max_lon, db_path)
    return _build_selection_summary(parcels)


def _build_selection_summary(parcels: list[dict]) -> dict:
    """Build complete selection summary from matching parcels.
    
    Returns:
        Dictionary containing:
        - selected_objectids: list of all matching PARCEL_IDs
        - total_parcels: integer count
        - total_area_m2: float sum
        - breakdown: dict by LANDUSE_CATEGORY with count, area, capacity, shops
        - vacant_count, developed_count
        - commercial_total_area_m2, non_commercial_total_area_m2
        - total_religious_capacity, total_shops_estimated
        - block_ids_covered: unique BLOCK_IDs
    """
    if not parcels:
        return _empty_selection_summary()
    
    selected_objectids = []
    total_area_m2 = 0.0
    vacant_count = 0
    developed_count = 0
    commercial_total_area_m2 = 0.0
    non_commercial_total_area_m2 = 0.0
    total_religious_capacity = 0
    total_shops_estimated = 0
    block_ids = set()
    
    # Category breakdown structure
    breakdown = {}
    
    for p in parcels:
        # Collect OBJECTID/PARCEL_ID
        parcel_id = p.get("PARCEL_ID") or p.get("OBJECTID")
        if parcel_id is not None:
            selected_objectids.append(parcel_id)
        
        # Sum areas
        area = float(p.get("AREA_M2") or 0.0)
        total_area_m2 += area
        
        # Track development status
        status = str(p.get("PARCEL_STATUS_LABEL") or "").lower()
        if "vacant" in status:
            vacant_count += 1
        elif "developed" in status:
            developed_count += 1
        
        # Track commercial vs non-commercial
        is_commercial = p.get("IS_COMMERCIAL")
        if is_commercial == 1 or is_commercial == True or str(is_commercial).lower() == "true":
            commercial_total_area_m2 += area
        else:
            non_commercial_total_area_m2 += area
        
        # Aggregate capacity estimates
        capacity = int(p.get("CAPACITY_ESTIMATED") or 0)
        shops = int(p.get("SHOPS_ESTIMATED") or 0)
        
        # Track by category
        category = p.get("LANDUSE_CATEGORY") or "Unknown"
        if category not in breakdown:
            breakdown[category] = {
                "count": 0,
                "total_area_m2": 0.0,
                "total_capacity_estimated": 0,
                "total_shops_estimated": 0,
            }
        breakdown[category]["count"] += 1
        breakdown[category]["total_area_m2"] += area
        breakdown[category]["total_capacity_estimated"] += capacity
        breakdown[category]["total_shops_estimated"] += shops
        
        # Category-specific totals
        if category == "Religious":
            total_religious_capacity += capacity
        if is_commercial == 1 or is_commercial == True or str(is_commercial).lower() == "true":
            total_shops_estimated += shops
        
        # Track blocks
        block_id = p.get("BLOCK_ID")
        if block_id and str(block_id) != "Unknown":
            block_ids.add(str(block_id))
    
    return {
        "selected_objectids": selected_objectids,
        "total_parcels": len(parcels),
        "total_area_m2": round(total_area_m2, 2),
        "breakdown": breakdown,
        "category_breakdown": {cat: info["count"] for cat, info in breakdown.items()},
        "vacant_count": vacant_count,
        "developed_count": developed_count,
        "commercial_total_area_m2": round(commercial_total_area_m2, 2),
        "non_commercial_total_area_m2": round(non_commercial_total_area_m2, 2),
        "total_religious_capacity": total_religious_capacity,
        "total_shops_estimated": total_shops_estimated,
        "block_ids_covered": sorted(list(block_ids)),
        "parcels": parcels,
    }


def _empty_selection_summary() -> dict:
    """Return an empty selection summary structure."""
    return {
        "selected_objectids": [],
        "total_parcels": 0,
        "total_area_m2": 0.0,
        "breakdown": {},
        "category_breakdown": {},
        "vacant_count": 0,
        "developed_count": 0,
        "commercial_total_area_m2": 0.0,
        "non_commercial_total_area_m2": 0.0,
        "total_religious_capacity": 0,
        "total_shops_estimated": 0,
        "block_ids_covered": [],
        "parcels": [],
    }


# =============================================================================
# Responsibility 2: Category Query Engine
# =============================================================================


def query_parcels_in_selection(
    category: str,
    selected_objectids: list[int],
    db_path: str = DB_PATH
) -> list[dict]:
    """Query parcels by category within a selection.
    
    Filters parcel_search_index to return only rows where:
    - PARCEL_ID is in selected_objectids
    - LANDUSE_CATEGORY matches the requested category
    
    Args:
        category: LANDUSE_CATEGORY to filter by (e.g., "Mosque", "Commercial")
        selected_objectids: List of PARCEL_IDs from current polygon selection
        
    Returns:
        List of matching parcel objects with display fields.
    """
    if not selected_objectids:
        return []
    
    # Use the database function to get filtered results
    matching = search_parcels_by_category(category, selected_objectids, db_path)
    
    # Return the relevant fields for frontend display
    result = []
    for p in matching:
        result.append({
            "PARCEL_ID": p.get("PARCEL_ID"),
            "REPR_LAT": p.get("REPR_LAT"),
            "REPR_LON": p.get("REPR_LON"),
            "AREA_M2": p.get("AREA_M2"),
            "CAPACITY_ESTIMATED": p.get("CAPACITY_ESTIMATED"),
            "SHOPS_ESTIMATED": p.get("SHOPS_ESTIMATED"),
            "SUBTYPE_LABEL_EN": p.get("SUBTYPE_LABEL_EN"),
            "PARCEL_STATUS_LABEL": p.get("PARCEL_STATUS_LABEL"),
            "BLOCK_ID": p.get("BLOCK_ID"),
            "IS_COMMERCIAL": p.get("IS_COMMERCIAL"),
        })
    
    return result


# =============================================================================
# Responsibility 3: Individual Parcel Capacity Calculations
# =============================================================================


def calculate_mosque_capacity(
    objectid: int,
    db_path: str = DB_PATH
) -> dict:
    """Calculate mosque capacity for a specific parcel.
    
    Computes capacity at 8 m²/worshipper rate.
    
    Args:
        objectid: PARCEL_ID/OBJECTID of the mosque parcel
        
    Returns:
        Dictionary with area, capacity, formula, and development status.
    """
    parcels = get_parcels_by_objectids([objectid], db_path)
    
    if not parcels:
        return {
            "error": f"Parcel {objectid} not found",
            "PARCEL_ID": objectid,
            "AREA_M2": 0,
            "capacity_worshippers": 0,
            "formula": "",
            "parcel_status": "Unknown",
        }
    
    parcel = parcels[0]
    area_m2 = float(parcel.get("AREA_M2") or 0)
    rate = 8.0  # m² per worshipper
    
    capacity = int(area_m2 / rate) if rate > 0 else 0
    
    # Format numbers with commas for readability
    area_formatted = f"{area_m2:,.0f}"
    capacity_formatted = f"{capacity:,}"
    
    formula = f"Area: {area_formatted} m² ÷ {rate:.0f} m² per worshipper = {capacity_formatted} worshippers"
    
    # Determine development status
    status = parcel.get("PARCEL_STATUS_LABEL") or parcel.get("PARCEL_STATUS_LABEL_EN") or "Unknown"
    
    return {
        "PARCEL_ID": objectid,
        "AREA_M2": round(area_m2, 2),
        "capacity_worshippers": capacity,
        "rate_m2_per_worshipper": rate,
        "formula": formula,
        "parcel_status": status,
        "is_vacant": "vacant" in str(status).lower(),
        "is_developed": "developed" in str(status).lower(),
    }


def calculate_commercial_capacity(
    objectid: int,
    shop_size_m2: float = 120.0,
    db_path: str = DB_PATH
) -> dict:
    """Calculate commercial capacity for a specific parcel.
    
    Computes number of shops as floor(AREA_M2 / shop_size_m2).
    
    Args:
        objectid: PARCEL_ID/OBJECTID of the commercial parcel
        shop_size_m2: Size per shop in m² (user-provided, default 120)
        
    Returns:
        Dictionary with area, shop count, formula, and suggestions.
    """
    parcels = get_parcels_by_objectids([objectid], db_path)
    
    if not parcels:
        return {
            "error": f"Parcel {objectid} not found",
            "PARCEL_ID": objectid,
            "AREA_M2": 0,
            "shop_count": 0,
            "formula": "",
            "parcel_status": "Unknown",
            "default_shop_size_m2": 120.0,
        }
    
    parcel = parcels[0]
    area_m2 = float(parcel.get("AREA_M2") or 0)
    
    # Ensure valid shop size
    if shop_size_m2 <= 0:
        shop_size_m2 = 120.0
    
    shop_count = math.floor(area_m2 / shop_size_m2)
    
    # Format numbers for readability
    area_formatted = f"{area_m2:,.0f}"
    shop_size_formatted = f"{shop_size_m2:,.0f}"
    
    formula = f"Area: {area_formatted} m² ÷ {shop_size_formatted} m² per shop = {shop_count:,} shops"
    
    # Determine development status
    status = parcel.get("PARCEL_STATUS_LABEL") or parcel.get("PARCEL_STATUS_LABEL_EN") or "Unknown"
    
    return {
        "PARCEL_ID": objectid,
        "AREA_M2": round(area_m2, 2),
        "shop_count": shop_count,
        "shop_size_m2": shop_size_m2,
        "default_shop_size_m2": 120.0,
        "formula": formula,
        "parcel_status": status,
        "is_reasonable_size": 20 <= shop_size_m2 <= area_m2,
    }


# =============================================================================
# Legacy Functions (backward compatibility)
# =============================================================================


def build_summary_stats(
    parcels: list[dict],
    shop_size_m2: float = 120.0,
    mosque_space_m2: float = 8.0
) -> dict:
    """Build summary statistics from a list of parcels (legacy function)."""
    if not parcels:
        return {
            "total_parcels": 0,
            "total_area_m2": 0.0,
            "vacant_count": 0,
            "developed_count": 0,
            "mosque_count": 0,
            "mosque_total_area_m2": 0.0,
            "mosque_capacity_estimate": 0,
            "park_count": 0,
            "park_total_area_m2": 0.0,
            "residential_count": 0,
            "residential_total_area_m2": 0.0,
            "commercial_count": 0,
            "commercial_total_area_m2": 0.0,
            "shops_estimate": 0,
            "government_count": 0,
            "educational_count": 0,
            "breakdown_by_category": {},
            "landuse_category": {},
            "mainlanduse_label": {},
            "subtypes_counts": {},
            "subtypes": [],
            "overlapping_block_ids": [],
            "shop_size_m2": shop_size_m2,
            "mosque_space_m2": mosque_space_m2
        }
        
    total_area_m2 = 0.0
    vacant_count = 0
    developed_count = 0
    mosque_count = 0
    mosque_total_area_m2 = 0.0
    park_count = 0
    park_total_area_m2 = 0.0
    residential_count = 0
    residential_total_area_m2 = 0.0
    commercial_count = 0
    commercial_total_area_m2 = 0.0
    government_count = 0
    educational_count = 0
    
    breakdown_by_category = {}
    landuse_cat_counts = {}
    mainlanduse_counts = {}
    subtype_counts = {}
    subtypes = set()
    block_ids = set()
    
    for p in parcels:
        area = float(p.get("AREA_M2") or 0.0)
        total_area_m2 += area
        
        luc = p.get("LANDUSE_CATEGORY") or "Unknown"
        landuse_cat_counts[luc] = landuse_cat_counts.get(luc, 0) + 1
        
        if luc not in breakdown_by_category:
            breakdown_by_category[luc] = {"count": 0, "total_area_m2": 0.0}
        breakdown_by_category[luc]["count"] += 1
        breakdown_by_category[luc]["total_area_m2"] += area
        
        mlu = p.get("MAINLANDUSE_LABEL_EN") or "Unknown"
        mainlanduse_counts[mlu] = mainlanduse_counts.get(mlu, 0) + 1
        
        status = p.get("PARCEL_STATUS_LABEL") or p.get("PARCEL_STATUS_LABEL_EN") or "Unknown"
        if "vacant" in status.lower() or str(p.get("PARCELSTATUS")) == "0":
            vacant_count += 1
        elif "developed" in status.lower() or str(p.get("PARCELSTATUS")) == "2":
            developed_count += 1
            
        if luc == "Mosque":
            mosque_count += 1
            mosque_total_area_m2 += area
        elif luc == "Park":
            park_count += 1
            park_total_area_m2 += area
        elif luc == "Commercial":
            commercial_count += 1
            commercial_total_area_m2 += area
        elif luc == "Residential":
            residential_count += 1
            residential_total_area_m2 += area
        elif luc == "Government":
            government_count += 1
        elif luc == "Educational":
            educational_count += 1
            
        subtype = p.get("SUBTYPE_LABEL_EN")
        if subtype and subtype != "Unknown":
            subtypes.add(subtype)
            subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1
            
        block_id = p.get("BLOCK_ID")
        if block_id and str(block_id) != "Unknown":
            block_ids.add(str(block_id))
            
    mosque_capacity_estimate = int(mosque_total_area_m2 / mosque_space_m2) if mosque_space_m2 > 0 else 0
    shops_estimate = int(commercial_total_area_m2 / shop_size_m2) if shop_size_m2 > 0 else 0
            
    return {
        "total_parcels": len(parcels),
        "total_area_m2": round(total_area_m2, 2),
        "vacant_count": vacant_count,
        "developed_count": developed_count,
        "mosque_count": mosque_count,
        "mosque_total_area_m2": round(mosque_total_area_m2, 2),
        "mosque_capacity_estimate": mosque_capacity_estimate,
        "park_count": park_count,
        "park_total_area_m2": round(park_total_area_m2, 2),
        "residential_count": residential_count,
        "residential_total_area_m2": round(residential_total_area_m2, 2),
        "commercial_count": commercial_count,
        "commercial_total_area_m2": round(commercial_total_area_m2, 2),
        "shops_estimate": shops_estimate,
        "government_count": government_count,
        "educational_count": educational_count,
        "breakdown_by_category": breakdown_by_category,
        "landuse_category": landuse_cat_counts,
        "mainlanduse_label": mainlanduse_counts,
        "subtypes_counts": subtype_counts,
        "subtypes": sorted(list(subtypes)),
        "overlapping_block_ids": sorted(list(block_ids)),
        "shop_size_m2": shop_size_m2,
        "mosque_space_m2": mosque_space_m2
    }


def analyze_bbox(
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    shop_size_m2: float = 120.0,
    mosque_space_m2: float = 8.0
) -> dict:
    """Analyze parcels in a bounding box (legacy function)."""
    parcels = get_parcels_in_bbox(min_y, max_y, min_x, max_x)
    return build_summary_stats(parcels, shop_size_m2, mosque_space_m2)


def analyze_polygon(
    polygon_geojson: dict,
    shop_size_m2: float = 120.0,
    mosque_space_m2: float = 8.0
) -> dict:
    """Analyze parcels in a GeoJSON polygon (legacy function)."""
    from backend.database import get_parcels_in_polygon
    parcels = get_parcels_in_polygon(polygon_geojson)
    return build_summary_stats(parcels, shop_size_m2, mosque_space_m2)


def analyze_parcel_set(
    parcels: list[dict],
    shop_size_m2: float = 120.0,
    mosque_space_m2: float = 8.0
) -> dict:
    """Analyze a set of parcels (legacy function)."""
    return build_summary_stats(parcels, shop_size_m2, mosque_space_m2)
