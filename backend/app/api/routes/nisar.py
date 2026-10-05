from fastapi import APIRouter, HTTPException, Query
from app.models.change import CHANGE_PRODUCTS, ChangeType
from app.models.observation import Product, SearchResult
from app.services.nisar_service import EarthaccessProvider, cached_search, get_provider
from app.utils.geo import InvalidAOI, point_to_bbox, validate_bbox

router = APIRouter(prefix="/api/nisar", tags=["nisar"])


@router.get("/search", response_model=SearchResult)
def search(
    change_type: ChangeType = ChangeType.AUTO,
    lat: float | None = None, lon: float | None = None,
    bbox: str | None = Query(None, description="west,south,east,north"),
    start: str | None = None, end: str | None = None,
):
    try:
        if bbox:
            box = validate_bbox(*[float(x) for x in bbox.split(",")])
        elif lat is not None and lon is not None:
            box = point_to_bbox(lat, lon)
        else:
            raise InvalidAOI("Provide lat & lon, or bbox=west,south,east,north.")
    except (InvalidAOI, ValueError) as e:
        raise HTTPException(422, str(e))
    products = [Product(p) for p in CHANGE_PRODUCTS[change_type]]
    try:
        result = cached_search(get_provider(), box, products, start, end)
    except PermissionError as e:
        raise HTTPException(401, str(e))
    except Exception as e:
        raise HTTPException(502, f"NISAR search failed: {e}")
    if result.count == 0:
        result.notes.append("No suitable NISAR observation was found for this location and date range. "
                            "Try expanding the date range or selecting a larger area.")
    return result


@router.get("/collections")
def collections():
    """Discover real NISAR collection short names on CMR (to verify .env mapping)."""
    try:
        return {"collections": EarthaccessProvider().collections()}
    except Exception as e:
        raise HTTPException(502, f"Collection discovery failed: {e}")


@router.get("/auth-status")
def auth_status():
    return EarthaccessProvider().auth_status()


@router.get("/resolved")
def resolved(refresh: bool = False):
    """Which real NISAR collection short names each product code resolved to."""
    try:
        return {"resolved": EarthaccessProvider().resolved(refresh=refresh)}
    except Exception as e:
        raise HTTPException(502, f"Could not reach the NASA catalog: {e}")
