# Earth Pulse (Phase 2: NISAR connection + area watcher)

"Understand How Earth Changes." An independent NASA Space Apps project built on public NISAR data. **Not an official NASA application.**

## Status
Phases 1-2 plus an initial change-analysis slice: map, place/coordinate search, NISAR metadata search against NASA's catalog, an **area watcher** that records a baseline and then flags NISAR observations published later, and a real HDF5 comparison endpoint. The analysis is a screening metric and does not yet claim calibrated displacement or apply every product-specific quality mask.

**Near-real-time, not real-time.** NASA publishes NISAR Level 1-3 products roughly 1 to 3 days after acquisition, and the public record starts with observations from 2026-06-17 (earlier data is being added). Every result shows acquisition dates, never "live imagery".

## Run locally
Backend (Python 3.10+):
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env     # add your Earthdata credentials
uvicorn app.main:app --reload  # http://localhost:8000/docs
pytest
```
Frontend (Node 18+):
```bash
cd frontend
npm install
npm run dev                    # http://localhost:3000
```
Optional PostGIS: `docker compose up -d db` (unused until Phase 2+).

## Watcher
`POST /api/watches` stores an area (SQLite at `backend/data/watches.db`; PostGIS comes later). The first check is a baseline: existing granules are not reported as new. A background task re-checks every `WATCH_INTERVAL_MINUTES` (default 180); use "Check now" in the UI to force it. Only granules that appear after the baseline are flagged.

## Verify the NISAR link (first thing to do)
1. Register at urs.earthdata.nasa.gov and put credentials in `.env`.
2. Open `/api/nisar/auth-status` (should say authenticated), then `/api/nisar/resolved`. Short names are auto-discovered from the catalog by title; a product with an empty list means no matching collection was found. `NISAR_SHORTNAME_*` in `.env` only overrides discovery.
3. Search a location in the UI. Phase 2 hardens this; Phase 3 downloads one real granule and reads its HDF5 layers.

## Change analysis
Choose a product and two dates in the UI, then use **Analyze change between dates**. The backend searches for two distinct real granules, downloads them through `earthaccess`, finds a compatible numeric HDF5 layer, and computes a product-specific screening metric:

- `GCOV` and `GSLC`: median relative radar-response change.
- `SME2`: mean soil-moisture product-unit difference.
- `GUNW`: median interferogram difference (not calibrated centimeters yet).
- `GOFF`: median pixel-offset difference (not calibrated movement distance yet).

The endpoint is `POST /api/analysis/compare`. Results are deliberately described as possible change: geolocation, quality masks, calibration, and domain-specific interpretation still require product-level processing before operational use.

## Layout
`backend/app/{api,services,algorithms,models,core,utils}` as specified; stub files mark later phases. `frontend/{app,components,services,types}`.

## Technical risks
- NISAR is new: product availability, collection names, versions and public access timelines may change. Check coverage before promising a location.
- GUNW/GOFF are large HDF5 files; need AOI subsetting, caching and h5py/rasterio, and likely preprocessing for demo.
- Few acquisitions per site means time series and trends will often be impossible; the UI must say so.
- Interpretation (e.g. wildfire vs. other backscatter change) needs context data; keep language cautious.
- Infrastructure data (OSM/Overture) quality varies by region.

## MVP realism
Most feasible: GUNW ground deformation (Phase 4), then GCOV/GSLC backscatter change. SME2, GOFF and glacier analysis depend on real data availability at chosen sites; treat as stretch.

## Remaining
Phases 2-13 per the spec. Next: Phase 2 (auth + search hardening), Phase 3 (read one real granule).
