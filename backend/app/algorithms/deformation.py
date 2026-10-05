from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import pi
from typing import Any

import numpy as np


@dataclass(frozen=True)
class DisplacementSummary:
    mean: float | None
    median: float | None
    max: float | None
    min: float | None
    std: float | None
    valid_fraction: float
    affected_area_km2: float
    threshold_mm: float
    status: str
    message: str | None = None


def phase_to_los_mm(unwrapped_phase_rad: np.ndarray, wavelength_m: float, sign: int = 1) -> np.ndarray:
    """Convert unwrapped phase to LOS displacement in mm.

    The observed GUNW file stores phase in radians and does not provide a
    sign-convention attribute. Earth Pulse uses the standard InSAR convention
    for this conversion: positive LOS displacement means motion toward the
    satellite. The caller must obtain ``wavelength_m`` from file metadata.
    """
    if wavelength_m <= 0 or sign not in {-1, 1}:
        raise ValueError("wavelength_m must be positive and sign must be +1 or -1.")
    return sign * np.asarray(unwrapped_phase_rad, dtype=np.float64) * wavelength_m / (4 * pi) * 1000


def build_quality_mask(
    coherence: np.ndarray,
    connected_components: np.ndarray,
    coh_threshold: float,
    require_main_component: bool = True,
) -> np.ndarray:
    coherence = np.asarray(coherence)
    components = np.asarray(connected_components)
    if coherence.shape != components.shape:
        raise ValueError("coherence and connected_components must have the same shape.")
    if not 0 <= coh_threshold <= 1:
        raise ValueError("coh_threshold must be between 0 and 1.")
    mask = np.isfinite(coherence) & (coherence >= coh_threshold) & (components > 0)
    if require_main_component:
        mask &= components == 1
    return mask


def reference_to_stable_area(
    disp: np.ndarray,
    mask: np.ndarray,
    method: str = "median_high_coherence",
    manual_point: tuple[int, int] | None = None,
) -> tuple[np.ndarray, float]:
    values = np.asarray(disp, dtype=np.float64)
    valid = np.asarray(mask, dtype=bool) & np.isfinite(values)
    if not valid.any():
        raise ValueError("No valid pixels are available for reference estimation.")
    if method == "median_high_coherence":
        reference = float(np.median(values[valid]))
    elif method == "manual_point":
        if manual_point is None:
            raise ValueError("manual_point is required when reference_method is manual_point.")
        row, col = manual_point
        if not (0 <= row < values.shape[0] and 0 <= col < values.shape[1]) or not valid[row, col]:
            raise ValueError("manual_point is outside the valid analysis area.")
        reference = float(values[row, col])
    else:
        raise ValueError(f"Unsupported reference method: {method}")
    return np.where(np.isfinite(values), values - reference, np.nan), reference


def summarize(disp: np.ndarray, mask: np.ndarray, pixel_area_km2: float, threshold_mm: float) -> DisplacementSummary:
    values = np.asarray(disp, dtype=np.float64)
    valid = np.asarray(mask, dtype=bool) & np.isfinite(values)
    valid_fraction = float(valid.mean()) if valid.size else 0.0
    if not valid.any():
        return DisplacementSummary(None, None, None, None, None, valid_fraction, 0.0, threshold_mm, "insufficient",
                                   "Insufficient data for reliable analysis.")
    selected = values[valid]
    affected = np.abs(selected) >= threshold_mm
    return DisplacementSummary(
        mean=float(np.mean(selected)), median=float(np.median(selected)),
        max=float(np.max(selected)), min=float(np.min(selected)), std=float(np.std(selected)),
        valid_fraction=valid_fraction, affected_area_km2=float(affected.sum() * pixel_area_km2),
        threshold_mm=threshold_mm, status="ok",
    )


