import h5py
import numpy as np
import pytest

from app.services.gunw_layout import (
    COHERENCE,
    MASK,
    PHASE,
    PROJECTION,
    inspect_gunw_layout,
)


def _fixture(path):
    with h5py.File(path, "w") as handle:
        for name, shape, dtype in (
            (PHASE, (2, 3), "f4"),
            (COHERENCE, (2, 3), "f4"),
            (MASK, (2, 3), "u4"),
        ):
            dataset = handle.create_dataset(name, shape=shape, dtype=dtype)
            dataset.attrs["units"] = "radians" if name == PHASE else "1"
        projection = handle.create_dataset(PROJECTION, data=np.uint32(32646))
        projection.attrs["epsg_code"] = 32646


def test_inspect_gunw_layout_validates_observed_structure(tmp_path):
    path = tmp_path / "fixture.h5"
    _fixture(path)

    result = inspect_gunw_layout(path)

    assert result.shape == (2, 3)
    assert result.phase_units == "radians"
    assert result.coherence_units == "1"
    assert result.projection_epsg == 32646


def test_inspect_gunw_layout_rejects_missing_fields(tmp_path):
    path = tmp_path / "fixture.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset(PHASE, shape=(2, 2), dtype="f4")

    with pytest.raises(ValueError, match="missing required datasets"):
        inspect_gunw_layout(path)
