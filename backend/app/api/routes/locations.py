import httpx
from fastapi import APIRouter, HTTPException, Query
from app.core.config import settings
from app.utils.geo import InvalidAOI, validate_point

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("/search")
def search(q: str = Query(min_length=2)):
    """Place name or 'lat, lon' -> candidate locations."""
    parts = [p.strip() for p in q.split(",")]
    if len(parts) == 2:
        try:
            lat, lon = validate_point(float(parts[0]), float(parts[1]))
            return {"results": [{"name": f"{lat:.4f}, {lon:.4f}", "lat": lat, "lon": lon}]}
        except InvalidAOI as e:
            raise HTTPException(422, str(e))
        except ValueError:
            pass
    try:
        r = httpx.get(settings.geocoder_url, params={"q": q, "format": "json", "limit": 5},
                      headers={"User-Agent": "EarthPulse-SpaceApps/0.1"}, timeout=10)
        r.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(502, "Geocoding service unavailable. Enter coordinates as 'lat, lon' instead.")
    return {"results": [{"name": x["display_name"], "lat": float(x["lat"]), "lon": float(x["lon"])} for x in r.json()]}