def extract_change_zones(
    disp: np.ndarray,
    mask: np.ndarray,
    threshold_mm: float,
    transform: tuple[float, float, float, float, float, float],
    crs: int,
    min_zone_area_km2: float = 0.01,
) -> dict[str, Any]:
    """Return connected threshold blobs as GeoJSON polygons in EPSG:4326.

    Rectangular pixel rings are deliberately used instead of treating a radar
    raster as a point cloud. The transform is affine pixel-to-CRS coordinates.
    """
    from pyproj import Transformer

    values = np.asarray(disp)
    valid = np.asarray(mask, dtype=bool) & np.isfinite(values) & (np.abs(values) >= threshold_mm)
    rows, cols = valid.shape
    seen: set[tuple[int, int]] = set()
    transformer = Transformer.from_crs(crs, 4326, always_xy=True)
    features = []
    pixel_area_m2 = abs(transform[1] * transform[5] - transform[2] * transform[4])
    min_pixels = max(1, int(np.ceil(min_zone_area_km2 * 1_000_000 / pixel_area_m2)))
    for start in zip(*np.where(valid)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component = []
        while stack:
            r, c = stack.pop()
            component.append((int(r), int(c)))
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if 0 <= nr < rows and 0 <= nc < cols and valid[nr, nc] and (nr, nc) not in seen:
                    seen.add((nr, nc))
                    stack.append((nr, nc))
        if len(component) < min_pixels:
            continue
        polygons = []
        for r, c in component:
            x0 = transform[0] + c * transform[1] + r * transform[2]
            y0 = transform[3] + c * transform[4] + r * transform[5]
            corners = [(x0, y0), (x0 + transform[1], y0 + transform[4]),
                       (x0 + transform[1] + transform[2], y0 + transform[4] + transform[5]),
                       (x0 + transform[2], y0 + transform[5]), (x0, y0)]
            polygons.extend(corners[:-1])
        # A MultiPolygon preserves disconnected pixel squares without claiming
        # that their bounding box is physically affected.
        coords = []
        for r, c in component:
            x0 = transform[0] + c * transform[1] + r * transform[2]
            y0 = transform[3] + c * transform[4] + r * transform[5]
            ring = [[*transformer.transform(x, y)] for x, y in
                    [(x0, y0), (x0 + transform[1], y0 + transform[4]),
                     (x0 + transform[1] + transform[2], y0 + transform[4] + transform[5]),
                     (x0 + transform[2], y0 + transform[5]), (x0, y0)]]
            coords.append([ring])
        features.append({"type": "Feature", "properties": {"pixel_count": len(component),
                         "area_km2": len(component) * pixel_area_m2 / 1_000_000},
                         "geometry": {"type": "MultiPolygon", "coordinates": coords}})
    return {"type": "FeatureCollection", "features": features, "crs": {"type": "name",
            "properties": {"name": "EPSG:4326"}}}


def _granule_parts(granule_id: str) -> dict[str, str]:
    import re
    match = re.search(r"_(\d{8}T\d{6})_(\d{8}T\d{6})_(\d{8}T\d{6})_(\d{8}T\d{6})_", granule_id)
    if not match:
        raise ValueError(f"Cannot parse reference and secondary dates from granule ID: {granule_id}")
    parts = granule_id.split("_")
    return {"reference_start": match.group(1), "reference_end": match.group(2),
            "secondary_start": match.group(3), "secondary_end": match.group(4),
            "track": parts[5] if len(parts) > 5 else "", "frame": parts[7] if len(parts) > 7 else "",
            "orbit_direction": parts[6] if len(parts) > 6 else ""}


def parse_granule_dates(granule_id: str) -> dict[str, str]:
    return _granule_parts(granule_id)


def chain_time_series(pairs: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    ordered = sorted(pairs, key=lambda p: _granule_parts(p["granule_id"])["reference_start"])
    segments: list[list[dict[str, Any]]] = []
    for pair in ordered:
        meta = _granule_parts(pair["granule_id"])
        if not segments:
            segments.append([pair])
            continue
        previous = segments[-1][-1]
        prev_meta = _granule_parts(previous["granule_id"])
        if all(meta[k] == prev_meta[k] for k in ("track", "frame", "orbit_direction")) and \
                meta["reference_start"] == prev_meta["secondary_start"]:
            segments[-1].append(pair)
        else:
            segments.append([pair])
    return segments


def confidence_from(valid_fraction: float, mean_coherence: float | None, threshold_min: float = 0.1) -> tuple[str, list[str]]:
    reasons = []
    if valid_fraction < threshold_min:
        return "insufficient", ["Valid pixel fraction is below the configured minimum.", "Insufficient data for reliable analysis."]
    if mean_coherence is None or mean_coherence < 0.5:
        reasons.append("Mean coherence is low.")
    if valid_fraction >= 0.5 and mean_coherence is not None and mean_coherence >= 0.7:
        return "high", ["Valid coverage and coherence meet the high-confidence rules."]
    if valid_fraction >= 0.25 and mean_coherence is not None and mean_coherence >= 0.5:
        return "medium", reasons or ["Coverage is adequate but not high."]
    return "low", reasons or ["Valid coverage is limited."]
