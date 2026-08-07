"""ADR 0005 conformance test: the same request submitted through the
SDK, CLI, REST API, and MCP server yields the same scientific content.

ADR 0005 names this the acceptance bar for every interface built on
top of ``oec.sdk.Engine``: "the same ``ExecutionRequest`` submitted
through any interface must yield the same scientific content in
``ExecutionResult`` (allowing only transport-level formatting
differences)." Sprint 07 adds the last two interfaces (REST, MCP) this
ADR was written for -- this test is the first place all four are
actually compared against each other in one place, rather than each
interface's own test suite separately asserting its own output looks
right.

Scientific content compared: ``status``, the numeric ``result`` fields,
``method.id``, and ``diagnostics.converged``. Deliberately excluded as
transport-only/per-call formatting: ``run_id``, ``started_at``/
``completed_at``/``duration_ms`` (every call is a fresh execution),
``provenance.trace_id`` (a fresh UUID per call unless the caller
supplies one), and any pure text/table formatting a given interface
applies on top of the JSON.
"""

from __future__ import annotations

import json
import math

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from oec import sdk
from oec.api.app import create_app
from oec.cli.main import app as cli_app
from oec.mcp.server import call_tool

_SKILL_ID = "mathematics.solve_root"
_INPUTS = {"expression": "x**2 - 2", "bracket": [0, 2]}
_EXPECTED_ROOT = math.sqrt(2)


def test_sdk_cli_rest_mcp_agree_on_scientific_content() -> None:
    # 1. SDK
    engine = sdk.Engine(skills_root="skills")
    sdk_result = engine.run(_SKILL_ID, _INPUTS)

    # 2. CLI
    cli_result = CliRunner().invoke(
        cli_app,
        ["run", _SKILL_ID, "--skills-root", "skills", "--input", json.dumps(_INPUTS), "--json"],
    )
    assert cli_result.exit_code == 0
    cli_body = json.loads(cli_result.stdout)

    # 3. REST
    with TestClient(create_app(skills_root="skills")) as client:
        rest_response = client.post(f"/v1/skills/{_SKILL_ID}/run", json={"inputs": _INPUTS})
    assert rest_response.status_code == 200
    rest_body = rest_response.json()

    # 4. MCP
    mcp_result = call_tool(engine, _SKILL_ID, _INPUTS)
    assert mcp_result.isError is False
    mcp_body = json.loads(mcp_result.content[0].text)

    # All four agree on status.
    statuses = {
        "sdk": sdk_result.status.value,
        "cli": cli_body["status"],
        "rest": rest_body["status"],
        "mcp": mcp_body["status"],
    }
    assert len(set(statuses.values())) == 1, statuses
    assert statuses["sdk"] == "VALIDATED"

    # All four agree on the numeric result, and it's the independently
    # known root (not just "the four agree with each other by coincidence").
    roots = {
        "sdk": sdk_result.result["root"],
        "cli": cli_body["result"]["root"],
        "rest": rest_body["result"]["root"],
        "mcp": mcp_body["result"]["root"],
    }
    for surface, root in roots.items():
        assert math.isclose(root, _EXPECTED_ROOT, rel_tol=1e-9), (surface, root)

    # All four agree on method identity and convergence diagnostics.
    method_ids = {
        "sdk": sdk_result.method.id,
        "cli": cli_body["method"]["id"],
        "rest": rest_body["method"]["id"],
        "mcp": mcp_body["method"]["id"],
    }
    assert len(set(method_ids.values())) == 1, method_ids

    converged_flags = {
        "sdk": sdk_result.diagnostics["converged"],
        "cli": cli_body["diagnostics"]["converged"],
        "rest": rest_body["diagnostics"]["converged"],
        "mcp": mcp_body["diagnostics"]["converged"],
    }
    assert len(set(converged_flags.values())) == 1, converged_flags
    assert converged_flags["sdk"] is True


