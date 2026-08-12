from __future__ import annotations

from typing import Any

from oec.chemistry.thermochemistry import hess_reaction_enthalpy


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = hess_reaction_enthalpy(list(inputs["steps"]))
    assumptions = [a.text if hasattr(a, "text") else str(a) for a in out["assumptions"]]
    return {
        "result": {
            "delta_h_j_per_mol": out["delta_h_j_per_mol"],
            "n_steps": out["n_steps"],
            "assumptions": assumptions,
        },
        "diagnostics": {},
    }
