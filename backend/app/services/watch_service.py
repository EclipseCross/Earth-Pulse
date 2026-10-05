"""Watch an area: periodically search NASA for NISAR granules and record ones not seen before.
First check only records a baseline (existing granules are NOT reported as new)."""
import sqlite3
import time
from pathlib import Path

from app.core.config import settings
from app.core.logging import log
from app.models.change import CHANGE_PRODUCTS, ChangeType
from app.models.observation import Product
from app.services.nisar_service import cached_search, get_provider
from app.utils.geo import point_to_bbox

SCHEMA = """
CREATE TABLE IF NOT EXISTS watches(id INTEGER PRIMARY KEY, lat REAL, lon REAL, change_type TEXT,
  created REAL, last_checked REAL, last_error TEXT, baseline_done INTEGER DEFAULT 0, baseline_count INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS granules(watch_id INTEGER, granule_id TEXT, product TEXT, acquisition_start TEXT,
  detected REAL, is_new INTEGER, unread INTEGER, PRIMARY KEY(watch_id, granule_id));
"""


def _db() -> sqlite3.Connection:
    path = Path(settings.watch_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def create_watch(lat: float, lon: float, change_type: ChangeType) -> int:
    point_to_bbox(lat, lon)  # validates
    with _db() as con:
        cur = con.execute("INSERT INTO watches(lat,lon,change_type,created) VALUES(?,?,?,?)",
                          (lat, lon, change_type.value, time.time()))
        return cur.lastrowid


def delete_watch(wid: int) -> None:
    with _db() as con:
        con.execute("DELETE FROM granules WHERE watch_id=?", (wid,))
        con.execute("DELETE FROM watches WHERE id=?", (wid,))


def mark_read(wid: int) -> None:
    with _db() as con:
        con.execute("UPDATE granules SET unread=0 WHERE watch_id=?", (wid,))


def _view(con, row) -> dict:
    new = [dict(r) for r in con.execute(
        "SELECT granule_id,product,acquisition_start,detected,unread FROM granules WHERE watch_id=? AND is_new=1 ORDER BY detected DESC",
        (row["id"],))]
    return {**dict(row), "new_observations": new, "unread": sum(1 for n in new if n["unread"])}


def list_watches() -> list[dict]:
    with _db() as con:
        return [_view(con, r) for r in con.execute("SELECT * FROM watches ORDER BY id DESC")]


def get_watch(wid: int) -> dict | None:
    with _db() as con:
        r = con.execute("SELECT * FROM watches WHERE id=?", (wid,)).fetchone()
        return _view(con, r) if r else None


def check_watch(wid: int, provider=None) -> dict | None:
    provider = provider or get_provider()
    w = get_watch(wid)
    if not w:
        return None
    products = [Product(p) for p in CHANGE_PRODUCTS[ChangeType(w["change_type"])]]
    box = point_to_bbox(w["lat"], w["lon"])
    try:
        res = cached_search(provider, box, products, None, None, use_cache=False)
        err = None
    except Exception as e:
        log.warning("Watch %s check failed: %s", wid, e)
        res, err = None, str(e)
    with _db() as con:
        if res is not None:
            first = not w["baseline_done"]
            for o in res.observations:
                exists = con.execute("SELECT 1 FROM granules WHERE watch_id=? AND granule_id=?", (wid, o.granule_id)).fetchone()
                if exists:
                    continue
                con.execute("INSERT INTO granules VALUES(?,?,?,?,?,?,?)",
                            (wid, o.granule_id, o.product.value, o.acquisition_start, time.time(),
                             0 if first else 1, 0 if first else 1))
            if first:
                con.execute("UPDATE watches SET baseline_done=1, baseline_count=? WHERE id=?", (res.count, wid))
        con.execute("UPDATE watches SET last_checked=?, last_error=? WHERE id=?", (time.time(), err, wid))
    return get_watch(wid)


def check_all() -> None:
    for w in list_watches():
        check_watch(w["id"])
