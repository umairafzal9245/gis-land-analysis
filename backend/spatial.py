"""Spatial and bounding box analysis helpers."""
from backend.database import get_parcels_in_bbox, get_parcels_in_polygon

def build_summary_stats(parcels: list[dict], shop_size_m2: float = 120.0, mosque_space_m2: float = 8.0) -> dict:
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
        
        # update breakdown
        if luc not in breakdown_by_category:
            breakdown_by_category[luc] = {"count": 0, "total_area_m2": 0.0}
        breakdown_by_category[luc]["count"] += 1
        breakdown_by_category[luc]["total_area_m2"] += area
        
        mlu = p.get("MAINLANDUSE_LABEL_EN") or "Unknown"
        mainlanduse_counts[mlu] = mainlanduse_counts.get(mlu, 0) + 1
        
        status = p.get("PARCEL_STATUS_LABEL") or "Unknown"
        if status == "Vacant" or str(p.get("PARCELSTATUS")) == "0":
            vacant_count += 1
        elif status == "Developed" or str(p.get("PARCELSTATUS")) == "2":
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
        if block_id and block_id != "Unknown":
            block_ids.add(block_id)
            
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

def analyze_bbox(min_x: float, min_y: float, max_x: float, max_y: float, shop_size_m2: float = 120.0, mosque_space_m2: float = 8.0) -> dict:
    parcels = get_parcels_in_bbox(min_x, min_y, max_x, max_y)
    return build_summary_stats(parcels, shop_size_m2, mosque_space_m2)

def analyze_polygon(polygon_geojson: dict, shop_size_m2: float = 120.0, mosque_space_m2: float = 8.0) -> dict:
    parcels = get_parcels_in_polygon(polygon_geojson)
    return build_summary_stats(parcels, shop_size_m2, mosque_space_m2)

def analyze_parcel_set(parcels: list[dict], shop_size_m2: float = 120.0, mosque_space_m2: float = 8.0) -> dict:
    return build_summary_stats(parcels, shop_size_m2, mosque_space_m2)
