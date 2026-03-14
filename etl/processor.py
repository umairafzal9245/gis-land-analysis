"""ETL processor for GeoJSON to SQLite ingestion."""
import json
import math
import sqlite3
import pyogrio
import geopandas as gpd
from pathlib import Path

from etl.constants import DOMAIN_MAPPINGS, SUBTYPE_MAPPINGS

GDB = r'/home/asim/gis-land-analysis/data/AI _Test.gdb'
layers = pyogrio.list_layers(GDB)   # see all layer names
gdf = gpd.read_file(GDB, layer='SubdivisionParcelBoundary') # Fixed case based on user's directory
print(gdf.columns.tolist())         # verify all fields are present

def process_geojson_to_sqlite(geojson_path: str, sqlite_path: str) -> None:
    """Read GeoJSON and write processed records into SQLite."""
    with open(geojson_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    features = data.get("features", [])

    conn = sqlite3.connect(sqlite_path)
    _ensure_schema(conn)
    records = [_feature_to_record(f) for f in features]
    conn.executemany(
        """
        INSERT INTO parcels
            (parcel_id, owner, address, land_use, zoning, area_sqft, area_acres,
             subtype, geometry_json, min_x, min_y, max_x, max_y)
        VALUES
            (:parcel_id, :owner, :address, :land_use, :zoning, :area_sqft, :area_acres,
             :subtype, :geometry_json, :min_x, :min_y, :max_x, :max_y)
        """,
        records,
    )
    conn.commit()
    conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS parcels (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            parcel_id     TEXT,
            owner         TEXT,
            address       TEXT,
            land_use      TEXT,
            zoning        TEXT,
            area_sqft     REAL,
            area_acres    REAL,
            subtype       TEXT,
            geometry_json TEXT,
            min_x         REAL,
            min_y         REAL,
            max_x         REAL,
            max_y         REAL
        )
    """)
    conn.commit()


def _feature_to_record(feature: dict) -> dict:
    props = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}

    raw_subtype = str(props.get("SUBTYPE", props.get("SubType", "")))
    raw_landuse = str(props.get("LANDUSE", props.get("LandUse", props.get("land_use", ""))))

    area_sqft = _compute_area_sqft(geometry)
    bbox = _compute_bbox(geometry)

    return {
        "parcel_id": str(props.get("PARCEL_ID", props.get("ParcelID", props.get("APN", "")))),
        "owner": str(props.get("OWNER", props.get("Owner", ""))),
        "address": str(props.get("ADDRESS", props.get("Address", props.get("SITEADDR", "")))),
        "land_use": DOMAIN_MAPPINGS.get(raw_landuse, raw_landuse),
        "zoning": str(props.get("ZONING", props.get("Zoning", ""))),
        "area_sqft": round(area_sqft, 2),
        "area_acres": round(area_sqft / 43_560, 6),
        "subtype": SUBTYPE_MAPPINGS.get(raw_subtype, raw_subtype),
        "geometry_json": json.dumps(geometry),
        "min_x": bbox[0],
        "min_y": bbox[1],
        "max_x": bbox[2],
        "max_y": bbox[3],
    }


def _compute_bbox(geometry: dict) -> tuple[float, float, float, float]:
    coords = _flatten_coords(geometry)
    if not coords:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return (min(xs), min(ys), max(xs), max(ys))


def _compute_area_sqft(geometry: dict) -> float:
    if geometry.get("type") not in ("Polygon", "MultiPolygon"):
        return 0.0
    rings = (
        geometry["coordinates"]
        if geometry["type"] == "Polygon"
        else [ring for poly in geometry["coordinates"] for ring in poly]
    )
    if not rings:
        return 0.0
    avg_lat = sum(c[1] for c in rings[0]) / len(rings[0])
    lat_m = 111_139.0
    lon_m = 111_139.0 * math.cos(math.radians(avg_lat))
    total = sum(abs(_shoelace(ring)) for ring in rings)
    return total * lat_m * lon_m * 10.7639  # m² → ft²


def _shoelace(ring: list) -> float:
    n = len(ring)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += ring[i][0] * ring[j][1]
        area -= ring[j][0] * ring[i][1]
    return area / 2.0


def _flatten_coords(geometry: dict) -> list:
    geo_type = geometry.get("type", "")
    coords = geometry.get("coordinates", [])
    if geo_type == "Point":
        return [coords]
    if geo_type in ("MultiPoint", "LineString"):
        return list(coords)
    if geo_type in ("MultiLineString", "Polygon"):
        return [pt for ring in coords for pt in ring]
    if geo_type == "MultiPolygon":
        return [pt for poly in coords for ring in poly for pt in ring]
    return []
