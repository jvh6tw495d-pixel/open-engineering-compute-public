"""chemistry.reaction_extent — thin adapter over water_formation stoichiometry."""

from __future__ import annotations

from typing import Any

from oec.chemistry import Composition, water_formation_reaction


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    rxn = water_formation_reaction()
    initial = Composition(
        amounts_mol={
            "H2": float(inputs["h2_mol"]),
            "O2": float(inputs["o2_mol"]),
            "H2O": float(inputs["h2o_mol"]),
        }
    )
    xi = float(inputs["extent_mol"])
    final = rxn.apply_extent(initial, xi)
    return {
        "result": {
            "extent_mol": xi,
            "max_extent_mol": rxn.max_extent_mol(initial),
            "amounts_mol": dict(final.amounts_mol),
            "atom_balance_ok": all(c.balanced for c in rxn.atom_balance_check().values()),
        },
        "diagnostics": {},
    }
