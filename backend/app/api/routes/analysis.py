from fastapi import APIRouter, HTTPException

from app.models.analysis import ChangeAnalysisRequest, ChangeAnalysisResult
from app.models.ground_analysis import GroundAnalysisRequest
from app.models.backscatter_analysis import BackscatterAnalysisRequest
from app.services.backscatter_service import get_backscatter_result, run_backscatter_analysis
from app.services.change_detection_service import analyze
from app.services.ground_analysis_service import get_result, run_ground_analysis
from app.utils.geo import InvalidAOI, point_to_bbox, validate_bbox

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


@router.post("")
def ground_analysis(body: GroundAnalysisRequest):
    if body.change_type != "ground":
        raise HTTPException(422, "This Phase 4 endpoint accepts change_type='ground' only.")
    try:
        bbox = body.bbox
        if bbox is None:
            if body.lat is None or body.lon is None:
                raise InvalidAOI("Provide lat/lon or a bounding box.")
            bbox = point_to_bbox(body.lat, body.lon)
        else:
            bbox = validate_bbox(*bbox)
        analysis_id, result = run_ground_analysis(bbox, body.granule_ids)
        return {"analysis_id": analysis_id, "result": result}
    except (InvalidAOI, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"NISAR ground analysis failed: {exc}") from exc


@router.post("/backscatter")
def backscatter_analysis(body: BackscatterAnalysisRequest):
    try:
        if body.bbox is None:
            if body.lat is None or body.lon is None:
                raise InvalidAOI("Provide lat/lon or a bounding box.")
            bbox = point_to_bbox(body.lat, body.lon)
        else:
            bbox = validate_bbox(*body.bbox)
        return dict(zip(("analysis_id", "result"), run_backscatter_analysis(
            bbox, body.product, body.before_granule_id, body.after_granule_id, body.polarization,
        )))
    except (InvalidAOI, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"NISAR backscatter analysis failed: {exc}") from exc


@router.get("/backscatter/{analysis_id}")
def read_backscatter_analysis(analysis_id: str):
    try:
        return get_backscatter_result(analysis_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{analysis_id}")
def read_analysis(analysis_id: str):
    try:
        return get_result(analysis_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{analysis_id}/change")
def read_change(analysis_id: str):
    try:
        result = get_result(analysis_id)
        return {"zones": result["zones"], "bounds": None, "raster_overlay_url": None}
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{analysis_id}/timeseries")
def read_timeseries(analysis_id: str):
    try:
        get_result(analysis_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"status": "insufficient", "message": "Insufficient temporal observations for reliable trend estimation."}
