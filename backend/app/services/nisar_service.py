"""NISAR service abstraction (Phase 2).
 - EarthaccessProvider: live CMR search via NASA Earthdata. Collection short names are discovered
   from the catalog by title (env overrides win), so we don't rely on guessed names.
 - DemoProvider: reads real preprocessed metadata from backend/demo_data/*.json.
Neither provider invents observations; an empty result is valid."""
import json
import os
import time
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.core.logging import log
from app.models.observation import DataOrigin, Observation, Product, SearchResult

DEMO_DIR = Path(__file__).resolve().parents[2] / "demo_data"

# Title keywords used to match NISAR collections to our product codes.
TITLE_KEYWORDS = {
    "GUNW": "unwrapped interferogram",
    "GSLC": "single look complex",
    "GCOV": "polarimetric covariance",
    "GOFF": "pixel offsets",
    "SME2": "soil moisture",
}


def resolve_short_names(collections: list[dict]) -> dict[str, list[str]]:
    """Pure function: catalog entries [{short_name,title,version}] -> {product: [short_names]}."""
    out: dict[str, list[str]] = {k: [] for k in TITLE_KEYWORDS}
    for c in collections:
        title = (c.get("title") or "").lower()
        sn = c.get("short_name")
        if not sn or "nisar" not in title:
            continue
        for prod, kw in TITLE_KEYWORDS.items():
            if kw in title and sn not in out[prod]:
                out[prod].append(sn)
    return out


class NisarProvider(Protocol):
    def search(self, bbox, products: list[Product], start: str | None, end: str | None) -> SearchResult: ...


def _overlaps(a, b) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


class DemoProvider:
    def search(self, bbox, products, start, end) -> SearchResult:
        obs: list[Observation] = []
        notes = ["Demo mode: using preprocessed NISAR metadata from backend/demo_data."]
        files = sorted(DEMO_DIR.glob("*.json"))
        if not files:
            notes.append("No demo datasets installed yet. See backend/demo_data/README.md.")
        for f in files:
            for raw in json.loads(f.read_text()).get("observations", []):
                o = Observation(**{**raw, "origin": DataOrigin.DEMO})
                if o.product not in products:
                    continue
                if o.bbox and not _overlaps(bbox, o.bbox):
                    continue
                if start and o.acquisition_start and o.acquisition_start < start:
                    continue
                if end and o.acquisition_start and o.acquisition_start > end:
                    continue
                obs.append(o)
        return SearchResult(origin=DataOrigin.DEMO, bbox=bbox, products_searched=products,
                            count=len(obs), observations=obs, notes=notes)


class EarthaccessProvider:
    _logged_in = False
    _resolved: dict[str, list[str]] | None = None

    def auth_status(self) -> dict:
        try:
            self._login()
            return {"authenticated": True, "message": "Logged in to NASA Earthdata."}
        except Exception as e:
            return {"authenticated": False, "message": str(e)}

    def _login(self):
        import earthaccess
        if EarthaccessProvider._logged_in:
            return
        for key, value in {
            "EARTHDATA_USERNAME": settings.earthdata_username,
            "EARTHDATA_PASSWORD": settings.earthdata_password,
            "EARTHDATA_TOKEN": settings.earthdata_token,
        }.items():
            if value:
                os.environ.setdefault(key, value)
        auth = earthaccess.login(strategy="environment")
        if not getattr(auth, "authenticated", False):
            auth = earthaccess.login(strategy="netrc")
        if not getattr(auth, "authenticated", False):
            raise PermissionError("Earthdata authentication failed. Set EARTHDATA_USERNAME and EARTHDATA_PASSWORD in .env.")
        EarthaccessProvider._logged_in = True

    def collections(self) -> list[dict]:
        import earthaccess
        res = earthaccess.search_datasets(keyword="NISAR", count=200)
        return [{"short_name": c.get("umm", {}).get("ShortName"), "version": c.get("umm", {}).get("Version"),
                 "title": c.get("umm", {}).get("EntryTitle")} for c in res]

    def resolved(self, refresh: bool = False) -> dict[str, list[str]]:
        if EarthaccessProvider._resolved is None or refresh:
            EarthaccessProvider._resolved = resolve_short_names(self.collections())
        merged = dict(EarthaccessProvider._resolved)
        for prod, v in settings.short_name_overrides().items():
            merged[prod] = [x.strip() for x in v.split(",") if x.strip()]
        return merged

    def search(self, bbox, products, start, end) -> SearchResult:
        out, notes, _ = self._search_with_granules(bbox, products, start, end)
        return SearchResult(origin=DataOrigin.LIVE, bbox=bbox, products_searched=products,
                            count=len(out), observations=out, notes=notes)

    def _search_with_granules(self, bbox, products, start, end):
        import earthaccess
        self._login()
        names = self.resolved()
        out: list[Observation] = []
        granules = {}
        seen: set[str] = set()
        notes: list[str] = []
        for p in products:
            sns = names.get(p.value) or []
            if not sns:
                notes.append(f"{p.value}: no matching NISAR collection found in the catalog.")
                continue
            for sn in sns:
                try:
                    kw = dict(short_name=sn, bounding_box=bbox, count=100)
                    if start or end:
                        kw["temporal"] = (start, end)
                    for g in earthaccess.search_data(**kw):
                        umm = g["umm"]
                        gid = umm.get("GranuleUR", "")
                        if gid in seen:
                            continue
                        seen.add(gid)
                        granules[gid] = g
                        rng = umm.get("TemporalExtent", {}).get("RangeDateTime", {})
                        links = g.data_links() if hasattr(g, "data_links") else []
                        size = getattr(g, "size", None)
                        size_mb = size() if callable(size) else size
                        out.append(Observation(
                            granule_id=gid, product=p,
                            acquisition_start=rng.get("BeginningDateTime"), acquisition_end=rng.get("EndingDateTime"),
                            size_mb=size_mb,
                            download_url=links[0] if links else None, origin=DataOrigin.LIVE))
                except Exception as exc:  # one collection failing must not hide the others
                    log.warning("Search failed for %s/%s: %s", p.value, sn, exc)
                    notes.append(f"{p.value} ({sn}): search failed ({exc}).")
        out.sort(key=lambda o: o.acquisition_start or "")
        return out, notes, granules

    def search_granules(self, bbox, products, start, end):
        out, _, granules = self._search_with_granules(bbox, products, start, end)
        return out, granules

    def download_granules(self, granules, destination):
        import earthaccess
        files = earthaccess.download(granules, str(destination))
        result = {}
        for path in files:
            path = Path(path)
            for granule in granules:
                gid = granule["umm"].get("GranuleUR", "")
                if gid in path.name:
                    result[gid] = path
        if len(result) != len(granules):
            raise RuntimeError("NASA download completed but a requested granule file could not be matched.")
        return result


def get_provider() -> NisarProvider:
    return DemoProvider() if settings.earthpulse_mode == "demo" else EarthaccessProvider()


_cache: dict[tuple, tuple[float, SearchResult]] = {}


def cached_search(provider: NisarProvider, bbox, products, start, end, use_cache: bool = True) -> SearchResult:
    key = (tuple(round(x, 4) for x in bbox), tuple(p.value for p in products), start, end)
    hit = _cache.get(key)
    if use_cache and hit and time.time() - hit[0] < settings.search_cache_seconds:
        return hit[1]
    res = provider.search(bbox, products, start, end)
    if not res.notes or res.count:  # don't cache pure-failure results
        _cache[key] = (time.time(), res)
    return res
