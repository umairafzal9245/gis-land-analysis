from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class BBoxRequest(BaseModel):
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    shop_size_m2: float = 120.0
    mosque_space_m2: float = 8.0

class PolygonRequest(BaseModel):
    geometry: dict
    shop_size_m2: float = 120.0
    mosque_space_m2: float = 8.0

class ParcelListRequest(BaseModel):
    parcels: List[dict]
    shop_size_m2: float = 120.0
    mosque_space_m2: float = 8.0

class AnalysisResponse(BaseModel):
    total_parcels: int
    total_area_m2: float
    vacant_count: int
    developed_count: int
    mosque_count: int
    mosque_total_area_m2: float
    mosque_capacity_estimate: int
    park_count: int
    park_total_area_m2: float
    residential_count: int
    residential_total_area_m2: float
    commercial_count: int
    commercial_total_area_m2: float
    shops_estimate: int
    government_count: int
    educational_count: int
    breakdown_by_category: Dict[str, Dict[str, Any]]
    
    # Keeping old properties to prevent frontend errors if they rely on it (unless requested to strictly match)
    # The prompt says: "The JSON response from every selection endpoint must contain the following fields..." 
    # I'll include the old fields as Optional to be safe just in case.
    landuse_category: Optional[Dict[str, int]] = None
    mainlanduse_label: Optional[Dict[str, int]] = None
    subtypes_counts: Optional[Dict[str, int]] = None
    subtypes: Optional[List[str]] = None
    overlapping_block_ids: Optional[List[str]] = None
    shop_size_m2: float = 120.0
    mosque_space_m2: float = 8.0

class ReportRequest(BaseModel):
    stats: Dict[str, Any]

class ReportResponse(BaseModel):
    report_text: str
