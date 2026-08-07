"""chemistry.fick_flux — thin adapter over oec.chemistry.fick_flux_1d."""

from __future__ import annotations

from typing import Any

from oec.chemistry import fick_flux_1d


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    res = fick_flux_1d(
        concentration_a_mol_m3=float(inputs["concentration_a_mol_m3"]),
        concentration_b_mol_m3=float(inputs["concentration_b_mol_m3"]),
        distance_m=float(inputs["distance_m"]),
        diffusivity_m2_s=float(inputs["diffusivity_m2_s"]),
    )
    return {
        "result": {
            "flux_mol_per_m2_s": res.flux_mol_per_m2_s,
            "diffusivity_m2_s": res.diffusivity_m2_s,
            "dc_dx_mol_per_m4": res.dc_dx_mol_per_m4,
        },
        "diagnostics": {},
    }