def test_sdk_cli_rest_mcp_agree_on_invalid_status() -> None:
    """The conformance bar holds for a non-VERIFIED/VALIDATED status too
    -- INVALID (a schema violation) must look the same on all four."""
    bad_inputs = {**_INPUTS, "unexpected_field": True}

    engine = sdk.Engine(skills_root="skills")
    sdk_result = engine.run(_SKILL_ID, bad_inputs)

    cli_result = CliRunner().invoke(
        cli_app,
        [
            "run",
            _SKILL_ID,
            "--skills-root",
            "skills",
            "--input",
            json.dumps(bad_inputs),
            "--json",
        ],
    )
    cli_body = json.loads(cli_result.stdout)

    with TestClient(create_app(skills_root="skills")) as client:
        rest_response = client.post(f"/v1/skills/{_SKILL_ID}/run", json={"inputs": bad_inputs})
    rest_body = rest_response.json()

    mcp_result = call_tool(engine, _SKILL_ID, bad_inputs)
    mcp_body = json.loads(mcp_result.content[0].text)

    statuses = {
        "sdk": sdk_result.status.value,
        "cli": cli_body["status"],
        "rest": rest_body["status"],
        "mcp": mcp_body["status"],
    }
    assert len(set(statuses.values())) == 1, statuses
    assert statuses["sdk"] == "INVALID"

    # Transport-level distinctions are allowed to differ: the CLI exits
    # non-zero (ADR 0014) and REST still returns HTTP 200 (ADR 0015) --
    # both correctly encode "INVALID" in their own transport idiom.
    assert cli_result.exit_code == 3
    assert rest_response.status_code == 200
    assert mcp_result.isError is False  # INVALID is a result, not an MCP-level error


# Phase A3: same ADR 0005 bar for a closed-form electrical skill (units path).
_ELEC_SKILL = "electrical.three_phase_power"
_ELEC_INPUTS = {
    "voltage_line_to_line": {"value": 380.0, "unit": "V"},
    "current_line": {"value": 10.0, "unit": "A"},
    "power_factor": 0.8,
    "power_factor_type": "lagging",
}


def test_sdk_cli_rest_mcp_agree_on_electrical_three_phase_power() -> None:
    engine = sdk.Engine(skills_root="skills")
    sdk_result = engine.run(_ELEC_SKILL, _ELEC_INPUTS)

    cli_result = CliRunner().invoke(
        cli_app,
        [
            "run",
            _ELEC_SKILL,
            "--skills-root",
            "skills",
            "--input",
            json.dumps(_ELEC_INPUTS),
            "--json",
        ],
    )
    assert cli_result.exit_code == 0
    cli_body = json.loads(cli_result.stdout)

    with TestClient(create_app(skills_root="skills")) as client:
        rest_response = client.post(f"/v1/skills/{_ELEC_SKILL}/run", json={"inputs": _ELEC_INPUTS})
    assert rest_response.status_code == 200
    rest_body = rest_response.json()

    mcp_result = call_tool(engine, _ELEC_SKILL, _ELEC_INPUTS)
    assert mcp_result.isError is False
    mcp_body = json.loads(mcp_result.content[0].text)

    statuses = {
        "sdk": sdk_result.status.value,
        "cli": cli_body["status"],
        "rest": rest_body["status"],
        "mcp": mcp_body["status"],
    }
    assert len(set(statuses.values())) == 1, statuses
    assert statuses["sdk"] == "VERIFIED"

    for surface, body in (
        ("sdk", sdk_result.result),
        ("cli", cli_body["result"]),
        ("rest", rest_body["result"]),
        ("mcp", mcp_body["result"]),
    ):
        assert math.isclose(
            body["apparent_power"]["value"],
            math.sqrt(3) * 380.0 * 10.0,
            rel_tol=1e-9,
        ), surface

    method_ids = {
        "sdk": sdk_result.method.id,
        "cli": cli_body["method"]["id"],
        "rest": rest_body["method"]["id"],
        "mcp": mcp_body["method"]["id"],
    }
    assert len(set(method_ids.values())) == 1, method_ids
    assert method_ids["sdk"] == "balanced_three_phase_power"
