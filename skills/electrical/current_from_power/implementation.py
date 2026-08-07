"""electrical.current_from_power entrypoint.

Runs inside the sandboxed subprocess (ADR 0012) — imported only by
``oec.execution.runner``, never by the Skill Loader or the parent
process.

Closed-form, not iterative (``method.iterative: false``): see
``skill.md``'s "Mathematical formulation". By the time this runs,
``ExecutionService`` has already converted ``power``/``voltage`` to
watts/volts (ADR 0016) — this module never does its own unit
conversion.
"""

from __future__ import annotations

import math
from typing import Any

_SQRT_3 = math.sqrt(3.0)


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    power = float(inputs["power"]["value"])
    power_type: str = inputs["power_type"]
    voltage = float(inputs["voltage"]["value"])
    phase_count: int = inputs["phase_count"]
    efficiency = float(inputs.get("efficiency", 1.0))

    electrical_power = power / efficiency

    if power_type == "active":
        power_factor = float(inputs["power_factor"])
        denominator = voltage * power_factor
    else:
        denominator = voltage

    if phase_count == 3:
        denominator *= _SQRT_3

    current = electrical_power / denominator

    return {
        "result": {
            "current": {"value": current, "unit": "A"},
            "electrical_power": {"value": electrical_power, "unit": "W"},
            "phase_count": phase_count,
            "power_type": power_type,
        },
        "diagnostics": {},
    }
