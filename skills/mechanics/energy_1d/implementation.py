"""mechanics.energy_1d entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Thin adapter (skill-first,
per plan section 8): validates/adapts inputs into ``QuantityValue``s and
calls ``oec.physics.mechanics``. This module performs **no** physics
arithmetic of its own — every computation (energies, deltas and the
work-energy balance) is delegated to ``oec.physics.mechanics``.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.mechanics import (
    STANDARD_GRAVITY,
    kinetic_energy,
    mechanical_energy_balance,
    mechanical_energy_deltas,
    potential_energy,
)

_ZERO_JOULES = QuantityValue(value=0.0, unit="J")


def _qv(field: dict[str, Any]) -> QuantityValue:
    return QuantityValue(value=float(field["value"]), unit=field["unit"])


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    mass = _qv(inputs["mass"])
    height_initial = _qv(inputs["height_initial"])
    height_final = _qv(inputs["height_final"])
    velocity_initial = _qv(inputs["velocity_initial"])
    velocity_final = _qv(inputs["velocity_final"])
    gravity = _qv(inputs["gravity"]) if "gravity" in inputs else STANDARD_GRAVITY
    work_in = _qv(inputs["work_in"]) if "work_in" in inputs else _ZERO_JOULES
    losses = _qv(inputs["losses"]) if "losses" in inputs else _ZERO_JOULES

    ke_initial = kinetic_energy(mass, velocity_initial)
    ke_final = kinetic_energy(mass, velocity_final)
    pe_initial = potential_energy(mass, height_initial, gravity)
    pe_final = potential_energy(mass, height_final, gravity)

    delta_kinetic, delta_potential = mechanical_energy_deltas(
        ke_initial, ke_final, pe_initial, pe_final
    )

    balance = mechanical_energy_balance(work_in, delta_kinetic, delta_potential, losses)

    return {
        "result": {
            "kinetic_energy_initial": ke_initial.model_dump(mode="json"),
            "kinetic_energy_final": ke_final.model_dump(mode="json"),
            "potential_energy_initial": pe_initial.model_dump(mode="json"),
            "potential_energy_final": pe_final.model_dump(mode="json"),
            "delta_kinetic": delta_kinetic.model_dump(mode="json"),
            "delta_potential": delta_potential.model_dump(mode="json"),
            "balance": balance.model_dump(mode="json"),
        },
        "diagnostics": {},
    }
