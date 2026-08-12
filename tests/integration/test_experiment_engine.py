"""W2 integration: multi-step experiment via Engine + CLI + REST + MCP."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from oec.cli.main import app
from oec.experiment import ExperimentStatus
from oec.sdk import Engine


def test_e2e_root_and_distribution() -> None:
    """Core-only experiment: solve root then evaluate normal PDF (no AI extras)."""
    engine = Engine(skills_root="skills")
    record = engine.run_experiment(
        {
            "id": "w2_e2e_root_dist",
            "seed": 0,
            "title": "root + norm pdf",
            "steps": [
                {
                    "step_id": "root",
                    "skill_id": "mathematics.solve_root",
                    "inputs": {"expression": "x**2 - 2", "bracket": [0, 2]},
                },
                {
                    "step_id": "pdf",
                    "skill_id": "statistics.distribution_eval",
                    "inputs": {
                        "distribution": "norm",
                        "operation": "pdf",
                        "params": {"loc": 0.0, "scale": 1.0},
                        "x": 0.0,
                    },
                },
            ],
            "metrics": [
                {
                    "name": "pdf0",
                    "path": "result.value",
                    "step_id": "pdf",
                    "direction": "maximize",
                }
            ],
        }
    )
    assert record.status == ExperimentStatus.COMPLETED
    assert len(record.steps) == 2
    assert record.metrics[0].value is not None
    assert record.metrics[0].value > 0.3
    assert "config_hash" in record.reproducibility
    # JSON round-trip of full record
    payload = record.to_dict()
    assert payload["status"] == "COMPLETED"
    assert payload["steps"][0]["execution"]["status"] in {
        "VERIFIED",
        "VALIDATED",
        "CONVERGED_WITH_WARNINGS",
        "APPROXIMATE",
    }


def test_mcp_experiment_run(engine: Engine | None = None) -> None:
    from oec.mcp.server import call_tool
    from oec.sdk import Engine as Eng

    eng = engine or Eng(skills_root="skills")
    result = call_tool(
        eng,
        "experiment.run",
        {
            "spec": {
                "id": "mcp_exp",
                "seed": 0,
                "steps": [
                    {
                        "step_id": "d",
                        "skill_id": "statistics.describe",
                        "inputs": {"values": [2.0, 4.0, 6.0]},
                    }
                ],
                "metrics": [
                    {
                        "name": "mean",
                        "path": "result.mean",
                        "step_id": "d",
                        "direction": "minimize",
                    }
                ],
            }
        },
    )
    assert result.isError is False
    body = json.loads(result.content[0].text)
    assert body["status"] == "COMPLETED"
    assert body["metrics"][0]["value"] == 4.0


def test_rest_experiment_run() -> None:
    import pytest

    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from oec.api.app import create_app

    with TestClient(create_app(skills_root="skills")) as client:
        resp = client.post(
            "/v1/experiments/run",
            json={
                "id": "rest_exp",
                "seed": 0,
                "steps": [
                    {
                        "step_id": "d",
                        "skill_id": "statistics.describe",
                        "inputs": {"values": [1.0, 3.0]},
                    }
                ],
                "metrics": [
                    {
                        "name": "mean",
                        "path": "result.mean",
                        "step_id": "d",
                        "direction": "minimize",
                    }
                ],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["metrics"][0]["value"] == 2.0


def test_cli_experiment_run(tmp_path: Path) -> None:
    spec_path = tmp_path / "exp.json"
    spec_path.write_text(
        json.dumps(
            {
                "id": "cli_demo",
                "seed": 3,
                "steps": [
                    {
                        "step_id": "d",
                        "skill_id": "statistics.describe",
                        "inputs": {"values": [4.0, 5.0, 6.0]},
                    }
                ],
                "metrics": [
                    {
                        "name": "mean",
                        "path": "result.mean",
                        "step_id": "d",
                        "direction": "minimize",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["experiment", "run", "--spec-file", str(spec_path), "--skills-root", "skills"],
    )
    assert result.exit_code == 0, result.output
    body = json.loads(result.output)
    assert body["status"] == "COMPLETED"
    assert body["metrics"][0]["value"] == 5.0
