"""W7 cross-domain builders — structure tests (no heavy extras)."""

from __future__ import annotations

from oec.experiment.cross_domain import (
    build_foundation_embed_then_stats_experiment,
    build_monte_carlo_then_describe_experiment,
    build_physics_kinematics_experiment,
    build_root_bind_to_distribution_experiment,
    build_wave_then_stats_experiment,
    list_cross_domain_builders,
)


def test_list_builders_nonempty() -> None:
    rows = list_cross_domain_builders()
    assert len(rows) >= 5
    names = {r["name"] for r in rows}
    assert "build_physics_kinematics_experiment" in names


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
