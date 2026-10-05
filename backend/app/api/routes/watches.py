from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.change import ChangeType
from app.services import watch_service as ws
from app.utils.geo import InvalidAOI

router = APIRouter(prefix="/api/watches", tags=["watches"])


class WatchIn(BaseModel):
    lat: float
    lon: float
    change_type: ChangeType = ChangeType.AUTO


@router.post("")
def create(body: WatchIn):
    try:
        wid = ws.create_watch(body.lat, body.lon, body.change_type)
    except InvalidAOI as e:
        raise HTTPException(422, str(e))
    return ws.check_watch(wid)  # baseline immediately


@router.get("")
def list_all():
    return {"watches": ws.list_watches()}


@router.post("/{wid}/check")
def check(wid: int):
    r = ws.check_watch(wid)
    if not r:
        raise HTTPException(404, "Watch not found.")
    return r


@router.post("/{wid}/read")
def read(wid: int):
    ws.mark_read(wid)
    return {"ok": True}


@router.delete("/{wid}")
def delete(wid: int):
    ws.delete_watch(wid)
    return {"ok": True}
