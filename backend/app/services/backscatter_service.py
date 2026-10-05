from __future__ import annotations

import re
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np
from pyproj import Transformer

from app.algorithms.backscatter import (
    extract_backscatter_zones,
    multilook_mean,
    power_to_db,
    summarize_backscatter,
)
from app.core.config import settings
from app.models.observation import Product
from app.services.nisar_service import EarthaccessProvider
from app.services.processing_service import CACHE, _window
from app.utils.geo import validate_bbox

BACKSCATTER_RESULTS: dict[str, dict] = {}


def _datasets(handle: h5py.File) -> list[tuple[str, h5py.Dataset]]:
    found: list[tuple[str, h5py.Dataset]] = []
    def visit(name: str, item):
        if isinstance(item, h5py.Dataset) and item.ndim == 2 and np.issubdtype(item.dtype, np.number):
            found.append((name, item))
    handle.visititems(visit)
    return found


def _find_dataset(handle: h5py.File, suffix: str) -> h5py.Dataset | None:
    matches: list[h5py.Dataset] = []
    def visit(name: str, item):
        if isinstance(item, h5py.Dataset) and name.endswith(suffix):
            matches.append(item)
    handle.visititems(visit)
    return matches[0] if len(matches) == 1 else None


def _find_signal(handle: h5py.File, polarization: str | None) -> tuple[str, h5py.Dataset, str]:
    candidates = []
    for name, dataset in _datasets(handle):
        lower = name.lower()
        pol = next((p for p in ("hh", "hv", "vh", "vv") if f"/{p}/" in f"/{lower}/"), None)
        if polarization and pol != polarization.lower():
            continue
        if any(token in lower for token in ("power", "intensity", "backscatter", "gamma0", "sigma0", "covariance")):
            candidates.append((name, dataset, pol or polarization or "unknown"))
    if len(candidates) != 1:
        raise ValueError("Could not identify exactly one unambiguous GCOV/GSLC backscatter dataset for the requested polarization.")
    return candidates[0]


def process_backscatter(path: Path, bbox: tuple[float, float, float, float], polarization: str | None):
    with h5py.File(path, "r") as handle:
        name, signal, actual_pol = _find_signal(handle, polarization)
        x_dataset = _find_dataset(handle, "xCoordinates")
        y_dataset = _find_dataset(handle, "yCoordinates")
        projection = _find_dataset(handle, "projection")
        if x_dataset is None or y_dataset is None or projection is None:
            raise ValueError("Backscatter file is missing coordinate or projection metadata.")
        x = np.asarray(x_dataset[()])
        y = np.asarray(y_dataset[()])
        crs_value = projection.attrs.get("epsg_code", projection[()])
        crs = int(crs_value)
        to_grid = Transformer.from_crs(4326, crs, always_xy=True)
        west, south = to_grid.transform(bbox[0], bbox[1])
        east, north = to_grid.transform(bbox[2], bbox[3])
        x0, x1 = _window(x, min(west, east), max(west, east))
        y0, y1 = _window(y, min(north, south), max(north, south))
        values = np.asarray(signal[y0:y1, x0:x1], dtype=np.float64)
        if not np.isfinite(values).any():
            raise ValueError("The requested backscatter AOI contains only nodata.")
        dx = float(np.median(np.diff(x)))
        dy = float(np.median(np.diff(y)))
        transform = (float(x[x0]), dx, 0.0, float(y[y0]), 0.0, dy)
        units = str(signal.attrs.get("units", "")).lower()
        if units not in {"1", "linear", "power", "intensity", ""}:
            raise ValueError(f"Unsupported backscatter units: {units}.")
    return values, transform, crs, actual_pol, name, units


def _date(granule_id: str) -> str | None:
    match = re.search(r"_(\d{8}T\d{6})_", granule_id)
    return datetime.strptime(match.group(1), "%Y%m%dT%H%M%S").date().isoformat() if match else None


def _pair_metadata(granule_id: str) -> tuple[str | None, str | None, str | None]:
    parts = granule_id.split("_")
    track = next((p for p in parts if p.isdigit() and len(p) == 3), None)
    orbit = next((p for p in parts if p.upper() in {"A", "D", "ASCENDING", "DESCENDING"}), None)
    polarization = next((p.upper() for p in parts if p.upper() in {"HH", "HV", "VH", "VV"}), None)
    return track, orbit, polarization


