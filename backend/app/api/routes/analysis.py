from fastapi import APIRouter, HTTPException

from app.models.analysis import ChangeAnalysisRequest, ChangeAnalysisResult
from app.services.change_detection_service import analyze
from app.utils.geo import InvalidAOI

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/compare", response_model=ChangeAnalysisResult)
def compare(body: ChangeAnalysisRequest):
    try:
        return analyze((body.lat, body.lon), body.product, body.start, body.end)
    except (InvalidAOI, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"NISAR change analysis failed: {exc}") from exc
