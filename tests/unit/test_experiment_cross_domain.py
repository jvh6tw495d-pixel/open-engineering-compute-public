"""W7 cross-domain builders — structure tests (no heavy extras)."""

from __future__ import annotations

import oec.experiment.cross_domain as cd
from oec.experiment.cross_domain import (
    build_foundation_embed_then_stats_experiment,
    build_monte_carlo_then_describe_experiment,
    build_peft_train_then_generate_experiment,
    build_physics_kinematics_experiment,
    build_root_bind_to_distribution_experiment,
    build_wave_then_stats_experiment,
    get_cross_domain_builder,
    list_cross_domain_builders,
)
from oec.experiment.specs import ExperimentSpec


def test_list_builders_nonempty() -> None:
    rows = list_cross_domain_builders()
    assert len(rows) >= 5
    names = {r["name"] for r in rows}
    assert "build_physics_kinematics_experiment" in names


def test_builder_catalog_matches_module_defined_builders() -> None:
    """Catalog must equal build_*_experiment defined in this module (not imports)."""
    catalog_names = {r["name"] for r in list_cross_domain_builders()}
    defined_here = {
        name
        for name, obj in vars(cd).items()
        if (
            name.startswith("build_")
            and name.endswith("_experiment")
            and callable(obj)
            and getattr(obj, "__module__", None) == cd.__name__
        )
    }
    assert catalog_names == defined_here
    # Imported helpers must stay out of the public W7 MCP/CLI catalog.
    assert "build_optimize_single_experiment" not in catalog_names
    assert "build_mlp_regressor_experiment" not in catalog_names


def test_get_cross_domain_builder_fail_closed() -> None:
    assert get_cross_domain_builder("not_a_real_builder") is None
    assert get_cross_domain_builder("ExperimentSpec") is None
    assert get_cross_domain_builder("sphere_problem_2d") is None
    fn = get_cross_domain_builder("build_physics_kinematics_experiment")
    assert callable(fn)
    built = fn()
    assert isinstance(built, ExperimentSpec)


def test_builder_shapes() -> None:
    kin = build_physics_kinematics_experiment()
    assert kin.steps[0].skill_id == "mechanics.kinematics_1d"
    wave = build_wave_then_stats_experiment()
    assert len(wave.steps) == 2
    mc = build_monte_carlo_then_describe_experiment(n_samples=50)
    assert mc.steps[0].skill_id == "statistics.monte_carlo"
    root = build_root_bind_to_distribution_experiment()
    assert root.steps[1].binds_from
    emb = build_foundation_embed_then_stats_experiment(dim=16)
    assert emb.steps[0].skill_id == "foundation.embed"
    peft = build_peft_train_then_generate_experiment()
    assert peft.steps[0].skill_id == "foundation.peft_train"
    assert peft.steps[1].skill_id == "foundation.generate"
    assert peft.steps[1].binds_from
    assert peft.steps[1].binds_from[0].path == "result.artifact.path"
    assert peft.steps[1].binds_from[0].as_key == "adapter_path"
    assert peft.required_extras == ("foundation",)
