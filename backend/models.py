"""Pydantic models for API request/response validation."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List

# Valid categories for category queries — must match LANDUSE_CATEGORIES in etl/constants.py
QUERYABLE_CATEGORIES = [
    "Residential", "Commercial", "Religious", "Educational",
    "Health", "Municipal", "Recreational", "Utilities", "Special", "Unknown",
]


# =============================================================================
# Selection Request Models
# =============================================================================


class PolygonSelectRequest(BaseModel):
    """Request to select parcels within a polygon."""
    coordinates: List[List[float]] = Field(
        ...,
        min_length=3,
        description="List of [lat, lon] coordinate pairs (minimum 3 pairs)"
    )
    
    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v):
        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 coordinate pairs")
        for coord in v:
            if len(coord) != 2:
                raise ValueError("Each coordinate must be a [lat, lon] pair")
        return v


class BBoxSelectRequest(BaseModel):
    """Request to select parcels within a bounding box."""
    min_lat: float = Field(..., description="Minimum latitude boundary")
    max_lat: float = Field(..., description="Maximum latitude boundary")
    min_lon: float = Field(..., description="Minimum longitude boundary")
    max_lon: float = Field(..., description="Maximum longitude boundary")
    
    @field_validator("max_lat")
    @classmethod
    def validate_lat_order(cls, v, info):
        min_lat = info.data.get("min_lat")
        if min_lat is not None and v < min_lat:
            raise ValueError("max_lat must be greater than min_lat")
        return v
    
    @field_validator("max_lon")
    @classmethod
    def validate_lon_order(cls, v, info):
        min_lon = info.data.get("min_lon")
        if min_lon is not None and v < min_lon:
            raise ValueError("max_lon must be greater than min_lon")
        return v


class CategoryQueryRequest(BaseModel):
    """Request to query parcels by category within a selection."""
    category: str = Field(..., description="LANDUSE_CATEGORY to filter by")
    selected_objectids: List[int] = Field(
        ...,
        description="List of PARCEL_IDs from current selection"
    )
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v not in QUERYABLE_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(QUERYABLE_CATEGORIES)}")
        return v


# =============================================================================
# Capacity Calculation Request Models
# =============================================================================


class MosqueCapacityRequest(BaseModel):
    """Request to calculate mosque capacity for a parcel."""
    object_id: int = Field(..., description="PARCEL_ID/OBJECTID of the mosque parcel")


class CommercialCapacityRequest(BaseModel):
    """Request to calculate commercial capacity for a parcel."""
    object_id: int = Field(..., description="PARCEL_ID/OBJECTID of the commercial parcel")
    shop_size_m2: float = Field(
        default=120.0,
        gt=0,
        description="Size per shop in m² (must be greater than 0)"
    )


# =============================================================================
# Report Request Models
# =============================================================================


class ReportRequest(BaseModel):
    """Request to generate an LLM or PDF report for a selection."""
    selected_objectids: List[int] = Field(
        ...,
        description="List of PARCEL_IDs in the selection"
    )
    selection_summary: Dict[str, Any] = Field(
        ...,
        description="The breakdown object from polygon/bbox selection"
    )
    extra_context: Optional[str] = Field(
        default=None,
        description="Optional additional context for the report"
    )


# =============================================================================
# Legacy Models (backward compatibility)
# =============================================================================


class BBoxRequest(BaseModel):
    """Legacy bbox request format."""
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    shop_size_m2: float = 120.0
    mosque_space_m2: float = 8.0


class PolygonRequest(BaseModel):
    """Legacy polygon request with GeoJSON geometry."""
    geometry: dict
    shop_size_m2: float = 120.0
    mosque_space_m2: float = 8.0


class ParcelListRequest(BaseModel):
    """Legacy parcel list request."""
    parcels: List[dict]
    shop_size_m2: float = 120.0
    mosque_space_m2: float = 8.0


class AnalysisResponse(BaseModel):
    """Legacy analysis response format."""
    total_parcels: int
    total_area_m2: float
    vacant_count: int
    developed_count: int
    religious_count: int
    religious_total_area_m2: float
    religious_capacity_estimate: int
    recreational_count: int
    recreational_total_area_m2: float
    residential_count: int
    residential_total_area_m2: float
    commercial_count: int
    commercial_total_area_m2: float
    shops_estimate: int
    municipal_count: int
    educational_count: int
    health_count: int
    utilities_count: int
    breakdown_by_category: Dict[str, Dict[str, Any]]
    landuse_category: Optional[Dict[str, int]] = None
    mainlanduse_label: Optional[Dict[str, int]] = None
    subtypes_counts: Optional[Dict[str, int]] = None
    subtypes: Optional[List[str]] = None
    overlapping_block_ids: Optional[List[str]] = None
    shop_size_m2: float = 120.0
    mosque_space_m2: float = 8.0


class ReportResponse(BaseModel):
    """Response containing generated report text."""
    report_text: str


class TextReportRequest(BaseModel):
    """Legacy text report request."""
    object_id: int
    context_mode: str
