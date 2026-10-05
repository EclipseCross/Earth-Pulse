from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
from pyproj import Transformer

from app.core.config import settings
from app.services.gunw_layout import COHERENCE, GRID, MASK, PHASE, PROJECTION

CONNECTED = f"{GRID}/HH/connectedComponents"
FREQUENCY = "science/LSAR/GUNW/grids/frequencyA/centerFrequency"
CACHE = Path(__file__).resolve().parents[2] / ".cache"


@dataclass(frozen=True)
class ProcessedGUNW:
    phase: np.ndarray
    coherence: np.ndarray
    connected_components: np.ndarray
    mask: np.ndarray
    wavelength_m: float
    transform: tuple[float, float, float, float, float, float]
    crs: int
    units: str
    processing_notes: list[str]


def _window(coords: np.ndarray, low: float, high: float) -> tuple[int, int]:
    selected = np.where((coords >= low) & (coords <= high))[0]
    if not selected.size:
        raise ValueError("The requested AOI does not overlap the GUNW grid.")
    return int(selected.min()), int(selected.max()) + 1


def _cache_key(path: Path, bbox: tuple[float, float, float, float]) -> Path:
    token = hashlib.sha256(f"{path}:{bbox}".encode()).hexdigest()
    return CACHE / f"gunw-{token}.npz"


def process_gunw(path: Path, bbox: tuple[float, float, float, float]) -> ProcessedGUNW:
    with h5py.File(path, "r") as handle:
        phase = handle[PHASE]
        x = np.asarray(handle[f"{GRID}/xCoordinates"][()])
        y = np.asarray(handle[f"{GRID}/yCoordinates"][()])
        projection = handle[PROJECTION]
        crs = int(projection.attrs.get("epsg_code", projection[()]))
        to_grid = Transformer.from_crs(4326, crs, always_xy=True)
        west, south = to_grid.transform(bbox[0], bbox[1])
        east, north = to_grid.transform(bbox[2], bbox[3])
        x0, x1 = _window(x, min(west, east), max(west, east))
        y0, y1 = _window(y, min(north, south), max(north, south))
        pixels = (x1 - x0) * (y1 - y0)
        if pixels > settings.max_processing_pixels:
            raise ValueError("Requested AOI exceeds the processing pixel limit.")
        phase_data = np.asarray(phase[y0:y1, x0:x1], dtype=np.float64)
        coherence_data = np.asarray(handle[COHERENCE][y0:y1, x0:x1], dtype=np.float64)
        components = np.asarray(handle[CONNECTED][y0:y1, x0:x1], dtype=np.uint16)
        packed_mask = np.asarray(handle[MASK][y0:y1, x0:x1], dtype=np.uint32)
        center_frequency = float(handle[FREQUENCY][()])
        if center_frequency <= 0:
            raise ValueError("GUNW center frequency metadata is invalid.")
        wavelength = 299_792_458.0 / center_frequency
        dx = float(handle[f"{GRID}/xCoordinateSpacing"][()])
        dy = float(handle[f"{GRID}/yCoordinateSpacing"][()])
        transform = (float(x[x0]), dx, 0.0, float(y[y0]), 0.0, dy)
        units = str(phase.attrs.get("units", ""))
        if units != "radians":
            raise ValueError(f"Unexpected GUNW phase units: {units or 'missing'}.")
    if not np.isfinite(phase_data).any():
        raise ValueError("The requested GUNW AOI contains only nodata.")
    return ProcessedGUNW(
        phase=phase_data, coherence=coherence_data, connected_components=components,
        mask=packed_mask, wavelength_m=wavelength, transform=transform, crs=crs,
        units=units, processing_notes=[
            "Read only the requested AOI window from the real GUNW HDF5 file.",
            f"Wavelength derived from {FREQUENCY} centerFrequency metadata.",
            "Positive LOS displacement uses the standard toward-satellite convention; the file has no sign attribute.",
        ],
    )


def cache_processed(path: Path, bbox: tuple[float, float, float, float]) -> ProcessedGUNW:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = _cache_key(path, bbox)
    if cached.exists():
        with np.load(cached, allow_pickle=False) as data:
            return ProcessedGUNW(
                phase=data["phase"], coherence=data["coherence"], connected_components=data["components"],
                mask=data["mask"], wavelength_m=float(data["wavelength"]), transform=tuple(data["transform"]),
                crs=int(data["crs"]), units=str(data["units"]), processing_notes=list(json.loads(str(data["notes"]))),
            )
    result = process_gunw(path, bbox)
    np.savez_compressed(cached, phase=result.phase, coherence=result.coherence,
                        components=result.connected_components, mask=result.mask,
                        wavelength=result.wavelength_m, transform=result.transform, crs=result.crs,
                        units=result.units, notes=json.dumps(result.processing_notes))
    return result
