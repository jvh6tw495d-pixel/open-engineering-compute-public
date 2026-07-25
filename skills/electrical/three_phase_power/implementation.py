"""electrical.three_phase_power entrypoint.

Runs inside the sandboxed subprocess (ADR 0012) — imported only by
``oec.execution.runner``, never by the Skill Loader or the parent
process.

Closed-form, not iterative (``method.iterative: false``): the standard
balanced three-phase power identities (see ``skill.md``'s "Mathematical
formulation"). By the time this runs, ``ExecutionService`` has already
converted ``voltage_line_to_line``/``current_line`` to volts/amps
(ADR 0016) — this module never does its own unit conversion.
"""

from __future__ import annotations

import math
from typing import Any

_SQRT_3 = math.sqrt(3.0)


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    voltage = float(inputs["voltage_line_to_line"]["value"])
    current = float(inputs["current_line"]["value"])
    power_factor = float(inputs["power_factor"])
    power_factor_type: str = inputs.get("power_factor_type", "lagging")

    apparent_power = _SQRT_3 * voltage * current
    active_power = apparent_power * power_factor
    reactive_magnitude = apparent_power * math.sin(math.acos(power_factor))
    reactive_power = reactive_magnitude if power_factor_type == "lagging" else -reactive_magnitude

    return {
        "result": {
            "active_power": {"value": active_power, "unit": "W"},
            "reactive_power": {"value": reactive_power, "unit": "var"},
            "apparent_power": {"value": apparent_power, "unit": "VA"},
            "power_factor": power_factor,
            "power_factor_type": power_factor_type,
        },
        "diagnostics": {},
    }
