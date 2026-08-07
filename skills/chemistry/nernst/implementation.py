"""chemistry.nernst — thin adapter over oec.chemistry.nernst_potential."""

from __future__ import annotations

from typing import Any

from oec.chemistry import nernst_potential


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    res = nernst_potential(
        e0_v=float(inputs["e0_v"]),
        n_electrons=int(inputs["n_electrons"]),
        reaction_quotient=float(inputs["reaction_quotient"]),
        temperature_k=float(inputs.get("temperature_k", 298.15)),
    )
    return {
        "result": {
            "e_v": res.e_v,
            "e0_v": res.e0_v,
            "n_electrons": res.n_electrons,
            "temperature_k": res.temperature_k,
            "reaction_quotient": res.reaction_quotient,
        },
        "diagnostics": {},
    }
