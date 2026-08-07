"""thermal.conduction_1d entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Thin adapter (skill-first,
per plan section 8): validates/adapts inputs into ``QuantityValue``s and
calls ``oec.physics.thermal``. This module performs no physics arithmetic
of its own.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.thermal import conduction_heat_rate, steady_conduction_balance


def _qv(field: dict[str, Any]) -> QuantityValue:
    return QuantityValue(value=float(field["value"]), unit=field["unit"])


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    conductivity = _qv(inputs["conductivity"])
    area = _qv(inputs["area"])
    length = _qv(inputs["length"])
    hot_temperature = _qv(inputs["hot_temperature"])
    cold_temperature = _qv(inputs["cold_temperature"])

    heat_rate = conduction_heat_rate(conductivity, area, length, hot_temperature, cold_temperature)
    heat_out = _qv(inputs["heat_out"]) if "heat_out" in inputs else heat_rate

    balance = steady_conduction_balance(heat_in=heat_rate, heat_out=heat_out)

    return {
        "result": {
            "heat_rate": heat_rate.model_dump(mode="json"),
            "balance": balance.model_dump(mode="json"),
        },
        "diagnostics": {},
    }
