"""chemistry.batch_kinetics — thin adapter for A→B batch Euler step."""

from __future__ import annotations

from typing import Any

from oec.chemistry import Composition, Species, batch_extent_euler_step
from oec.chemistry.stoichiometry import Reaction


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    a = Species(id="A", name="A", formula={"C": 1})
    b = Species(id="B", name="B", formula={"C": 1})
    rxn = Reaction(
        id="a_to_b",
        name="A to B",
        nu={"A": -1.0, "B": 1.0},
        species={"A": a, "B": b},
    )
    comp = Composition(amounts_mol={"A": float(inputs["a_mol"]), "B": float(inputs["b_mol"])})
    step = batch_extent_euler_step(
        rxn,
        comp,
        k=float(inputs["k"]),
        orders={"A": 1.0},
        volume_m3=float(inputs["volume_m3"]),
        dt_s=float(inputs["dt_s"]),
    )
    return {
        "result": {
            "extent_step_mol": step.extent_step_mol,
            "rate_mol_per_m3_s": step.rate_mol_per_m3_s,
            "amounts_mol": dict(step.composition.amounts_mol),
            "dt_s": step.dt_s,
        },
        "diagnostics": {},
    }
