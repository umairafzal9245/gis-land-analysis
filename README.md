# GIS Land Analysis

A full-stack application for ingesting, visualizing, and analyzing land parcel data with AI-powered insights and PDF report generation.

## Architecture

```
backend/      FastAPI REST API (Python)
etl/          GeoJSON → SQLite ingestion pipeline
frontend/     React + Leaflet map UI (Vite)
data/         GeoJSON source data and SQLite database
tests/        pytest test suite
```

## Setup

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

### ETL — ingest parcel data

```bash
python -c "
from etl.processor import process_geojson_to_sqlite
process_geojson_to_sqlite('data/SubdivisionParcelBoundary.geojson', 'data/gis_database.db')
"
```
cd /home/asim/gis-land-analysis && python -m etl.processor
uvicorn backend.main:app --reload --port 8000
npm run dev
### Run the API server

```bash
uvicorn backend.main:app --reload
```

API docs available at http://localhost:8000/docs

### Frontend

```bash
npm install
npm run dev
```

UI available at http://localhost:5173

## API Endpoints

| Method | Path              | Description                              |
|--------|-------------------|------------------------------------------|
| GET    | `/health`         | Health check                             |
| GET    | `/parcels`        | List all parcels (optional bbox filter)  |
| GET    | `/parcels/stats`  | Aggregate parcel statistics              |
| POST   | `/analyze`        | AI-powered analysis via LLM provider     |
| GET    | `/report`         | Download PDF report                      |

### Parcel bbox filter

```
GET /parcels?min_x=-118.5&min_y=33.7&max_x=-117.5&max_y=34.2
```

### LLM Analysis providers

```json
POST /analyze
{ "provider": "ollama" }   // local Ollama (default)
{ "provider": "gemini" }   // Google Gemini (requires GEMINI_API_KEY)
{ "provider": "groq" }     // Groq (requires GROQ_API_KEY)
```

## Tests

```bash
pytest tests/
```

## Environment Variables

| Variable         | Description                        |
|------------------|------------------------------------|
| `GEMINI_API_KEY` | Google Gemini API key              |
| `GROQ_API_KEY`   | Groq API key                       |
| `OLLAMA_BASE_URL`| Ollama base URL (default: localhost:11434) |
| `DB_PATH`        | Path to SQLite database            |
