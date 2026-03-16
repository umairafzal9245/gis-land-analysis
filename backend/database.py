"""SQLite query helpers for the GIS Land Analysis API.

This module provides optimized query functions for:
- Lightweight marker data for map rendering
- Bounding box queries for viewport filtering
- Full parcel details by ID
- Block summary statistics
- Category-based parcel search
"""
import sqlite3
from contextlib import contextmanager
from typing import Generator
from shapely.geometry import Point, shape

DB_PATH = "data/gis_database.db"


@contextmanager
def get_connection(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections with Row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH) -> None:
    """Initialize the database (placeholder for future migrations)."""
    pass


# =============================================================================
# Primary API Functions (Step 5.1)
# =============================================================================


def get_all_parcels_lightweight(db_path: str = DB_PATH) -> list[dict]:
    """Return lightweight parcel data for map marker rendering.
    
    Queries the parcel_search_index table for all parcels, returning only
    the columns needed for map display. This keeps the payload small for
    rendering all 3,446 markers on initial load.
    
    Returns:
        List of dicts with: PARCEL_ID, REPR_LAT, REPR_LON, LANDUSE_CATEGORY,
        SUBTYPE_LABEL_EN, IS_COMMERCIAL
    """
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT 
                PARCEL_ID,
                REPR_LAT,
                REPR_LON,
                LANDUSE_CATEGORY,
                SUBTYPE_LABEL_EN,
                IS_COMMERCIAL
            FROM parcel_search_index
        """).fetchall()
        return [dict(row) for row in rows]


def get_parcels_in_bbox(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    db_path: str = DB_PATH
) -> list[dict]:
    """Return parcels within a bounding box.
    
    Queries parcel_search_index for parcels whose REPR_LAT and REPR_LON
    fall within the specified bounds. Used for viewport-based filtering.
    
    Args:
        min_lat: Minimum latitude boundary
        max_lat: Maximum latitude boundary
        min_lon: Minimum longitude boundary
        max_lon: Maximum longitude boundary
        
    Returns:
        List of parcel dicts from parcel_search_index matching the bounds.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM parcel_search_index
            WHERE REPR_LAT >= ? AND REPR_LAT <= ?
              AND REPR_LON >= ? AND REPR_LON <= ?
            """,
            (min_lat, max_lat, min_lon, max_lon),
        ).fetchall()
        return [dict(row) for row in rows]


def get_parcels_by_objectids(
    objectids: list[int],
    db_path: str = DB_PATH
) -> list[dict]:
    """Return full parcel details for specific parcel IDs.
    
    Queries the main parcels table for all columns plus computed fields.
    Used when a user clicks a marker and needs comprehensive parcel data.
    
    Args:
        objectids: List of PARCEL_ID/OBJECTID values to retrieve.
        
    Returns:
        List of full parcel records (all 93+ columns) for matching IDs.
    """
    if not objectids:
        return []
    
    with get_connection(db_path) as conn:
        # Use parameterized query with dynamically generated placeholders
        placeholders = ",".join("?" for _ in objectids)
        
        # Try OBJECTID first, fall back to PARCEL_ID
        try:
            rows = conn.execute(
                f"SELECT * FROM parcels WHERE OBJECTID IN ({placeholders})",
                objectids
            ).fetchall()
        except sqlite3.OperationalError:
            # OBJECTID column doesn't exist, try PARCEL_ID
            rows = conn.execute(
                f"SELECT * FROM parcels WHERE PARCEL_ID IN ({placeholders})",
                objectids
            ).fetchall()
        
        return [dict(row) for row in rows]


def get_block_summary(
    block_id: str | None = None,
    db_path: str = DB_PATH
) -> list[dict]:
    """Return pre-aggregated block statistics.
    
    Queries the block_summary table for aggregated metrics including
    total parcels, area, vacancy counts, and category breakdowns.
    
    Args:
        block_id: Optional specific block ID. If None, returns all blocks.
        
    Returns:
        List of block summary records with aggregated statistics.
    """
    with get_connection(db_path) as conn:
        if block_id:
            rows = conn.execute(
                "SELECT * FROM block_summary WHERE BLOCK_ID = ?",
                (block_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM block_summary").fetchall()
        return [dict(row) for row in rows]


def search_parcels_by_category(
    category: str,
    objectids: list[int] | None = None,
    db_path: str = DB_PATH
) -> list[dict]:
    """Search parcels by land use category with optional ID restriction.
    
    Queries parcel_search_index for parcels matching the specified
    LANDUSE_CATEGORY. Optionally restricts results to a subset of
    parcel IDs (e.g., from a polygon selection).
    
    Args:
        category: The LANDUSE_CATEGORY to filter by (e.g., "Mosque", "Commercial")
        objectids: Optional list of PARCEL_IDs to restrict search scope
        
    Returns:
        List of matching parcels from parcel_search_index.
    """
    with get_connection(db_path) as conn:
        if objectids:
            placeholders = ",".join("?" for _ in objectids)
            rows = conn.execute(
                f"""
                SELECT * FROM parcel_search_index
                WHERE LANDUSE_CATEGORY = ?
                  AND PARCEL_ID IN ({placeholders})
                """,
                [category] + list(objectids)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM parcel_search_index WHERE LANDUSE_CATEGORY = ?",
                (category,)
            ).fetchall()
        return [dict(row) for row in rows]


# =============================================================================
# Legacy / Additional Query Functions
# =============================================================================


def query_all_parcels(db_path: str = DB_PATH) -> list[dict]:
    """Return all parcels with full details from the parcels table."""
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM parcels").fetchall()
        return [dict(row) for row in rows]


def get_all_parcels(db_path: str = DB_PATH) -> list[dict]:
    """Alias for query_all_parcels for consistency with get_* naming pattern."""
    return query_all_parcels(db_path)


def get_parcels(
    details_landuse: str | None = None,
    main_landuse: str | None = None,
    parcel_status: str | None = None,
    block_id: str | None = None,
    db_path: str = DB_PATH
) -> list[dict]:
    """Query parcels with optional filters on legacy columns."""
    with get_connection(db_path) as conn:
        query = "SELECT * FROM parcels WHERE 1=1"
        params = []
        if details_landuse is not None:
            query += " AND DETAILSLANDUSE = ?"
            params.append(details_landuse)
        if main_landuse is not None:
            query += " AND MAINLANDUSE = ?"
            params.append(main_landuse)
        if parcel_status is not None:
            query += " AND PARCELSTATUS = ?"
            params.append(parcel_status)
        if block_id is not None:
            query += " AND BLOCK_ID = ?"
            params.append(block_id)
        
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def query_parcels_in_bbox(
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    db_path: str = DB_PATH
) -> list[dict]:
    """Legacy bbox query using x/y coordinates (lon/lat order)."""
    return get_parcels_in_bbox(min_y, max_y, min_x, max_x, db_path)


def get_parcels_in_polygon(polygon_geojson: dict, db_path: str = DB_PATH) -> list[dict]:
    """Return parcels whose representative point falls within a GeoJSON polygon."""
    poly = shape(polygon_geojson)
    min_x, min_y, max_x, max_y = poly.bounds
    
    # First filter by bounding box, then precise polygon check
    candidates = get_parcels_in_bbox(min_y, max_y, min_x, max_x, db_path)
    results = []
    for c in candidates:
        if c.get("REPR_LON") is not None and c.get("REPR_LAT") is not None:
            pt = Point(c["REPR_LON"], c["REPR_LAT"])
            # Use covers() not contains(): covers() returns True when the point lies
            # on the polygon boundary, so parcels whose representative point sits
            # exactly on the drawn polygon edge are correctly included.
            if poly.covers(pt):
                results.append(c)
    return results


def get_all_blocks(db_path: str = DB_PATH) -> list[str]:
    """Return list of all unique BLOCK_ID values."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT BLOCK_ID FROM parcels WHERE BLOCK_ID IS NOT NULL ORDER BY BLOCK_ID"
        ).fetchall()
        return [row["BLOCK_ID"] for row in rows]
