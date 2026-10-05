from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class BackscatterSummary:
    mean_db_change: float | None
    valid_fraction: float
    affected_area_km2: float
    threshold_db: float
    status: str
    message: str | None = None


def power_to_db(power: np.ndarray, floor: float = 1e-10) -> np.ndarray:
    """Convert linear radar power/intensity to dB without taking log of zero."""
    if floor <= 0:
        raise ValueError("The power floor must be positive.")
    values = np.asarray(power, dtype=np.float64)
    return 10.0 * np.log10(np.maximum(values, floor))


def multilook_mean(values: np.ndarray, factor: int) -> np.ndarray:
    """Block-average complete square windows; factor 1 leaves the raster unchanged."""
    if factor < 1:
        raise ValueError("The multilook factor must be at least 1.")
    values = np.asarray(values, dtype=np.float64)
    if factor == 1:
        return values.copy()
    rows, cols = values.shape
    rows -= rows % factor
    cols -= cols % factor
    if rows == 0 or cols == 0:
        raise ValueError("The multilook factor is larger than the raster.")
    return values[:rows, :cols].reshape(rows // factor, factor, cols // factor, factor).mean((1, 3))


def robust_z_score(change_db: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Return robust z scores using median and MAD over valid pixels."""
    values = np.asarray(change_db, dtype=np.float64)
    valid = np.asarray(valid, dtype=bool) & np.isfinite(values)
    if not valid.any():
        return np.full(values.shape, np.nan)
    median = float(np.median(values[valid]))
    mad = float(np.median(np.abs(values[valid] - median)))
    scale = 1.4826 * mad
    if scale == 0:
        return np.where(valid, np.where(values == median, 0.0, np.inf), np.nan)
    return np.where(valid, (values - median) / scale, np.nan)


def summarize_backscatter(
    before_db: np.ndarray,
    after_db: np.ndarray,
    valid: np.ndarray,
    pixel_area_km2: float,
    threshold_db: float,
    z_threshold: float | None = None,
) -> BackscatterSummary:
    before = np.asarray(before_db, dtype=np.float64)
    after = np.asarray(after_db, dtype=np.float64)
    valid = np.asarray(valid, dtype=bool) & np.isfinite(before) & np.isfinite(after)
    if before.shape != after.shape or before.shape != valid.shape:
        raise ValueError("Before, after, and valid arrays must have the same shape.")
    fraction = float(valid.mean()) if valid.size else 0.0
    if not valid.any():
        return BackscatterSummary(None, fraction, 0.0, threshold_db, "insufficient",
                                  "Insufficient data for reliable analysis.")
    change = after - before
    significant = np.abs(change) >= threshold_db
    if z_threshold is not None:
        significant &= np.abs(robust_z_score(change, valid)) >= z_threshold
    return BackscatterSummary(
        mean_db_change=float(np.mean(change[valid])),
        valid_fraction=fraction,
        affected_area_km2=float(np.count_nonzero(significant & valid) * pixel_area_km2),
        threshold_db=threshold_db,
        status="ok",
    )


def extract_backscatter_zones(
    change_db: np.ndarray,
    valid: np.ndarray,
    threshold_db: float,
    transform: tuple[float, float, float, float, float, float],
    crs: int,
    min_zone_area_km2: float,
    z_threshold: float | None = None,
) -> dict[str, Any]:
    from app.algorithms.deformation import extract_change_zones

    change = np.asarray(change_db, dtype=np.float64)
    valid = np.asarray(valid, dtype=bool) & np.isfinite(change)
    significant = np.abs(change) >= threshold_db
    if z_threshold is not None:
        significant &= np.abs(robust_z_score(change, valid)) >= z_threshold
    return extract_change_zones(
        change, valid & significant, 0.0, transform, crs, min_zone_area_km2,
    )
