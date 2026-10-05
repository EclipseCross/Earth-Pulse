from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import h5py


GRID = "science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram"
PHASE = f"{GRID}/HH/unwrappedPhase"
COHERENCE = f"{GRID}/HH/coherenceMagnitude"
MASK = f"{GRID}/mask"
PROJECTION = f"{GRID}/projection"


@dataclass(frozen=True)
class GUNWLayout:
    phase_path: str
    coherence_path: str
    mask_path: str
    projection_path: str
    shape: tuple[int, int]
    phase_units: str
    coherence_units: str
    projection_epsg: int


def _text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def inspect_gunw_layout(path: Path) -> GUNWLayout:
    """Validate the observed Phase 3 GUNW structure without loading rasters."""
    with h5py.File(path, "r") as handle:
        missing = [name for name in (PHASE, COHERENCE, MASK, PROJECTION) if name not in handle]
        if missing:
            raise ValueError(f"GUNW file is missing required datasets: {', '.join(missing)}")

        phase = handle[PHASE]
        coherence = handle[COHERENCE]
        mask = handle[MASK]
        projection = handle[PROJECTION]
        if phase.ndim != 2 or coherence.shape != phase.shape or mask.shape != phase.shape:
            raise ValueError("GUNW phase, coherence, and mask rasters do not have compatible shapes.")
        if phase.dtype.kind != "f" or coherence.dtype.kind != "f" or mask.dtype.kind not in "ui":
            raise ValueError("GUNW phase/coherence/mask dtypes do not match the observed layout.")

        epsg = projection.attrs.get("epsg_code", projection[()])
        return GUNWLayout(
            phase_path=PHASE,
            coherence_path=COHERENCE,
            mask_path=MASK,
            projection_path=PROJECTION,
            shape=tuple(int(value) for value in phase.shape),
            phase_units=_text(phase.attrs.get("units", "")),
            coherence_units=_text(coherence.attrs.get("units", "")),
            projection_epsg=int(epsg),
        )
