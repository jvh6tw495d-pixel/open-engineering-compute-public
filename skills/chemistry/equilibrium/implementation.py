"""chemistry.equilibrium — thin adapter for A ⇌ B Qc/Kc check."""

from __future__ import annotations

from typing import Any

from oec.chemistry import Composition, Species, evaluate_equilibrium
from oec.chemistry.stoichiometry import Reaction


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    a = Species(id="A", name="A", formula={"C": 1})
    b = Species(id="B", name="B", formula={"C": 1})
    rxn = Reaction(
        id="iso",
        name="isomerisation",
        nu={"A": -1.0, "B": 1.0},
        species={"A": a, "B": b},
    )
    comp = Composition(amounts_mol={"A": float(inputs["a_mol"]), "B": float(inputs["b_mol"])})
    eq = evaluate_equilibrium(
        rxn,
        comp,
        kc=float(inputs["kc"]),
        volume_m3=float(inputs["volume_m3"]),
    )
    return {
        "result": {
            "qc": eq.qc,
            "kc": eq.kc,
            "driving_force": eq.driving_force,
            "at_equilibrium": eq.at_equilibrium,
        },
        "diagnostics": {},
    }
