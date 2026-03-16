"""SQLite query helpers."""
import sqlite3
import json
from contextlib import contextmanager
from typing import Generator
from shapely.geometry import Point, shape

DB_PATH = "data/gis_database.db"

@contextmanager
def get_connection(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db(db_path: str = DB_PATH) -> None:
    pass

def query_all_parcels(db_path: str = DB_PATH) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM parcels").fetchall()
        return [dict(row) for row in rows]

def get_parcels(
    details_landuse: str | None = None,
    main_landuse: str | None = None,
    parcel_status: str | None = None,
    block_id: str | None = None,
    db_path: str = DB_PATH
) -> list[dict]:
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

def get_block_summary(block_id: str | None = None, db_path: str = DB_PATH) -> list[dict]:
    with get_connection(db_path) as conn:
        if block_id:
            rows = conn.execute("SELECT * FROM block_summary WHERE BLOCK_ID = ?", (block_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM block_summary").fetchall()
        return [dict(row) for row in rows]

def get_parcels_in_bbox(min_x: float, min_y: float, max_x: float, max_y: float, db_path: str = DB_PATH) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM parcels
            WHERE REPR_LON >= ? AND REPR_LON <= ?
              AND REPR_LAT >= ? AND REPR_LAT <= ?
            """,
            (min_x, max_x, min_y, max_y),
        ).fetchall()
        return [dict(row) for row in rows]

def query_parcels_in_bbox(min_x: float, min_y: float, max_x: float, max_y: float, db_path: str = DB_PATH) -> list[dict]:
    return get_parcels_in_bbox(min_x, min_y, max_x, max_y, db_path)

def get_parcels_in_polygon(polygon_geojson: dict, db_path: str = DB_PATH) -> list[dict]:
    poly = shape(polygon_geojson)
    min_x, min_y, max_x, max_y = poly.bounds
    
    candidates = get_parcels_in_bbox(min_x, min_y, max_x, max_y, db_path)
    results = []
    for c in candidates:
        if "REPR_LON" in c and "REPR_LAT" in c and c["REPR_LON"] is not None and c["REPR_LAT"] is not None:
            pt = Point(c["REPR_LON"], c["REPR_LAT"])
            if poly.contains(pt):
                results.append(c)
    return results

def get_all_blocks(db_path: str = DB_PATH) -> list[str]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT DISTINCT BLOCK_ID FROM parcels WHERE BLOCK_ID IS NOT NULL ORDER BY BLOCK_ID").fetchall()
        return [row["BLOCK_ID"] for row in rows]
