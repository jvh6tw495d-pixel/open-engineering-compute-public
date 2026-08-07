"""Unit tests for oec.chemistry (v2.8 C1–C4 + transport)."""

from __future__ import annotations

import math

import pytest

from oec.chemistry import (
    Composition,
    Species,
    arrhenius_rate_constant,
    batch_extent_euler_step,
    equilibrium_constant_from_delta_g,
    evaluate_equilibrium,
    extent_to_equilibrium_binary,
    fick_flux_1d,
    nernst_potential,
    power_law_rate,
    two_node_diffusion_step,
    water_formation_reaction,
)
from oec.chemistry.errors import ChemistryEvaluationError, StoichiometryError
from oec.chemistry.stoichiometry import Reaction


def test_species_and_composition_mole_fraction() -> None:
    h2 = Species(id="H2", name="Hydrogen", formula={"H": 2})
    assert h2.formula["H"] == 2
    comp = Composition(amounts_mol={"H2": 2.0, "O2": 1.0})
    assert comp.total_mol == 3.0
    assert abs(comp.mole_fraction("H2") - 2.0 / 3.0) < 1e-15


def test_water_formation_atom_balance() -> None:
    rxn = water_formation_reaction()
    checks = rxn.atom_balance_check()
    assert all(c.balanced for c in checks.values())


def test_unbalanced_reaction_rejected() -> None:
    h2 = Species(id="H2", name="H2", formula={"H": 2})
    o2 = Species(id="O2", name="O2", formula={"O": 2})
    h2o = Species(id="H2O", name="H2O", formula={"H": 2, "O": 1})
    with pytest.raises(StoichiometryError):
        Reaction(
            id="bad",
            name="unbalanced",
            nu={"H2": -1.0, "O2": -1.0, "H2O": 1.0},
            species={"H2": h2, "O2": o2, "H2O": h2o},
        )


def test_extent_and_limiting_reactant() -> None:
    rxn = water_formation_reaction()
    comp = Composition(amounts_mol={"H2": 4.0, "O2": 1.0, "H2O": 0.0})
    assert abs(rxn.max_extent_mol(comp) - 1.0) < 1e-15  # O2 limits: 1/1
    out = rxn.apply_extent(comp, 1.0)
    assert abs(out.amounts_mol["H2"] - 2.0) < 1e-12
    assert abs(out.amounts_mol["O2"] - 0.0) < 1e-12
    assert abs(out.amounts_mol["H2O"] - 2.0) < 1e-12


def test_extent_cannot_go_negative() -> None:
    rxn = water_formation_reaction()
    comp = Composition(amounts_mol={"H2": 0.5, "O2": 1.0, "H2O": 0.0})
    with pytest.raises(StoichiometryError):
        rxn.apply_extent(comp, 1.0)


def test_fick_flux_direction() -> None:
    # c_A > c_B → positive flux A→B
    res = fick_flux_1d(
        concentration_a_mol_m3=10.0,
        concentration_b_mol_m3=0.0,
        distance_m=0.1,
        diffusivity_m2_s=1e-5,
    )
    assert res.flux_mol_per_m2_s > 0.0
    assert abs(res.flux_mol_per_m2_s - 1e-5 * 100.0) < 1e-15


def test_two_node_mass_conservation() -> None:
    na0, nb0 = 1.0, 0.0
    na1, nb1, delta = two_node_diffusion_step(
        amount_a_mol=na0,
        amount_b_mol=nb0,
        volume_a_m3=1.0,
        volume_b_m3=1.0,
        area_m2=0.01,
        distance_m=0.1,
        diffusivity_m2_s=1e-4,
        dt_s=1.0,
    )
    assert abs((na1 + nb1) - (na0 + nb0)) < 1e-12
    assert delta > 0.0
    assert na1 < na0


def test_arrhenius_increases_with_temperature() -> None:
    cold = arrhenius_rate_constant(
        pre_exponential=1e10,
        activation_energy_j_per_mol=50_000.0,
        temperature_k=300.0,
    )
    hot = arrhenius_rate_constant(
        pre_exponential=1e10,
        activation_energy_j_per_mol=50_000.0,
        temperature_k=400.0,
    )
    assert hot.k > cold.k


