from __future__ import annotations

from typing import Any

from oec.physics.optics import snell_refracted_angle


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = snell_refracted_angle(
        float(inputs["n1"]), float(inputs["n2"]), float(inputs["theta1_rad"])
    )
    return {
        "result": out,
        "diagnostics": {"total_internal_reflection": out["total_internal_reflection"]},
    }
