"""Property-based tests for electrical.transformer_loading."""

from __future__ import annotations

import math
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_S = st.floats(min_value=1e3, max_value=1e8, allow_nan=False, allow_infinity=False)
_RATIO = st.floats(min_value=0.01, max_value=2.0, allow_nan=False, allow_infinity=False)


@settings(deadline=None)
@given(rated=_S, ratio=_RATIO)
def test_loading_percent_is_100_times_ratio(rated: float, ratio: float) -> None:
    load = rated * ratio
    out = implementation.execute(
        {
            "rated_apparent_power": {"value": rated, "unit": "W"},
            "load_type": "apparent_power",
            "load_apparent_power": {"value": load, "unit": "W"},
        }
    )["result"]
    assert math.isclose(out["loading_percent"], 100.0 * ratio, rel_tol=1e-9)
    assert math.isclose(out["headroom"]["value"], rated - load, rel_tol=1e-9)


@settings(deadline=None)
@given(rated=_S, ratio=_RATIO)
def test_headroom_plus_load_equals_rated(rated: float, ratio: float) -> None:
    load = rated * ratio
    out = implementation.execute(
        {
            "rated_apparent_power": {"value": rated, "unit": "W"},
            "load_type": "apparent_power",
            "load_apparent_power": {"value": load, "unit": "W"},
        }
    )["result"]
    assert math.isclose(
        out["headroom"]["value"] + out["load_apparent_power"]["value"],
        rated,
        rel_tol=1e-9,
    )