def test_power_law_and_batch_step() -> None:
    rxn = water_formation_reaction()
    comp = Composition(amounts_mol={"H2": 2.0, "O2": 1.0, "H2O": 0.0})
    k = 1e-3
    rate = power_law_rate(
        k=k,
        concentrations_mol_m3={"H2": 2.0, "O2": 1.0},
        orders={"H2": 1.0, "O2": 1.0},
    )
    assert abs(rate - 2e-3) < 1e-15
    step = batch_extent_euler_step(
        rxn,
        comp,
        k=k,
        orders={"H2": 1.0, "O2": 1.0},
        volume_m3=1.0,
        dt_s=0.1,
    )
    assert step.extent_step_mol > 0.0
    assert step.composition.amounts_mol["H2O"] > 0.0


def test_equilibrium_at_kc() -> None:
    # Simple isomerisation A ⇌ B, nu={A:-1, B:1}, Kc=1, equal moles → Q=1
    a = Species(id="A", name="A", formula={"C": 1})
    b = Species(id="B", name="B", formula={"C": 1})
    rxn = Reaction(
        id="iso",
        name="isomerisation",
        nu={"A": -1.0, "B": 1.0},
        species={"A": a, "B": b},
    )
    comp = Composition(amounts_mol={"A": 1.0, "B": 1.0})
    eq = evaluate_equilibrium(rxn, comp, kc=1.0, volume_m3=1.0)
    assert eq.at_equilibrium
    assert abs(eq.driving_force) < 1e-12


def test_extent_to_equilibrium_binary() -> None:
    a = Species(id="A", name="A", formula={"C": 1})
    b = Species(id="B", name="B", formula={"C": 1})
    rxn = Reaction(
        id="iso",
        name="isomerisation",
        nu={"A": -1.0, "B": 1.0},
        species={"A": a, "B": b},
    )
    # Start pure A, Kc=1 → equilibrium at equal A,B → ξ=0.5
    comp = Composition(amounts_mol={"A": 1.0, "B": 0.0})
    xi = extent_to_equilibrium_binary(rxn, comp, kc=1.0, volume_m3=1.0)
    assert abs(xi - 0.5) < 1e-6
    final = rxn.apply_extent(comp, xi)
    assert abs(final.amounts_mol["A"] - final.amounts_mol["B"]) < 1e-5


def test_nernst_standard_state() -> None:
    # Q=1 → E = E0
    res = nernst_potential(e0_v=1.23, n_electrons=2, reaction_quotient=1.0, temperature_k=298.15)
    assert abs(res.e_v - 1.23) < 1e-12


def test_nernst_q_effect() -> None:
    # Q > 1 lowers E for positive E0 cell
    low_q = nernst_potential(e0_v=1.0, n_electrons=1, reaction_quotient=0.1, temperature_k=298.15)
    high_q = nernst_potential(e0_v=1.0, n_electrons=1, reaction_quotient=10.0, temperature_k=298.15)
    assert low_q.e_v > high_q.e_v


def test_nernst_rejects_bad_q() -> None:
    with pytest.raises(ChemistryEvaluationError):
        nernst_potential(e0_v=1.0, n_electrons=1, reaction_quotient=0.0)


def test_fick_rejects_negative_concentration() -> None:
    with pytest.raises(ChemistryEvaluationError):
        fick_flux_1d(
            concentration_a_mol_m3=-1.0,
            concentration_b_mol_m3=0.0,
            distance_m=1.0,
            diffusivity_m2_s=1e-5,
        )


def test_arrhenius_known_value() -> None:
    # Ea=0 → k = A
    res = arrhenius_rate_constant(
        pre_exponential=42.0,
        activation_energy_j_per_mol=0.0,
        temperature_k=300.0,
    )
    assert abs(res.k - 42.0) < 1e-12
    assert math.isfinite(res.k)


def test_delta_g_zero_gives_k_one() -> None:
    k = equilibrium_constant_from_delta_g(delta_g_j_per_mol=0.0, temperature_k=298.15)
    assert abs(k - 1.0) < 1e-12
