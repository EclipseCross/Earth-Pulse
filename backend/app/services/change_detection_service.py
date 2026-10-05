from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np

from app.models.analysis import ChangeAnalysisResult
from app.models.observation import Observation, Product
from app.services.nisar_service import EarthaccessProvider
from app.utils.geo import point_to_bbox


def _date(value: str | None) -> str | None:
    return value[:10] if value else None


def _numeric_layers(path: Path) -> dict[str, np.ndarray]:
    layers: dict[str, np.ndarray] = {}
    with h5py.File(path, "r") as handle:
        def visit(name: str, obj: h5py.Dataset) -> None:
            if obj.ndim < 2 or obj.dtype.kind not in "fiu":
                return
            data = np.asarray(obj[()])
            if data.size >= 16 and np.isfinite(data).any():
                layers[name] = data.astype(np.float64, copy=False)
        handle.visititems(visit)
    return layers


def _matching_layer(first: dict[str, np.ndarray], second: dict[str, np.ndarray]):
    for name, left in first.items():
        right = second.get(name)
        if right is not None and left.shape == right.shape:
            return name, left, right
    for name, left in first.items():
        for other, right in second.items():
            if left.shape == right.shape:
                return f"{name} / {other}", left, right
    raise ValueError("The granules contain no compatible numeric raster layer.")


def _metric(product: Product, left: np.ndarray, right: np.ndarray):
    valid = np.isfinite(left) & np.isfinite(right)
    if not valid.any():
        raise ValueError("The selected layer contains no overlapping finite pixels.")
    a, b = left[valid], right[valid]
    if product in {Product.GCOV, Product.GSLC}:
        relative = float(np.median(np.abs(b - a) / np.maximum(np.abs(a), np.finfo(float).eps)))
        return "median relative change", relative * 100, "%", f"The radar response changed by approximately {relative * 100:.1f}% in the selected layer."
    if product == Product.SME2:
        value = float(np.mean(b - a))
        return "mean soil-moisture difference", value, "product units", f"The later soil-moisture estimate is {value:+.3f} product units relative to the baseline."
    value = float(np.median(np.abs(b - a)))
    if product == Product.GUNW:
        return "median interferogram difference", value, "product units", f"The interferogram differs by {value:.3f} product units; this is not yet calibrated displacement in centimeters."
    return "median pixel-offset difference", value, "product units", f"The pixel-offset layer differs by {value:.3f} product units; this is not yet calibrated movement distance."


def _pick_pair(observations: list[Observation], start: str, end: str):
    dated = sorted((o for o in observations if _date(o.acquisition_start)), key=lambda o: o.acquisition_start or "")
    before = [o for o in dated if (_date(o.acquisition_start) or "") <= start]
    after = [o for o in dated if (_date(o.acquisition_start) or "") >= end]
    if not before or not after or before[-1].granule_id == after[0].granule_id:
        raise ValueError("No two distinct observations bracket the requested dates.")
    return before[-1], after[0]


def analyze(point: tuple[float, float], product: Product, start: str, end: str) -> ChangeAnalysisResult:
    try:
        datetime.strptime(start, "%Y-%m-%d")
        datetime.strptime(end, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Dates must use YYYY-MM-DD.") from exc
    if start >= end:
        raise ValueError("The comparison date must be after the baseline date.")

    provider = EarthaccessProvider()
    observations, granules = provider.search_granules(point_to_bbox(*point), [product], start, end)
    baseline, comparison = _pick_pair(observations, start, end)
    with tempfile.TemporaryDirectory(prefix="earth-pulse-") as folder:
        paths = provider.download_granules([granules[baseline.granule_id], granules[comparison.granule_id]], Path(folder))
        layer, first, second = _matching_layer(_numeric_layers(paths[baseline.granule_id]), _numeric_layers(paths[comparison.granule_id]))
        metric, value, unit, interpretation = _metric(product, first, second)
    return ChangeAnalysisResult(
        product=product,
        baseline_granule_id=baseline.granule_id,
        comparison_granule_id=comparison.granule_id,
        baseline_date=_date(baseline.acquisition_start) or start,
        comparison_date=_date(comparison.acquisition_start) or end,
        layer=layer, metric=metric, value=value, unit=unit, interpretation=interpretation,
        caveats=[
            "This is an automated screening metric, not a confirmed physical event.",
            "Product-specific geolocation and quality masks are not yet applied.",
            "Interpret the result with the relevant NISAR product specification and local context.",
        ],
    )
