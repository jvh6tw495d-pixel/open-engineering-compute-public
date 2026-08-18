"""S4 — evolutionary / hybrid builders on the fail-closed cross-domain catalog.

Public declarative experiment builders from W5 must be discoverable only through
``list_cross_domain_builders`` / ``get_cross_domain_builder``. Helpers and
non-catalog callables stay rejected. NEAT is catalogued (ADR 0044).
"""

from __future__ import annotations

from oec.evolutionary.contracts import (
    AlgorithmName,
    BudgetSpec,
    EvolutionaryAlgorithmSpec,
)
from oec.experiment.cross_domain import get_cross_domain_builder, list_cross_domain_builders
from oec.experiment.evolutionary import sphere_problem_2d
from oec.experiment.specs import ExperimentSpec

# S4 public evolutionary / hybrid experiment builders (not helpers).
_S4_PUBLIC_EVO_BUILDERS: dict[str, dict[str, list[str]]] = {
    "build_optimize_single_experiment": {
        "domains": ["evolutionary"],
        "extras": ["evolutionary"],
    },
    "build_nsga2_experiment": {
        "domains": ["evolutionary"],
        "extras": ["evolutionary"],
    },
    "build_neat_experiment": {
        "domains": ["evolutionary"],
        "extras": ["evolutionary"],
    },
    "build_hyperneat_experiment": {
        "domains": ["evolutionary"],
        "extras": ["evolutionary"],
    },
    "build_hybrid_training_experiment": {
        "domains": ["neural", "evolutionary"],
        "extras": ["neural", "evolutionary"],
    },
}

# Module callables that must never appear on the MCP/CLI catalog.
_HELPERS_AND_NON_CATALOG = (
    "sphere_problem_2d",
    "problem_to_optimize_inputs",
    "PopulationSpec",
    "build_mlp_regressor_experiment",
    "build_evo_then_describe_experiment",
    "build_neural_training_mode_experiment",
)


def test_s4_public_evo_builders_are_catalogued_with_metadata() -> None:
    rows = {r["name"]: r for r in list_cross_domain_builders()}
    for name, expected in _S4_PUBLIC_EVO_BUILDERS.items():
        assert name in rows, f"{name} missing from catalog"
        assert rows[name]["domains"] == expected["domains"]
        assert rows[name]["extras"] == expected["extras"]


def test_s4_helpers_and_non_public_names_stay_out_of_catalog() -> None:
    names = {r["name"] for r in list_cross_domain_builders()}
    for helper in _HELPERS_AND_NON_CATALOG:
        assert helper not in names
        assert get_cross_domain_builder(helper) is None


def test_s4_get_builder_resolves_optimize_single() -> None:
    fn = get_cross_domain_builder("build_optimize_single_experiment")
    assert callable(fn)
    algo = EvolutionaryAlgorithmSpec(
        algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
        budget=BudgetSpec(generations=4, population=6),
        seed=0,
    )
    spec = fn(problem=sphere_problem_2d(), algorithm=algo, seed=0)
    assert isinstance(spec, ExperimentSpec)
    assert spec.required_extras == ("evolutionary",)
    assert spec.steps[0].skill_id == "evolutionary.optimize_single"


def test_s4_get_builder_resolves_nsga2() -> None:
    fn = get_cross_domain_builder("build_nsga2_experiment")
    assert callable(fn)
    spec = fn(n_var=3, generations=5, population=8, seed=1)
    assert isinstance(spec, ExperimentSpec)
    assert spec.required_extras == ("evolutionary",)
    assert spec.steps[0].skill_id == "evolutionary.nsga2"


def test_s4_get_builder_resolves_neat() -> None:
    fn = get_cross_domain_builder("build_neat_experiment")
    assert callable(fn)
    spec = fn(fitness="xor", generations=5, population=8, seed=1)
    assert isinstance(spec, ExperimentSpec)
    assert spec.required_extras == ("evolutionary",)
    assert spec.steps[0].skill_id == "evolutionary.neat"


def test_s4_get_builder_resolves_hyperneat() -> None:
    fn = get_cross_domain_builder("build_hyperneat_experiment")
    assert callable(fn)
    spec = fn(fitness="xor", generations=5, population=8, seed=1)
    assert isinstance(spec, ExperimentSpec)
    assert spec.required_extras == ("evolutionary",)
    assert spec.steps[0].skill_id == "evolutionary.hyperneat"


def test_s4_get_builder_resolves_hybrid_training() -> None:
    fn = get_cross_domain_builder("build_hybrid_training_experiment")
    assert callable(fn)
    spec = fn(
        x=[[0.0], [1.0], [2.0], [3.0]],
        y=[0.0, 1.0, 2.0, 3.0],
        seed=2,
        max_evaluations=4,
    )
    assert isinstance(spec, ExperimentSpec)
    assert set(spec.required_extras) == {"neural", "evolutionary"}
    assert spec.steps[0].skill_id == "neural.training.hybrid"
