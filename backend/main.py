"""FastAPI backend for GIS Land Analysis."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import tempfile
import zipfile
import os

from backend.models import (
    # New models
    PolygonSelectRequest,
    BBoxSelectRequest,
    CategoryQueryRequest,
    NLQueryRequest,
    MosqueCapacityRequest,
    CommercialCapacityRequest,
    ReportRequest,
    ReportResponse,
    ShapefileExportRequest,
    GDBExportRequest,
    # Legacy models
    BBoxRequest,
    PolygonRequest,
    ParcelListRequest,
    AnalysisResponse,
    TextReportRequest,
)
from backend.database import (
    get_all_parcels_lightweight,
    get_parcels_by_objectids,
    get_all_blocks,
    get_block_summary,
)
from backend.spatial import (
    select_parcels_in_polygon,
    select_parcels_in_bbox,
    query_parcels_in_selection,
    calculate_mosque_capacity,
    calculate_commercial_capacity,
    # Legacy functions
    analyze_bbox,
    analyze_polygon,
    analyze_parcel_set,
)
from backend.llm_service import generate_selection_report, answer_nl_query, stream_nl_query
from backend.report_gen import generate_pdf_report

app = FastAPI(title="GIS Land Analysis API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "GIS Land Analysis API", "version": "2.0.0"}


# =============================================================================
# Parcels & Blocks Endpoints
# =============================================================================


@app.get("/parcels/lightweight")
def get_parcels_lightweight():
    """Get all parcels with marker-only columns for map rendering."""
    try:
        parcels = get_all_parcels_lightweight()
        return {"parcels": parcels, "count": len(parcels)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/parcels/{object_id}")
def get_parcel_detail(object_id: int):
    """Get full detail for one parcel."""
    try:
        parcels = get_parcels_by_objectids([object_id])
        if not parcels:
            raise HTTPException(status_code=404, detail=f"Parcel {object_id} not found")
        return {"parcel": parcels[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/blocks")
def get_blocks():
    """Get all block IDs."""
    try:
        blocks = get_all_blocks()
        return {"blocks": blocks, "count": len(blocks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analysis/block/{block_id}")
def get_block_analysis(block_id: str):
    """Get stats for one block."""
    try:
        summary = get_block_summary(block_id)
        if not summary:
            raise HTTPException(status_code=404, detail=f"Block {block_id} not found")
        return {"block": summary[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Selection Endpoints
# =============================================================================


@app.post("/selection/polygon")
def select_polygon(req: PolygonSelectRequest):
    """Select parcels within a polygon, returns summary + objectids."""
    try:
        result = select_parcels_in_polygon(req.coordinates)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/selection/bbox")
def select_bbox(req: BBoxSelectRequest):
    """Select parcels within a bounding box, returns summary + objectids."""
    try:
        result = select_parcels_in_bbox(
            req.min_lat, req.max_lat, req.min_lon, req.max_lon
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Query Endpoint
# =============================================================================


@app.post("/query/category")
def query_category(req: CategoryQueryRequest):
    """Filter selected objectids by LANDUSE_CATEGORY."""
    try:
        parcels = query_parcels_in_selection(req.category, req.selected_objectids)
        return {"parcels": parcels, "count": len(parcels), "category": req.category}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/nl")
def query_natural_language(req: NLQueryRequest):
    """Answer a natural language question about the selected parcels."""
    try:
        result = answer_nl_query(
            question=req.question,
            parcels_summary=req.selection_summary,
        )
        return {
            "answer": result["answer"],
            "question": req.question,
            "matching_parcel_ids": result.get("matching_parcel_ids", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query/nl/stream")
async def query_natural_language_stream(req: NLQueryRequest):
    """Stream a natural language answer as Server-Sent Events."""
    return StreamingResponse(
        stream_nl_query(
            question=req.question,
            parcels_summary=req.selection_summary,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

# =============================================================================
# Capacity Calculation Endpoints
# =============================================================================


@app.post("/calculate/mosque")
def calculate_mosque(req: MosqueCapacityRequest):
    """Calculate mosque capacity for one parcel."""
    try:
        result = calculate_mosque_capacity(req.object_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calculate/commercial")
def calculate_commercial(req: CommercialCapacityRequest):
    """Calculate commercial capacity with user-supplied shop size."""
    try:
        result = calculate_commercial_capacity(req.object_id, req.shop_size_m2)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Report Endpoints
# =============================================================================


@app.post("/report/text", response_model=ReportResponse)
def generate_text_report(req: ReportRequest):
    """Generate LLM report for a selection, incorporating filters and capacity calcs."""
    try:
        report_text = generate_selection_report(
            selection_summary=req.selection_summary,
            extra_context=req.extra_context,
            filtered_summary=req.filtered_summary,
            applied_filters=req.applied_filters,
            capacity_calculations=req.capacity_calculations,
            report_type=req.report_type,
            report_title=req.report_title,
        )
        return ReportResponse(report_text=report_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/report/pdf")
def generate_pdf(req: ReportRequest):
    """Generate PDF report for a selection, incorporating filters and capacity calcs."""
    try:
        # Generate narrative text
        report_text = generate_selection_report(
            selection_summary=req.selection_summary,
            extra_context=req.extra_context,
            filtered_summary=req.filtered_summary,
            applied_filters=req.applied_filters,
            capacity_calculations=req.capacity_calculations,
            report_type=req.report_type,
            report_title=req.report_title,
        )

        # Generate PDF with all session context
        pdf_bytes = generate_pdf_report(
            stats=req.selection_summary,
            report_text=report_text,
            applied_filters=req.applied_filters,
            capacity_calculations=req.capacity_calculations,
            filtered_summary=req.filtered_summary,
            report_title=req.report_title,
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=land_analysis_report.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Legacy Endpoints (backward compatibility)
# =============================================================================


@app.post("/export/shapefile")
def export_shapefile(req: ShapefileExportRequest):
    """Export selected parcels as a zipped shapefile."""
    try:
        import geopandas as gpd
        from shapely.geometry import Point

        parcels = get_parcels_by_objectids(req.selected_objectids)
        if not parcels:
            raise HTTPException(status_code=404, detail="No parcels found for export")

        rows = []
        for p in parcels:
            lon = p.get("REPR_LON")
            lat = p.get("REPR_LAT")
            geom = Point(float(lon), float(lat)) if lon and lat else None
            rows.append({
                "OBJECTID": p.get("OBJECTID") or p.get("PARCEL_ID"),
                "CATEGORY": p.get("LANDUSE_CATEGORY", ""),
                "SUBTYPE_EN": p.get("SUBTYPE_LABEL_EN", ""),
                "AREA_M2": p.get("AREA_M2", 0),
                "STATUS": p.get("PARCEL_STATUS_LABEL", ""),
                "BLOCK_ID": p.get("BLOCK_NO") or p.get("BLOCK_ID", ""),
                "geometry": geom,
            })

        gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")

        with tempfile.TemporaryDirectory() as tmpdir:
            shp_path = os.path.join(tmpdir, "parcels.shp")
            gdf.to_file(shp_path)

            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for fname in os.listdir(tmpdir):
                    fpath = os.path.join(tmpdir, fname)
                    zf.write(fpath, fname)
            zip_buf.seek(0)

        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=parcels_export.zip"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export/gdb")
def export_gdb(req: GDBExportRequest):
    """Export analysis results as a zipped File Geodatabase (.gdb).
    
    This endpoint creates a complete GDB export containing:
    - Selection polygon layer
    - All selected parcels with full geometry and computed fields
    - Query result layer (if category filter was applied)
    - Capacity calculations layer (if calculations were performed)
    - Analysis summary table
    - LLM report sections table
    - Domain lookup tables for Arabic labels
    
    The export is returned as a zip file containing the .gdb folder,
    a README.txt with usage instructions, and the report as a text file.
    
    Falls back to GeoPackage (.gpkg) if GDB writing is not supported.
    """
    try:
        from backend.gdb_export import export_to_gdb
        from datetime import datetime
        
        zip_buffer = export_to_gdb(
            selected_objectids=req.selected_objectids,
            polygon_coordinates=req.polygon_coordinates,
            selection_summary=req.selection_summary,
            query_category=req.query_category,
            query_parcel_ids=req.query_parcel_ids,
            capacity_calculations=req.capacity_calculations,
            report_text=req.report_text,
            generate_report_if_missing=req.generate_report_if_missing,
        )
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
        filename = f"GIS_Analysis_{timestamp}.zip"
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/bbox", response_model=AnalysisResponse)
def api_analyze_bbox(req: BBoxRequest):
    """Legacy bbox analysis endpoint."""
    try:
        # Auto-detect coordinate swap if needed
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
    """Legacy polygon analysis endpoint."""
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
    """Legacy parcel list analysis endpoint."""
    try:
        stats = analyze_parcel_set(
            req.parcels,
            req.shop_size_m2, req.mosque_space_m2
        )
        return AnalysisResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
