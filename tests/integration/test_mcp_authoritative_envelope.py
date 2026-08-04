"""Integration tests for authoritative-output envelope (v2.5.3 Wave 1 T7).

New file — does not edit existing MCP integration tests.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from oec.mcp.server import _AGENT_TOOL_SCHEMAS, call_tool
from oec.sdk import Engine


@pytest.fixture(scope="module")
def engine() -> Engine:
    eng = Engine(skills_root="skills")
    eng.warm()
    return eng


def _parse_content(result: Any) -> Any:
    assert result.content, "tool result has no content blocks"
    assert result.content[0].type == "text"
    return json.loads(result.content[0].text)


# ---------------------------------------------------------------------------
# T7(a): routed vs direct optimization → identical authoritative_answer
# ---------------------------------------------------------------------------


def test_routed_and_direct_optimization_share_identical_authoritative_answer(
    engine: Engine,
) -> None:
    direct = call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    routed = call_tool(
        engine,
        "agent.default",
        {"request": "solve optimization problem", "demo_label": "diet"},
    )
    assert direct.isError is False
    assert routed.isError is False
    direct_payload = _parse_content(direct)
    routed_payload = _parse_content(routed)

    assert "authoritative_answer" in direct_payload
    assert "authoritative_answer" in routed_payload
    direct_aa = direct_payload["authoritative_answer"]
    routed_aa = routed_payload["authoritative_answer"]
    # Host-facing numerical truth must match across routed vs direct paths.
    # run_id differs per Engine invocation; input_hash + values are the stable identity.
    assert direct_aa["kind"] == routed_aa["kind"] == "optimization_result"
    assert direct_aa["values"] == routed_aa["values"]
    assert direct_aa["provenance"]["input_hash"] == routed_aa["provenance"]["input_hash"]
    assert isinstance(direct_aa["values"], dict)
    assert "objective_value" in direct_aa["values"]
    # Nested result path still present for legacy consumers.
    assert routed_payload["result"]["execution"]["status"] == "VALIDATED"
    assert routed_payload["status"] == "ok"
    assert direct_payload["status"] == "ok"


# ---------------------------------------------------------------------------
# T7(b): free-text math path → scalar_extrema_result
# ---------------------------------------------------------------------------


def test_free_text_math_path_emits_scalar_extrema_result(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": (
                "Determine o máximo e o mínimo de v(t)=t^3 - 10.5*t^2 + 30*t + 20 "
                "entre 13 e 18 horas, onde t é o número de horas após o meio-dia."
            )
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == "agent.applied_mathematics"
    assert payload["result"]["interpreted_as"] == "scalar_extrema_on_closed_interval"
    aa = payload["authoritative_answer"]
    assert aa["kind"] == "scalar_extrema_result"
    assert set(aa["values"]) == {"min", "max"}
    assert "x" in aa["values"]["min"]
    assert "fun" in aa["values"]["min"]


def test_direct_applied_math_free_text_also_emits_scalar_extrema(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.applied_mathematics",
        {
            "request": (
                "Determine o máximo e o mínimo de v(t)=t^3 - 10.5*t^2 + 30*t + 20 "
                "entre 13 e 18 horas."
            )
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["authoritative_answer"]["kind"] == "scalar_extrema_result"


# ---------------------------------------------------------------------------
# T7(c): needs_clarification / needs_more_information carry no authority
# ---------------------------------------------------------------------------


def test_needs_clarification_has_no_authoritative_answer(engine: Engine) -> None:
    result = call_tool(engine, "agent.default", {"request": "do something vague"})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "needs_clarification"
    assert "authoritative_answer" not in payload


def test_needs_more_information_has_no_authoritative_answer(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.optimization_specialist",
        {"request": "minimize cost of a linear blending problem"},
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "needs_more_information"
    assert "authoritative_answer" not in payload


def test_router_nested_needs_more_information_has_no_authoritative_answer(
    engine: Engine,
) -> None:
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": "minimize cost of a linear blending problem",
            "preferred_domain": "optimization",
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["result"]["status"] == "needs_more_information"
    assert "authoritative_answer" not in payload


# ---------------------------------------------------------------------------
# T7(d): smoke-check all 7 specialists (+ raw skill untouched)
# ---------------------------------------------------------------------------


def test_smoke_all_seven_agents_normalize_without_crash(engine: Engine) -> None:
    """Each specialist path returns a parseable payload; authority only when solved."""
    agent_names = [name for name in _AGENT_TOOL_SCHEMAS if name != "agent.default"]
    assert len(agent_names) == 7

    calls: list[tuple[str, dict[str, Any]]] = [
        ("agent.optimization_specialist", {"demo_label": "diet"}),
        (
            "agent.applied_mathematics",
            {
                "skill_id": "mathematics.solve_root",
                "inputs": {"expression": "x**2 - 2", "bracket": [0, 2]},
            },
        ),
        ("agent.time_series", {"demo_label": "resample"}),
        ("agent.energy", {"demo_label": "balance"}),
        ("agent.control_dynamics", {"demo_label": "pid"}),
        ("agent.finance_uncertainty", {"demo_label": "returns"}),
    ]

    for name, arguments in calls:
        result = call_tool(engine, name, arguments)
        assert result.isError is False, name
        payload = _parse_content(result)
        assert payload.get("status") == "ok", name
        assert payload.get("authoritative_answer_schema_version") == "1.1", name
        assert "authoritative_answer" in payload, name
        assert "problem_classification" in payload, name
        assert "method_summary" in payload, name

    # Reviewer: solve then review.
    solve = _parse_content(
        call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    )
    review = call_tool(
        engine,
        "agent.scientific_reviewer",
        {"ops_document": solve["ops"], "execution": solve["execution"]},
    )
    assert review.isError is False
    review_payload = _parse_content(review)
    assert review_payload["status"] == "ok"
    assert review_payload["authoritative_answer"]["kind"] == "review_result"
    assert review_payload["passed"] is True  # original nesting preserved


def test_raw_skill_dispatch_untouched_by_envelope(engine: Engine) -> None:
    """Shape 8 keeps ExecutionStatus semantics — no status:ok envelope."""
    result = call_tool(
        engine,
        "mathematics.solve_root",
        {"expression": "x**2 - 2", "bracket": [0, 2]},
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "VALIDATED"
    assert "authoritative_answer" not in payload
    assert "authoritative_answer_schema_version" not in payload
    assert "result" in payload  # ExecutionResult.result


def test_optimization_schema_declares_skill_id_and_inputs(engine: Engine) -> None:
    """Surface-schema fix: agent.optimization_specialist must advertise skill_id+inputs."""
    from oec.mcp.server import build_tools

    tools = build_tools(engine)
    by_name = {tool.name: tool for tool in tools}
    props = by_name["agent.optimization_specialist"].inputSchema["properties"]
    assert "skill_id" in props
    assert "inputs" in props
    assert "ops" in props
    assert "demo_label" in props


# ---------------------------------------------------------------------------
# Wave 4 / schema 1.1: physics_result + energy_result regression + jsonschema
# ---------------------------------------------------------------------------


def _aa_schema() -> dict[str, Any]:
    from pathlib import Path

    schema_path = (
        Path(__file__).resolve().parents[2] / "schemas" / "authoritative_answer.schema.json"
    )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_schema_document_is_version_1_1_with_physics_result() -> None:
    schema = _aa_schema()
    assert schema["version"] == "1.1"
    kind_enum = schema["$defs"]["authoritativeAnswer"]["properties"]["kind"]["enum"]
    assert "physics_result" in kind_enum
    # v1.0 kinds remain.
    assert "energy_result" in kind_enum
    assert "optimization_result" in kind_enum
    version_enum = schema["properties"]["authoritative_answer_schema_version"]["enum"]
    assert set(version_enum) == {"1.0", "1.1"}


def test_thermal_skill_emits_physics_result_schema_1_1(engine: Engine) -> None:
    """New multi-domain physics skill → kind physics_result under schema 1.1."""
    import jsonschema

    inputs = {
        "conductivity": {"value": 1.5, "unit": "W / (m * K)"},
        "area": {"value": 0.5, "unit": "m ** 2"},
        "length": {"value": 0.02, "unit": "m"},
        "hot_temperature": {"value": 80.0, "unit": "degC"},
        "cold_temperature": {"value": 20.0, "unit": "degC"},
    }
    # Unknown skill prefixes fall through to applied_mathematics; Engine still runs.
    result = call_tool(
        engine,
        "agent.applied_mathematics",
        {"skill_id": "thermal.conduction_1d", "inputs": inputs},
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "ok"
    assert payload["authoritative_answer_schema_version"] == "1.1"
    aa = payload["authoritative_answer"]
    assert aa["kind"] == "physics_result"
    # values == execution.result verbatim (no double-wrap).
    execution = payload["execution"]
    assert aa["values"] == execution["result"]
    assert aa["values"]["heat_rate"]["value"] == pytest.approx(2250.0)

    # Real envelope validates against the published JSON Schema.
    validator = jsonschema.Draft202012Validator(_aa_schema())
    slice_for_schema = {
        "authoritative_answer_schema_version": payload["authoritative_answer_schema_version"],
        "authoritative_answer": aa,
    }
    validator.validate(slice_for_schema)


def test_electrical_dc_power_flow_stays_energy_result(engine: Engine) -> None:
    """Regression: electrical.* (including P1 dc_power_flow) stays energy_result."""
    import jsonschema

    inputs = {
        "lines": [
            {"from_bus": "A", "to_bus": "B", "susceptance": 10.0},
            {"from_bus": "B", "to_bus": "C", "susceptance": 10.0},
            {"from_bus": "A", "to_bus": "C", "susceptance": 10.0},
        ],
        "injections": {"A": -1.0, "B": 0.4, "C": 0.6},
        "slack_bus": "A",
    }
    direct = call_tool(
        engine,
        "agent.energy",
        {"skill_id": "electrical.dc_power_flow", "inputs": inputs},
    )
    routed = call_tool(
        engine,
        "agent.default",
        {"skill_id": "electrical.dc_power_flow", "inputs": inputs},
    )
    assert direct.isError is False
    assert routed.isError is False
    direct_payload = _parse_content(direct)
    routed_payload = _parse_content(routed)

    assert direct_payload["authoritative_answer"]["kind"] == "energy_result"
    assert routed_payload["authoritative_answer"]["kind"] == "energy_result"
    # routed == direct AA values (host-facing truth identity).
    assert (
        direct_payload["authoritative_answer"]["values"]
        == routed_payload["authoritative_answer"]["values"]
    )
    assert direct_payload["authoritative_answer_schema_version"] == "1.1"
    assert direct_payload["authoritative_answer"]["values"] == direct_payload["execution"]["result"]

    validator = jsonschema.Draft202012Validator(_aa_schema())
    validator.validate(
        {
            "authoritative_answer_schema_version": direct_payload[
                "authoritative_answer_schema_version"
            ],
            "authoritative_answer": direct_payload["authoritative_answer"],
        }
    )


def test_legacy_schema_version_1_0_still_validates() -> None:
    """Additive policy: a pure v1.0 envelope remains schema-valid."""
    import jsonschema

    legacy = {
        "authoritative_answer_schema_version": "1.0",
        "authoritative_answer": {
            "kind": "energy_result",
            "values": {"x": 1},
            "provenance": {"run_id": "legacy"},
        },
    }
    jsonschema.Draft202012Validator(_aa_schema()).validate(legacy)


# ---------------------------------------------------------------------------
# v2.6.1 Wave 2: energy-rich skills → energy_result; routed ≡ direct AA
# ---------------------------------------------------------------------------


def test_energy_hybrid_balance_routed_equals_direct_energy_result(engine: Engine) -> None:
    """New energy.* skill: kind energy_result; routed≡direct values; no double-wrap."""
    import jsonschema

    inputs = {
        "load": [{"value": 3.0, "unit": "W"}, {"value": 2.0, "unit": "W"}],
        "pv": [{"value": 0.0, "unit": "W"}, {"value": 3.0, "unit": "W"}],
        "grid_import": [{"value": 3.0, "unit": "W"}, {"value": -0.5, "unit": "W"}],
        "storage_charge": [{"value": 0.0, "unit": "W"}, {"value": 0.5, "unit": "W"}],
        "storage_discharge": [{"value": 0.0, "unit": "W"}, {"value": 0.0, "unit": "W"}],
        "dt_hours": {"value": 1.0, "unit": "h"},
    }
    direct = call_tool(
        engine,
        "agent.energy",
        {"skill_id": "energy.hybrid_balance", "inputs": inputs},
    )
    routed = call_tool(
        engine,
        "agent.default",
        {"skill_id": "energy.hybrid_balance", "inputs": inputs},
    )
    assert direct.isError is False
    assert routed.isError is False
    direct_payload = _parse_content(direct)
    routed_payload = _parse_content(routed)

    assert direct_payload["authoritative_answer"]["kind"] == "energy_result"
    assert routed_payload["authoritative_answer"]["kind"] == "energy_result"
    assert (
        direct_payload["authoritative_answer"]["values"]
        == routed_payload["authoritative_answer"]["values"]
    )
    assert direct_payload["authoritative_answer"]["values"] == direct_payload["execution"]["result"]
    assert direct_payload["authoritative_answer"]["values"]["balanced"] is True

    validator = jsonschema.Draft202012Validator(_aa_schema())
    validator.validate(
        {
            "authoritative_answer_schema_version": direct_payload[
                "authoritative_answer_schema_version"
            ],
            "authoritative_answer": direct_payload["authoritative_answer"],
        }
    )


def test_energy_pv_power_agent_demo_energy_result(engine: Engine) -> None:
    result = call_tool(engine, "agent.energy", {"demo_label": "pv_power"})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "ok"
    assert payload["authoritative_answer"]["kind"] == "energy_result"
    assert payload["authoritative_answer"]["values"]["power"]["value"] == pytest.approx(2000.0)
    # values are execution.result verbatim (no nested authoritative_answer).
    assert payload["authoritative_answer"]["values"] == payload["execution"]["result"]
    assert "authoritative_answer" not in payload["authoritative_answer"]["values"]
