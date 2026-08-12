"""W3 chemistry thermochemistry foundations."""

from __future__ import annotations

import pytest

from oec.chemistry.thermochemistry import hess_reaction_enthalpy, vanthoff_k2


def test_vanthoff_endothermic_increases_k() -> None:
    out = vanthoff_k2(k1=1.0, t1_k=298.15, t2_k=310.15, delta_h_j_per_mol=50_000.0)
    assert out["k2"] > 1.0


def test_vanthoff_isothermal_identity() -> None:
    out = vanthoff_k2(k1=2.5, t1_k=300.0, t2_k=300.0, delta_h_j_per_mol=12_000.0)
    assert out["k2"] == pytest.approx(2.5, rel=1e-12)


def test_hess_sum() -> None:
    out = hess_reaction_enthalpy(
        [
            {"delta_h_j_per_mol": -100.0, "coefficient": 1.0},
            {"delta_h_j_per_mol": 40.0, "coefficient": -1.0},
        ]
    )
    assert out["delta_h_j_per_mol"] == pytest.approx(-140.0)
