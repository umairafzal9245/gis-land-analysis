from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.models import (
    BBoxRequest, PolygonRequest, ParcelListRequest, AnalysisResponse,
    ReportRequest, ReportResponse
)
from backend.spatial import analyze_bbox, analyze_polygon, analyze_parcel_set
from backend.llm_service import analyze_parcels

app = FastAPI(title="GIS Land Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to GIS Land Analysis API"}

@app.post("/analyze/bbox", response_model=AnalysisResponse)
def api_analyze_bbox(req: BBoxRequest):
    try:
        if not (24 < req.min_lat < 26 and 46 < req.min_lon < 48):
            req.min_lat, req.min_lon = req.min_lon, req.min_lat
            req.max_lat, req.max_lon = req.max_lon, req.max_lat
        stats = analyze_bbox(
            req.min_lon, req.min_lat, req.max_lon, req.max_lat,
            req.shop_size_m2, req.mosque_space_m2
        )
        return AnalysisResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/polygon", response_model=AnalysisResponse)
def api_analyze_polygon(req: PolygonRequest):
    try:
        stats = analyze_polygon(
            req.geometry,
            req.shop_size_m2, req.mosque_space_m2
        )
        return AnalysisResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/parcels", response_model=AnalysisResponse)
def api_analyze_parcels(req: ParcelListRequest):
    try:
         stats = analyze_parcel_set(
            req.parcels,
            req.shop_size_m2, req.mosque_space_m2
         )
         return AnalysisResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/report", response_model=ReportResponse)
def api_analyze_parcels(req: ReportRequest):
    try:
        report_text = analyze_parcels(req.stats)
        return ReportResponse(report_text=report_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