def run_backscatter_analysis(bbox, product: Product, before_id: str | None, after_id: str | None,
                             polarization: str | None = None) -> tuple[str, dict]:
    bbox = validate_bbox(*bbox)
    if product not in {Product.GCOV, Product.GSLC}:
        raise ValueError("Backscatter analysis accepts GCOV or GSLC only.")
    provider = EarthaccessProvider()
    observations, granules = provider.search_granules(bbox, [product], None, None)
    if before_id and after_id:
        selected = {o.granule_id: o for o in observations}
        if before_id not in selected or after_id not in selected:
            raise ValueError("Both requested backscatter granules must be found in the live NASA catalog.")
        pair = [selected[before_id], selected[after_id]]
    else:
        groups: dict[tuple[str | None, str | None], list] = {}
        for observation in observations:
            track, orbit, _ = _pair_metadata(observation.granule_id)
            groups.setdefault((track, orbit), []).append(observation)
        eligible = [items for items in groups.values() if len(items) >= 2]
        pair = sorted(eligible, key=lambda items: items[-1].acquisition_start or "")[-1][-2:] if eligible else []
    if len(pair) != 2:
        raise ValueError("At least two backscatter acquisitions are required.")
    if pair[0].granule_id == pair[1].granule_id:
        raise ValueError("Before and after granules must be different.")
    before_meta = _pair_metadata(pair[0].granule_id)
    after_meta = _pair_metadata(pair[1].granule_id)
    if before_meta[0] and after_meta[0] and before_meta[0] != after_meta[0]:
        raise ValueError("Before and after acquisitions must use the same track.")
    if before_meta[1] and after_meta[1] and before_meta[1] != after_meta[1]:
        raise ValueError("Before and after acquisitions must use the same orbit direction.")
    with tempfile.TemporaryDirectory(prefix="earth-pulse-backscatter-") as folder:
        paths = provider.download_granules([granules[o.granule_id] for o in pair], Path(folder))
        before = process_backscatter(paths[pair[0].granule_id], bbox, polarization)
        after = process_backscatter(paths[pair[1].granule_id], bbox, before[3])
    if before[3] != after[3]:
        raise ValueError("Before and after acquisitions must use the same polarization.")
    before_db = power_to_db(multilook_mean(before[0], settings.backscatter_multilook_factor))
    after_db = power_to_db(multilook_mean(after[0], settings.backscatter_multilook_factor))
    valid = np.isfinite(before_db) & np.isfinite(after_db)
    pixel_area = abs(before[1][1] * before[1][5]) * settings.backscatter_multilook_factor ** 2 / 1_000_000
    summary = summarize_backscatter(before_db, after_db, valid, pixel_area,
                                    settings.backscatter_threshold_db, settings.backscatter_z_threshold)
    zones = extract_backscatter_zones(after_db - before_db, valid, settings.backscatter_threshold_db,
                                      before[1], before[2], settings.min_zone_area_km2,
                                      settings.backscatter_z_threshold)
    result = {
        "change_type": "potential_land_surface_disturbance", "product": product.value,
        "measurement": "backscatter_difference", "unit": "dB", "polarization": before[3],
        "before_granule_id": pair[0].granule_id, "after_granule_id": pair[1].granule_id,
        "before_date": _date(pair[0].granule_id), "after_date": _date(pair[1].granule_id),
        "mean_db_change": summary.mean_db_change, "affected_area_km2": summary.affected_area_km2,
        "threshold_db": summary.threshold_db, "valid_fraction": summary.valid_fraction,
        "statistical_rule": f"absolute change >= {settings.backscatter_threshold_db} dB"
        + (f" and robust |z| >= {settings.backscatter_z_threshold}" if settings.backscatter_z_threshold else ""),
        "zones": zones, "status": summary.status, "message": summary.message,
        "before_overlay_url": None, "after_overlay_url": None,
        "processing_notes": [f"Signal dataset discovered from real file: {before[4]}.",
                             "Converted linear radar power/intensity to 10*log10(power) dB.",
                             f"Multilook factor: {settings.backscatter_multilook_factor}."],
        "limitations": ["Potential land-surface disturbance, not a confirmed event.",
                        "Speckle, geometry, moisture, vegetation, and acquisition conditions can change backscatter.",
                        "Same track, orbit direction, polarization, and product are required.",
                        "Threshold is a configurable screening rule, not an engineering rating."],
    }
    analysis_id = str(uuid.uuid4())
    BACKSCATTER_RESULTS[analysis_id] = result
    return analysis_id, result


def get_backscatter_result(analysis_id: str) -> dict:
    if analysis_id not in BACKSCATTER_RESULTS:
        raise KeyError(f"Analysis {analysis_id} was not found.")
    return BACKSCATTER_RESULTS[analysis_id]
