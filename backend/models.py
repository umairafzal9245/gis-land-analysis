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
    landuse_category: Dict[str, int]
    mainlanduse_label: Dict[str, int]
    subtypes_counts: Dict[str, int]
    vacant_count: int
    developed_count: int
    total_mosque_capacity: int
    total_shops: int
    subtypes: List[str]
    overlapping_block_ids: List[str]
    shop_size_m2: float = 120.0
    mosque_space_m2: float = 8.0

class ReportRequest(BaseModel):
    stats: Dict[str, Any]

class ReportResponse(BaseModel):
    report_text: str
