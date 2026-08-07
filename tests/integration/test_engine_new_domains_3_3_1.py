"""Engine.run proofs for chemistry / multiphysics / THD (3.3.1 recovery Phase 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from oec.execution.models import ExecutionStatus
from oec.sdk import Engine

_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def engine() -> Engine:
    eng = Engine(skills_root=_ROOT / "skills")
    assert eng.registration_failures == []
    assert len(eng.registry.list_skills()) == 87
    return eng


@pytest.mark.parametrize(
    ("skill_id", "inputs"),
    [
        (
            "chemistry.nernst",
            {
                "e0_v": 1.23,
                "n_electrons": 2,
                "reaction_quotient": 1.0,
                "temperature_k": 298.15,
            },
        ),
        (
            "chemistry.fick_flux",
            {
                "concentration_a_mol_m3": 10.0,
                "concentration_b_mol_m3": 0.0,
                "distance_m": 0.1,
                "diffusivity_m2_s": 1e-5,
            },
        ),
        (
            "chemistry.reaction_extent",
            {"h2_mol": 4.0, "o2_mol": 1.0, "h2o_mol": 0.0, "extent_mol": 1.0},
        ),
        (
            "chemistry.equilibrium",
            {"a_mol": 1.0, "b_mol": 1.0, "kc": 1.0, "volume_m3": 1.0},
        ),
        (
            "chemistry.arrhenius",
            {
                "pre_exponential": 42.0,
                "activation_energy_j_per_mol": 0.0,
                "temperature_k": 300.0,
            },
        ),
        (
            "chemistry.batch_kinetics",
            {"a_mol": 1.0, "b_mol": 0.0, "k": 0.1, "volume_m3": 1.0, "dt_s": 1.0},
        ),
        (
            "electrical.harmonics_thd",
            {
                "fundamental": {"value": 100.0, "unit": "V"},
                "harmonics": [
                    {"value": 3.0, "unit": "V"},
                    {"value": 4.0, "unit": "V"},
                ],
            },
        ),
        (
            "multiphysics.wire_i2r",
            {
                "current_a": 10.0,
                "r0_ohm": 0.1,
                "t_amb_k": 293.15,
                "ua_w_per_k": 1.0,
                "alpha_per_k": 0.0,
                "t0_k": 293.15,
            },
        ),
        (
            "multiphysics.solar_thermal_electrical",
            {
                "irradiance_w_m2": 1000.0,
                "area_m2": 1.0,
                "eta0": 0.2,
                "t_amb_c": 25.0,
                "ua_w_per_k": 50.0,
            },
        ),
    ],
)
def test_engine_run_new_domain_skills(engine: Engine, skill_id: str, inputs: dict) -> None:
    result = engine.run(skill_id, inputs)
    assert result.status in {
        ExecutionStatus.VERIFIED,
        ExecutionStatus.VALIDATED,
        ExecutionStatus.CONVERGED_WITH_WARNINGS,
        ExecutionStatus.APPROXIMATE,
    }, (skill_id, result.status, result.diagnostics)
    assert result.result, skill_id


def test_catalog_count_matches_filesystem(engine: Engine) -> None:
    yaml_count = len(list((_ROOT / "skills").rglob("skill.yaml")))
    assert yaml_count == 87
    assert len(engine.registry.list_skills()) == yaml_count
