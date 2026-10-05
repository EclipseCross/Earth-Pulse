from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

import numpy as np

from app.algorithms.deformation import (
    build_quality_mask,
    confidence_from,
    extract_change_zones,
    parse_granule_dates,
    phase_to_los_mm,
    reference_to_stable_area,
    summarize,
)
from app.core.config import settings
from app.models.observation import Product
from app.services.nisar_service import EarthaccessProvider
from app.services.processing_service import cache_processed
from app.utils.geo import InvalidAOI, point_to_bbox, validate_bbox, validate_point

RESULTS: dict[str, dict] = {}


def _date(value: str) -> str:
    return datetime.strptime(value, "%Y%m%dT%H%M%S").date().isoformat()


def _choose(observations, granules, requested):
    if requested:
        selected = [o for o in observations if o.granule_id in requested]
        if len(selected) != len(requested):
            raise ValueError("One or more requested GUNW granules were not found in the live NASA catalog.")
    else:
        selected = observations[-1:] if observations else []
    if not selected:
        raise ValueError("No GUNW granules were found for this AOI and date range.")
    return selected, [granules[o.granule_id] for o in selected]


def run_ground_analysis(bbox, granule_ids: list[str] | None = None) -> tuple[str, dict]:
    provider = EarthaccessProvider()
    observations, granules = provider.search_granules(bbox, [Product.GUNW], None, None)
    selected, records = _choose(observations, granules, granule_ids)
    with __import__("tempfile").TemporaryDirectory(prefix="earth-pulse-gunw-") as folder:
        paths = provider.download_granules(records, Path(folder))
        processed = cache_processed(paths[selected[0].granule_id], bbox)

    quality = build_quality_mask(
        processed.coherence, processed.connected_components,
        settings.coherence_threshold, settings.require_main_component,
    )
    quality &= processed.mask != 255
    quality &= (processed.mask & 0xFF) != 0
    los = phase_to_los_mm(processed.phase, processed.wavelength_m)
    referenced, reference_value = reference_to_stable_area(los, quality, settings.reference_method)
    pixel_area = abs(processed.transform[1] * processed.transform[5]) / 1_000_000
    summary = summarize(referenced, quality, pixel_area, settings.displacement_threshold_mm)
    mean_coherence = float(np.mean(processed.coherence[quality])) if quality.any() else None
    confidence, reasons = confidence_from(summary.valid_fraction, mean_coherence, settings.min_valid_fraction)
    if summary.valid_fraction < settings.min_valid_fraction:
        confidence = "insufficient"
        reasons = ["Valid pixel fraction is below the configured minimum.", "Insufficient data for reliable analysis."]
    metadata = parse_granule_dates(selected[0].granule_id)
    zones = extract_change_zones(
        referenced, quality, settings.displacement_threshold_mm,
        processed.transform, processed.crs, settings.min_zone_area_km2,
    ) if confidence != "insufficient" else {"type": "FeatureCollection", "features": []}
    result = {
        "change_type": "ground_deformation",
        "measurement": "line_of_sight_displacement",
        "unit": "mm",
        "mean": summary.mean if confidence != "insufficient" else None,
        "median": summary.median if confidence != "insufficient" else None,
        "max": summary.max if confidence != "insufficient" else None,
        "min": summary.min if confidence != "insufficient" else None,
        "std": summary.std if confidence != "insufficient" else None,
        "affected_area_km2": summary.affected_area_km2 if confidence != "insufficient" else None,
        "threshold_mm": settings.displacement_threshold_mm,
        "coherence_mean": mean_coherence,
        "coherence_threshold": settings.coherence_threshold,
        "valid_fraction": summary.valid_fraction,
        "reference_method": settings.reference_method,
        "reference_value_mm": reference_value if confidence != "insufficient" else None,
        "granule_ids": [selected[0].granule_id],
        "reference_acquisition_date": _date(metadata["reference_start"]),
        "secondary_acquisition_date": _date(metadata["secondary_start"]),
        "track": metadata["track"], "frame": metadata["frame"],
        "orbit_direction": metadata["orbit_direction"],
        "wavelength_m": processed.wavelength_m,
        "sign_convention": "positive = motion toward satellite (standard InSAR convention; no sign attribute was present in this file)",
        "processing_notes": processed.processing_notes + [
            f"Quality mask: coherence >= {settings.coherence_threshold}, connected component == 1, valid packed mask.",
            f"Reference removed using {settings.reference_method}.",
        ],
        "limitations": [
            "LOS only; relative to a reference area, not vertical motion.",
            "Phase unwrapping errors are possible; connected components were quality-filtered.",
            "Atmospheric troposphere and ionosphere effects can resemble motion.",
            "Low coherence occurs over snow, ice, water, or dense vegetation.",
            "Moving glacier ice is not ground deformation.",
            "A 12-day pair is a short observation span.",
            "This is a screening result, not an engineering or NASA risk rating.",
        ],
        "confidence": confidence,
        "confidence_reasons": reasons,
        "status": "insufficient" if confidence == "insufficient" else "ok",
        "message": "Insufficient data for reliable analysis." if confidence == "insufficient" else None,
        "zones": zones,
    }
    analysis_id = str(uuid.uuid4())
    RESULTS[analysis_id] = result
    return analysis_id, result


def get_result(analysis_id: str) -> dict:
    try:
        return RESULTS[analysis_id]
    except KeyError as exc:
        raise KeyError(f"Analysis {analysis_id} was not found.") from exc
