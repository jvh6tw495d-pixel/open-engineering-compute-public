"""W6–W8 integration: foundation embed, cross-domain experiments, backends CLI."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from oec import __version__
from oec.cli.main import app
from oec.experiment import ExperimentStatus
from oec.experiment.cross_domain import (
    build_foundation_embed_then_stats_experiment,
    build_physics_kinematics_experiment,
    build_root_bind_to_distribution_experiment,
    build_wave_then_stats_experiment,
)
from oec.sdk import Engine


def test_version_is_3_5() -> None:
    assert __version__.startswith("3.5")


def test_w6_foundation_embed_skill() -> None:
    engine = Engine(skills_root="skills")
    result = engine.run(
        "foundation.embed",
        {"texts": ["a", "b"], "backend": "builtin_hash", "dim": 16, "seed": 0},
    )
    assert result.status.value in {"VERIFIED", "VALIDATED"}
    assert result.result["n"] == 2


def test_w6_capabilities_skill() -> None:
    engine = Engine(skills_root="skills")
    result = engine.run("foundation.capabilities", {})
    assert "transformers_available" in result.result


def test_w7_core_experiments_complete() -> None:
    engine = Engine(skills_root="skills")
    for builder in (
        build_physics_kinematics_experiment,
        build_wave_then_stats_experiment,
        build_root_bind_to_distribution_experiment,
        build_foundation_embed_then_stats_experiment,
    ):
        record = engine.run_experiment(builder())
        assert record.status == ExperimentStatus.COMPLETED, (
            builder.__name__,
            record.status,
            record.validation.messages,
        )


def test_w8_backends_cli() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["backends", "--json"])
    assert result.exit_code == 0, result.output
    body = json.loads(result.output)
    names = {row["name"] for row in body}
    assert "numpy" in names and "scipy" in names and "sympy" in names
    assert "transformers" in names


def test_w8_experiment_builders_cli() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["experiment", "builders", "--json"])
    assert result.exit_code == 0, result.output
    body = json.loads(result.output)
    assert any(r["name"] == "build_wave_then_stats_experiment" for r in body)
