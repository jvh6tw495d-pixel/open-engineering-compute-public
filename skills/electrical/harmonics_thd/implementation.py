"""electrical.harmonics_thd — thin adapter over oec.physics.harmonics."""

from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.harmonics import total_harmonic_distortion


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    fundamental = QuantityValue(**inputs["fundamental"])
    harmonics = [QuantityValue(**h) for h in inputs["harmonics"]]
    thd = total_harmonic_distortion(fundamental, harmonics)
    return {
        "result": {
            "thd": thd,
            "thd_percent": thd * 100.0,
        },
        "diagnostics": {},
    }
