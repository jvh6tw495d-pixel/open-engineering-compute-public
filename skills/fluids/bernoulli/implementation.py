"""fluids.bernoulli entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Thin adapter (skill-first,
per plan section 8): validates/adapts inputs into ``QuantityValue``s and
calls ``oec.physics.fluids``. This module performs no physics arithmetic
of its own.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.fluids import bernoulli_balance, bernoulli_head, darcy_weisbach_head_loss
from oec.physics.mechanics import STANDARD_GRAVITY


def _qv(field: dict[str, Any]) -> QuantityValue:
    return QuantityValue(value=float(field["value"]), unit=field["unit"])


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    density = _qv(inputs["density"])
    gravity = _qv(inputs["gravity"]) if "gravity" in inputs else STANDARD_GRAVITY

    velocity_upstream = _qv(inputs["velocity_upstream"])
    head_upstream = bernoulli_head(
        _qv(inputs["pressure_upstream"]),
        velocity_upstream,
        _qv(inputs["elevation_upstream"]),
        density,
        gravity,
    )
    head_downstream = bernoulli_head(
        _qv(inputs["pressure_downstream"]),
        _qv(inputs["velocity_downstream"]),
        _qv(inputs["elevation_downstream"]),
        density,
        gravity,
    )
    head_loss = darcy_weisbach_head_loss(
        float(inputs["friction_factor"]),
        _qv(inputs["length"]),
        _qv(inputs["diameter"]),
        velocity_upstream,
        gravity,
    )

    balance = bernoulli_balance(head_upstream, head_downstream, head_loss)

    return {
        "result": {
            "head_upstream": head_upstream.model_dump(mode="json"),
            "head_downstream": head_downstream.model_dump(mode="json"),
            "head_loss": head_loss.model_dump(mode="json"),
            "balance": balance.model_dump(mode="json"),
        },
        "diagnostics": {},
    }
