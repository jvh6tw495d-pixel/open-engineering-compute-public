"""chemistry.arrhenius — thin adapter."""

from __future__ import annotations

from typing import Any

from oec.chemistry import arrhenius_rate_constant


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    res = arrhenius_rate_constant(
        pre_exponential=float(inputs["pre_exponential"]),
        activation_energy_j_per_mol=float(inputs["activation_energy_j_per_mol"]),
        temperature_k=float(inputs["temperature_k"]),
    )
    return {
        "result": {
            "k": res.k,
            "temperature_k": res.temperature_k,
            "pre_exponential": res.pre_exponential,
            "activation_energy_j_per_mol": res.activation_energy_j_per_mol,
        },
        "diagnostics": {},
        "assumptions": [a.text for a in res.assumptions],
    }
