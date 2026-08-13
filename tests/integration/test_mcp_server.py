"""Integration tests for the OEC MCP server (ADR 0015).

Exercises the real ``skills/`` directory through the same ``oec.sdk.Engine``
facade the CLI and REST API use — handler logic is tested directly (no stdio
transport) so failures point at dispatch/serialization rather than MCP framing.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import anyio
import pytest
from mcp import types as mcp_types

from oec.mcp.server import (
    LIST_AGENTS_TOOL_NAME,
    LIST_SKILLS_TOOL_NAME,
    _contains_token,
    _has_execution_payload,
    _infer_domain_from_request,
    _router_target_for,
    _run_specialist_by_name,
    build_server,
    build_tools,
    call_tool,
    run_stdio_server,
)
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


def test_list_tools_includes_agents_skills_and_discovery(engine: Engine) -> None:
    tools = build_tools(engine)
    by_name = {tool.name: tool for tool in tools}

    assert LIST_AGENTS_TOOL_NAME in by_name
    assert LIST_SKILLS_TOOL_NAME in by_name
    assert by_name[LIST_AGENTS_TOOL_NAME].inputSchema == {
        "type": "object",
        "properties": {},
    }
    assert by_name[LIST_SKILLS_TOOL_NAME].inputSchema == {
        "type": "object",
        "properties": {},
    }
    assert tools[0].name == "agent.default"

    skill_ids = {m.id for m in engine.registry.list_skills(include_retired=False)}
    assert "mathematics.solve_root" in skill_ids
    for skill_id in skill_ids:
        assert skill_id in by_name

    # inputSchema is the skill's real schema, not a hand-written copy.
    loaded = engine.registry.get_skill("mathematics.solve_root")
    assert by_name["mathematics.solve_root"].inputSchema == loaded.input_schema
    assert "Prefer `agent.default`" in by_name["mathematics.solve_root"].description

    # Agent-first catalog: specialists + discovery + experiment tools + raw skills.
    # 10 specialists (incl. agent.foundation) + list_agents + list_skills
    # + experiment.list_builders + experiment.run = 14.
    assert "experiment.run" in by_name
    assert "experiment.list_builders" in by_name
    assert "agent.foundation" in by_name
    assert len(tools) == len(skill_ids) + 14
    # foundation skills registered (W6)
    assert "foundation.embed" in skill_ids


def test_call_tool_experiment_list_builders(engine: Engine) -> None:
    result = call_tool(engine, "experiment.list_builders", {})
    assert result.isError is False
    catalog = _parse_content(result)
    assert isinstance(catalog, list)
    names = {row["name"] for row in catalog}
    assert "build_physics_kinematics_experiment" in names
    assert "build_wave_then_stats_experiment" in names
    for row in catalog:
        assert "domains" in row and "extras" in row


def test_call_tool_experiment_list_builders_includes_s4_evo(engine: Engine) -> None:
    """S4: public evo/hybrid builders appear on MCP with accurate metadata."""
    result = call_tool(engine, "experiment.list_builders", {})
    assert result.isError is False
    by_name = {row["name"]: row for row in _parse_content(result)}
    assert by_name["build_optimize_single_experiment"]["domains"] == ["evolutionary"]
    assert by_name["build_optimize_single_experiment"]["extras"] == ["evolutionary"]
    assert by_name["build_nsga2_experiment"]["domains"] == ["evolutionary"]
    assert by_name["build_nsga2_experiment"]["extras"] == ["evolutionary"]
    assert by_name["build_hybrid_training_experiment"]["domains"] == [
        "neural",
        "evolutionary",
    ]
    assert by_name["build_hybrid_training_experiment"]["extras"] == [
        "neural",
        "evolutionary",
    ]
    # Helpers stay invisible to hosts.
    assert "sphere_problem_2d" not in by_name
    assert "problem_to_optimize_inputs" not in by_name
    assert "build_mlp_regressor_experiment" not in by_name


def test_call_tool_experiment_run_named_builder(engine: Engine) -> None:
    result = call_tool(
        engine,
        "experiment.run",
        {
            "builder": "build_monte_carlo_then_describe_experiment",
            "builder_kwargs": {"seed": 0, "n_samples": 40},
        },
    )
    assert result.isError is False
    body = _parse_content(result)
    assert body["status"] == "COMPLETED"
    assert body["spec"]["id"] == "w7.mc_uncertainty"
    assert body["steps"]
    assert body["metrics"]


def test_call_tool_experiment_run_s4_nsga2_accepted_or_extra_fail_closed(
    engine: Engine,
) -> None:
    """S4: catalogued NSGA2 builder is known; run fails only if extras missing."""
    result = call_tool(
        engine,
        "experiment.run",
        {
            "builder": "build_nsga2_experiment",
            "builder_kwargs": {
                "n_var": 3,
                "generations": 4,
                "population": 8,
                "seed": 0,
            },
        },
    )
    body = _parse_content(result)
    if result.isError:
        # Fail-closed path: optional evolutionary extra (pymoo) absent.
        err = str(body.get("error", "")).lower()
        assert "unknown experiment builder" not in err
        assert any(
            token in err for token in ("pymoo", "evolutionary", "not installed", "extra")
        ), body
        return
    # With extras installed: named builder is runnable end-to-end.
    assert body["status"] in {"COMPLETED", "FAILED", "ABORTED"}
    assert body["spec"]["id"] == "evolutionary.nsga2"
    assert body["spec"]["required_extras"] == ["evolutionary"]


def test_call_tool_experiment_run_unknown_builder_fail_closed(engine: Engine) -> None:
    # F1: module callables outside the catalog must be rejected (not invoked).
    for bad in (
        "ExperimentSpec",
        "sphere_problem_2d",
        "problem_to_optimize_inputs",
        "build_mlp_regressor_experiment",
        "build_evo_then_describe_experiment",
        "list_cross_domain_builders",
        "not_a_builder",
    ):
        result = call_tool(engine, "experiment.run", {"builder": bad})
        assert result.isError is True, bad
        payload = _parse_content(result)
        assert "unknown experiment builder" in payload["error"].lower()


def test_call_tool_experiment_run_builder_kwargs_must_be_object(engine: Engine) -> None:
    result = call_tool(
        engine,
        "experiment.run",
        {
            "builder": "build_physics_kinematics_experiment",
            "builder_kwargs": ["not", "an", "object"],
        },
    )
    assert result.isError is True
    payload = _parse_content(result)
    assert "builder_kwargs" in payload["error"].lower()


def test_call_tool_solve_root_returns_validated_result(engine: Engine) -> None:
    result = call_tool(
        engine,
        "mathematics.solve_root",
        {"expression": "x**2 - 2", "bracket": [0, 2]},
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "VALIDATED"
    assert math.isclose(payload["result"]["root"], math.sqrt(2), rel_tol=1e-9)


def test_call_tool_list_skills_returns_catalog(engine: Engine) -> None:
    result = call_tool(engine, LIST_SKILLS_TOOL_NAME, {})
    assert result.isError is False
    catalog = _parse_content(result)
    assert isinstance(catalog, list)
    assert len(catalog) >= 6
    ids = {entry["id"] for entry in catalog}
    assert "mathematics.solve_root" in ids
    # Mirrors oec skills list --json shape (manifest dump with aliases).
    sample = next(entry for entry in catalog if entry["id"] == "mathematics.solve_root")
    assert "version" in sample
    assert "title" in sample
    assert "domain" in sample


def test_call_tool_list_agents_returns_catalog(engine: Engine) -> None:
    result = call_tool(engine, LIST_AGENTS_TOOL_NAME, {})
    assert result.isError is False
    catalog = _parse_content(result)
    assert isinstance(catalog, list)
    ids = {entry["id"] for entry in catalog}
    assert "agent.default" in ids
    sample = next(entry for entry in catalog if entry["id"] == "agent.default")
    assert sample["kind"] == "agent_router"
    assert sample["default"] is True


def test_call_tool_default_router_runs_optimization_agent(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.default",
        {"request": "solve optimization problem", "demo_label": "diet"},
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["router"] == "agent.default"
    assert payload["selected_agent"] == "agent.optimization_specialist"
    assert payload["result"]["skill_id"] == "optimization.lp"
    assert payload["result"]["execution"]["status"] == "VALIDATED"


def test_call_tool_optimization_agent_runs_demo(engine: Engine) -> None:
    result = call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["problem_class"] == "lp"
    assert payload["skill_id"] == "optimization.lp"
    assert payload["execution"]["status"] == "VALIDATED"


def test_call_tool_scientific_reviewer_reviews_agent_output(engine: Engine) -> None:
    solve = _parse_content(
        call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    )
    result = call_tool(
        engine,
        "agent.scientific_reviewer",
        {
            "ops_document": solve["ops"],
            "execution": solve["execution"],
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["passed"] is True


def test_call_tool_domain_agent_runs_explicit_skill(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.applied_mathematics",
        {
            "skill_id": "mathematics.solve_root",
            "inputs": {"expression": "x**2 - 2", "bracket": [0, 2]},
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["agent"] == "applied_mathematics_specialist"
    assert payload["skill_id"] == "mathematics.solve_root"
    assert payload["execution"]["status"] == "VALIDATED"


def test_call_tool_default_router_respects_explicit_skill(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": "call specific function",
            "skill_id": "mathematics.solve_root",
            "inputs": {"expression": "x**2 - 2", "bracket": [0, 2]},
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == "agent.applied_mathematics"
    assert payload["result"]["skill_id"] == "mathematics.solve_root"
    assert payload["result"]["execution"]["status"] == "VALIDATED"


def test_call_tool_optimization_agent_runs_full_ops(engine: Engine) -> None:
    ops = {
        "ops_version": "0.1.0",
        "problem_class": "lp",
        "sense": "min",
        "variables": [
            {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
            {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
        ],
        "constraints": [{"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}],
        "objective": {"coeffs": {"x": 1, "y": 1}},
    }
    result = call_tool(engine, "agent.optimization_specialist", {"ops": ops})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["skill_id"] == "optimization.lp"
    assert payload["execution"]["status"] == "VALIDATED"


def test_call_tool_optimization_agent_requires_ops_or_demo(engine: Engine) -> None:
    result = call_tool(engine, "agent.optimization_specialist", {})
    assert result.isError is True
    payload = _parse_content(result)
    assert "requires 'ops', 'demo_label', or both 'skill_id' and 'inputs'" in payload["error"]


def test_call_tool_optimization_agent_request_falls_back_to_candidates(engine: Engine) -> None:
    """A free-text ``request`` (no ops/demo_label) is a dead end for this
    specialist -- there's no NL-to-OPS parser -- but it must degrade to the
    discovery fallback's structured needs_more_information payload, not a
    bare ValueError."""
    result = call_tool(
        engine,
        "agent.optimization_specialist",
        {"request": "minimize cost of a linear blending problem"},
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "needs_more_information"
    assert payload["agent"] == "agent.optimization_specialist"
    assert payload["candidates"]
    for candidate in payload["candidates"]:
        assert candidate["skill_id"].startswith("optimization.")
        assert candidate["input_schema"]


def test_call_tool_default_router_optimization_request_returns_optimization_candidates(
    engine: Engine,
) -> None:
    """agent.default with a free-text optimization request + preferred_domain
    must surface at least one real optimization.* candidate (not silently
    drop the request or hand back an unrelated domain)."""
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
    assert payload["selected_agent"] == "agent.optimization_specialist"
    inner = payload["result"]
    assert inner["status"] == "needs_more_information"
    assert inner["candidates"]
    for candidate in inner["candidates"]:
        assert candidate["skill_id"].startswith("optimization.")


def test_optimization_agent_skill_id_plus_inputs_retry_closes_the_discovery_loop(
    engine: Engine,
) -> None:
    """Full cycle promised by the discovery fallback: request -> candidate ->
    retry with skill_id+inputs -> real, non-error ExecutionResult. Exercised
    both directly against agent.optimization_specialist and routed through
    agent.default (skill_id prefix routing), proving the loop actually
    closes end to end rather than dead-ending on 'requires ops or
    demo_label' as it did before this fix."""
    suggestion = _parse_content(
        call_tool(
            engine,
            "agent.optimization_specialist",
            {"request": "minimize cost of a linear blending problem"},
        )
    )
    assert suggestion["status"] == "needs_more_information"
    candidate = suggestion["candidates"][0]
    skill_id = candidate["skill_id"]
    inputs = candidate["example_inputs"]
    assert isinstance(inputs, dict)
    assert skill_id.startswith("optimization.")

    direct = call_tool(
        engine, "agent.optimization_specialist", {"skill_id": skill_id, "inputs": inputs}
    )
    assert direct.isError is False
    direct_payload = _parse_content(direct)
    assert direct_payload["skill_id"] == skill_id
    assert direct_payload["execution"]["status"] in {
        "VALIDATED",
        "VERIFIED",
        "CONVERGED_WITH_WARNINGS",
        "APPROXIMATE",
    }

    routed = call_tool(engine, "agent.default", {"skill_id": skill_id, "inputs": inputs})
    assert routed.isError is False
    routed_payload = _parse_content(routed)
    assert routed_payload["selected_agent"] == "agent.optimization_specialist"
    assert routed_payload["result"]["skill_id"] == skill_id
    assert routed_payload["result"]["execution"]["status"] in {
        "VALIDATED",
        "VERIFIED",
        "CONVERGED_WITH_WARNINGS",
        "APPROXIMATE",
    }


def test_optimization_agent_rejects_skill_id_outside_its_domain(engine: Engine) -> None:
    """The specialist must not silently run a non-optimization skill just
    because it was handed a valid skill_id+inputs pair -- that belongs to a
    different agent, and the error must be structured and explicit, not a
    crash or a raw traceback."""
    result = call_tool(
        engine,
        "agent.optimization_specialist",
        {
            "skill_id": "mathematics.solve_root",
            "inputs": {"expression": "x**2 - 2", "bracket": [0, 2]},
        },
    )
    assert result.isError is True
    payload = _parse_content(result)
    assert "optimization.*" in payload["error"]
    assert payload["details"]["tool"] == "agent.optimization_specialist"


def test_call_tool_scientific_reviewer_requires_execution(engine: Engine) -> None:
    result = call_tool(engine, "agent.scientific_reviewer", {})
    assert result.isError is True
    payload = _parse_content(result)
    assert "requires 'execution'" in payload["error"]


def test_call_tool_scientific_reviewer_request_without_execution_explains_prerequisite(
    engine: Engine,
) -> None:
    """The reviewer audits a prior ExecutionResult; it has no skills of its
    own to suggest. A bare ``request`` must not error -- it should explain
    that an execution is the actual prerequisite."""
    result = call_tool(
        engine, "agent.scientific_reviewer", {"request": "check my optimization result"}
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "needs_more_information"
    assert payload["candidates"] == []
    assert "execution" in payload["hint"]


def test_call_tool_applied_math_request_falls_back_to_candidates_when_unparseable(
    engine: Engine,
) -> None:
    """``run_request`` only understands a narrow scalar-extrema grammar
    (f(x)=... over [a, b]); anything else must fall back to the discovery
    fallback instead of surfacing the parser's raw ValueError."""
    result = call_tool(
        engine, "agent.applied_mathematics", {"request": "please analyze my dataset for me"}
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "needs_more_information"
    assert payload["candidates"]
    for candidate in payload["candidates"]:
        assert candidate["input_schema"]


def test_call_tool_time_series_agent_runs_demo(engine: Engine) -> None:
    result = call_tool(engine, "agent.time_series", {"demo_label": "resample"})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["agent"] == "time_series_specialist"
    assert payload["execution"]["status"] == "VERIFIED"


def test_call_tool_energy_agent_runs_demo(engine: Engine) -> None:
    result = call_tool(engine, "agent.energy", {"demo_label": "balance"})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["agent"] == "energy_specialist"
    assert payload["execution"]["status"] == "VERIFIED"


def test_call_tool_neural_agent_runs_evolutionary_demo(engine: Engine) -> None:
    result = call_tool(engine, "agent.neural", {"demo_label": "optimize_single"})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["agent"] == "neural_evolutionary_specialist"
    assert payload["skill_id"] == "evolutionary.optimize_single"
    assert payload["execution"]["status"] in {"VALIDATED", "VERIFIED"}
    assert "run_id" in payload["narrative"]


def test_call_tool_neural_agent_lists_neural_candidates(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.neural",
        {"request": "train a multi-layer perceptron for regression"},
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "needs_more_information"
    assert payload["candidates"]
    for candidate in payload["candidates"]:
        assert candidate["skill_id"].startswith(("neural.", "evolutionary."))
        assert candidate["input_schema"]


def test_list_tools_exposes_neural_agent_and_raw_skills(engine: Engine) -> None:
    tools = build_tools(engine)
    by_name = {tool.name: tool for tool in tools}
    assert "agent.neural" in by_name
    assert "neural.mlp.regressor" in by_name
    assert "neural.training.hybrid" in by_name
    assert "evolutionary.optimize_single" in by_name
    props = by_name["agent.neural"].inputSchema["properties"]
    assert "skill_id" in props and "inputs" in props and "demo_label" in props


def test_call_tool_domain_agent_requires_demo_or_skill(engine: Engine) -> None:
    result = call_tool(engine, "agent.time_series", {})
    assert result.isError is True
    payload = _parse_content(result)
    assert "requires 'demo_label'" in payload["error"]


def test_call_tool_energy_agent_request_falls_back_to_candidates(engine: Engine) -> None:
    result = call_tool(
        engine, "agent.energy", {"request": "estimate battery state of charge over time"}
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "needs_more_information"
    assert payload["candidates"]
    for candidate in payload["candidates"]:
        assert candidate["skill_id"].split(".", 1)[0] in {"energy", "battery", "electrical"}
        assert candidate["input_schema"]


@pytest.mark.parametrize(
    ("preferred_domain", "expected_agent"),
    [
        ("optimization", "agent.optimization_specialist"),
        ("mathematics", "agent.applied_mathematics"),
        ("timeseries", "agent.time_series"),
        ("energy", "agent.energy"),
        ("neural", "agent.neural"),
    ],
)
def test_call_tool_default_router_respects_preferred_domain(
    engine: Engine, preferred_domain: str, expected_agent: str
) -> None:
    demo_by_agent = {
        "agent.optimization_specialist": "diet",
        "agent.applied_mathematics": "sqrt2",
        "agent.time_series": "resample",
        "agent.energy": "balance",
        "agent.neural": "optimize_single",
    }
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": "route me",
            "preferred_domain": preferred_domain,
            "demo_label": demo_by_agent[expected_agent],
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == expected_agent


def test_call_tool_default_router_respects_review_preferred_domain(engine: Engine) -> None:
    solve = _parse_content(
        call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    )
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": "review this",
            "preferred_domain": "review",
            "ops_document": solve["ops"],
            "execution": solve["execution"],
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == "agent.scientific_reviewer"
    assert payload["result"]["passed"] is True


@pytest.mark.parametrize(
    ("arguments", "expected_agent"),
    [
        ({"ops": {"problem_class": "lp"}}, "agent.optimization_specialist"),
        ({"ops_document": {"problem_class": "lp"}}, "agent.optimization_specialist"),
        ({"preferred_domain": "review"}, "agent.scientific_reviewer"),
    ],
)
def test_router_target_for_ops_and_review_signals(
    arguments: dict[str, Any], expected_agent: str
) -> None:
    assert _router_target_for(arguments) == expected_agent


_VALID_EXECUTION_STUB = {
    "status": "VALIDATED",
    "skill": {"id": "optimization.lp", "version": "0.1.0"},
    "method": {"id": "highs", "version": "0.1.0"},
    "started_at": "2026-07-30T00:00:00Z",
}


def test_has_execution_payload_rejects_empty_or_incomplete_dicts() -> None:
    """A hallucinated ``execution: {}`` (or any dict missing an
    ExecutionResult-required key) must not count as a real execution."""
    assert _has_execution_payload({"execution": {}}) is False
    assert _has_execution_payload({"execution": {"status": "VALIDATED"}}) is False
    assert _has_execution_payload({}) is False
    assert _has_execution_payload({"execution": "not-a-dict"}) is False
    assert _has_execution_payload({"execution": _VALID_EXECUTION_STUB}) is True


@pytest.mark.parametrize(
    ("arguments", "expected_agent"),
    [
        (
            {"execution": {}, "ops": {"problem_class": "lp"}},
            "agent.optimization_specialist",
        ),
        (
            {"execution": {}, "preferred_domain": "mathematics"},
            "agent.applied_mathematics",
        ),
        (
            {"execution": _VALID_EXECUTION_STUB},
            "agent.scientific_reviewer",
        ),
    ],
)
def test_router_target_for_empty_execution_does_not_outrank_real_signals(
    arguments: dict[str, Any], expected_agent: str
) -> None:
    """Regression: local LLMs sometimes hallucinate an empty/placeholder
    ``execution: {}`` alongside a clear ops/preferred_domain signal. A bare
    empty dict must not win over those -- only a real ExecutionResult-shaped
    execution should route to the reviewer."""
    assert _router_target_for(arguments) == expected_agent


def test_call_tool_default_router_knapsack_request_with_empty_execution_does_not_hit_reviewer(
    engine: Engine,
) -> None:
    """The real stress-test failure mode: a local model sends a knapsack
    optimization request with ``preferred_domain: 'optimization'``, valid
    ``ops``, AND a hallucinated ``execution: {}`` all in the same call. This
    must run the optimization specialist and succeed -- not get diverted to
    agent.scientific_reviewer and fail with a validation error over the
    empty execution."""
    # Same shape as OptimizationSpecialist's own "knapsack" demo_ops_from_label
    # (agents/optimization_specialist/specialist.py), so this test exercises
    # the router, not OPS-schema edge cases.
    ops = {
        "ops_version": "0.1.0",
        "problem_class": "milp",
        "sense": "max",
        "name": "knapsack_regression",
        "assumptions": ["Binary items", "Single weight constraint"],
        "variables": [
            {"name": "a", "kind": "binary"},
            {"name": "b", "kind": "binary"},
        ],
        "constraints": [{"name": "weight", "coeffs": {"a": 2, "b": 1}, "sense": "<=", "rhs": 2}],
        "objective": {"coeffs": {"a": 3, "b": 2}},
    }
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": "Solve this 0/1 knapsack problem and maximize value under capacity.",
            "preferred_domain": "optimization",
            "ops": ops,
            "execution": {},
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == "agent.optimization_specialist"
    assert payload["result"]["execution"]["status"] in {
        "VALIDATED",
        "VERIFIED",
        "CONVERGED_WITH_WARNINGS",
        "APPROXIMATE",
    }


def test_contains_token_requires_word_boundary_not_bare_substring() -> None:
    """Regression: ``"lp" in text``/``"ops" in text`` used to match inside
    unrelated words ('he**lp**', 'sh**ops**'), silently misrouting generic
    requests to the optimization domain."""
    assert _contains_token("please help me", "lp") is False
    assert _contains_token("browse the shops", "ops") is False
    assert _contains_token("solve this lp problem", "lp") is True
    assert _contains_token("opens a new ops document", "ops") is True
    # Deliberate stem/prefix matches must still work (no trailing boundary).
    assert _contains_token("respeite as restrições", "restri") is True
    assert _contains_token("this is about autocorrelation", "autocorrelat") is True


def test_infer_domain_from_request_does_not_misroute_on_substring() -> None:
    assert _infer_domain_from_request("Help me with my engineering problem") is None
    assert _infer_domain_from_request("Solve this LP problem for me") == "optimization"


def test_infer_domain_foundation_before_neural_on_transformers() -> None:
    """HF library name must route foundation, not neural via 'transformer' stem."""
    assert _infer_domain_from_request("use transformers embeddings") == "foundation"
    assert _infer_domain_from_request("huggingface llm embedding") == "foundation"
    assert _infer_domain_from_request("train a transformer network with torch") == "neural"
    assert _infer_domain_from_request("mlp neural regressor") == "neural"


@pytest.mark.parametrize(
    ("skill_id", "expected_agent"),
    [
        ("optimization.lp", "agent.optimization_specialist"),
        ("timeseries.resample", "agent.time_series"),
        ("energy.balance", "agent.energy"),
        ("battery.soc_step", "agent.energy"),
        ("electrical.three_phase_balance", "agent.energy"),
        ("neural.mlp.regressor", "agent.neural"),
        ("evolutionary.optimize_single", "agent.neural"),
        ("neural.training.hybrid", "agent.neural"),
        ("foundation.embed", "agent.foundation"),
        ("waves.phase_speed", "agent.energy"),
        ("em.coulomb", "agent.energy"),
    ],
)
def test_call_tool_default_router_infers_agent_from_skill_prefix(
    engine: Engine, skill_id: str, expected_agent: str
) -> None:
    assert _router_target_for({"skill_id": skill_id}) == expected_agent


@pytest.mark.parametrize(
    ("demo_label", "expected_agent"),
    [
        ("knapsack", "agent.optimization_specialist"),
        ("solve_root", "agent.applied_mathematics"),
        ("fill_missing", "agent.time_series"),
        ("soc_step", "agent.energy"),
        ("mlp_regressor", "agent.neural"),
        ("optimize_single", "agent.neural"),
        ("nsga2", "agent.neural"),
    ],
)
def test_call_tool_default_router_infers_agent_from_demo_label(
    engine: Engine, demo_label: str, expected_agent: str
) -> None:
    assert _router_target_for({"demo_label": demo_label}) == expected_agent


def test_call_tool_default_router_raises_when_no_signal(engine: Engine) -> None:
    result = call_tool(engine, "agent.default", {"request": "do something vague"})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "needs_clarification"


def test_call_tool_default_router_infers_mathematics_from_request(engine: Engine) -> None:
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


def test_call_tool_default_router_solves_clock_offset_extrema_request(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": (
                "Durante várias semanas, o departamento de trânsito registrou a velocidade "
                "média v(t)=t^3 - 10,5 t^2 + 30 t + 20 km/h, onde t é o número de horas "
                "após o meio-dia. Qual o instante, entre 13 e 18 horas, em que o trânsito "
                "é mais rápido? E qual o instante em que ele é mais lento?"
            )
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    report = payload["result"]
    assert payload["selected_agent"] == "agent.applied_mathematics"
    assert report["bounds"] == [1.0, 6.0]
    assert report["offset_hours"] == 12.0
    min_x = report["min_execution"]["result"]["x"]
    max_x = report["max_execution"]["result"]["x"]
    min_value = report["min_execution"]["result"]["fun"]
    max_value = -report["max_execution"]["result"]["fun"]
    assert math.isclose(min_x, 5.0, rel_tol=0, abs_tol=1e-3)
    assert math.isclose(max_x, 2.0, rel_tol=0, abs_tol=1e-3)
    assert math.isclose(min_value, 32.5, rel_tol=0, abs_tol=1e-3)
    assert math.isclose(max_value, 46.0, rel_tol=0, abs_tol=1e-3)


@pytest.mark.parametrize(
    "request_text",
    [
        "What is the autocorrelation of this series?",
        "Compute the PACF for order selection.",
        "Fit an AR model using Yule-Walker estimation.",
        "Run the Levinson-Durbin recursion on this autocovariance sequence.",
        "Estimate autoregressive coefficients for this time series.",
    ],
)
def test_call_tool_default_router_infers_timeseries_from_ar_request(
    engine: Engine, request_text: str
) -> None:
    """Keyword routing (v2.5.1): the AR/ACF/PACF/Yule-Walker/Levinson-Durbin
    keywords route a request-only call to agent.time_series. No
    NL-argument-extraction parser exists for arbitrary numeric series, so
    the specialist still can't run anything on its own -- but instead of a
    bare error it now returns the discovery fallback's structured
    needs_more_information payload (real candidate skills, not a dead
    end), proving both that routing recognized the keywords and that the
    fallback engaged rather than raising."""
    result = call_tool(engine, "agent.default", {"request": request_text})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == "agent.time_series"
    inner = payload["result"]
    assert inner["status"] == "needs_more_information"
    assert inner["candidates"], "expected at least one candidate skill"
    for candidate in inner["candidates"]:
        assert candidate["skill_id"].startswith("timeseries.")
        assert candidate["input_schema"]


def test_call_tool_default_router_executes_ar_yule_walker_via_request_plus_skill(
    engine: Engine,
) -> None:
    """The realistic invocation pattern for this domain: a natural-language
    request carries intent for routing, while skill_id+inputs -- not a
    fabricated NL argument parse -- carries the actual numeric input. Proves
    the full MCP path (router -> agent.time_series -> real skill execution)
    is callable end-to-end for the new AR package."""
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": "Estimate the AR(1) coefficient of this series via Yule-Walker.",
            "skill_id": "timeseries.ar_yule_walker",
            "inputs": {"series": [1.0, -1.0, 1.0, -1.0], "order": 1},
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == "agent.time_series"
    assert payload["result"]["skill_id"] == "timeseries.ar_yule_walker"
    assert payload["result"]["execution"]["status"] == "VERIFIED"
    assert math.isclose(
        payload["result"]["execution"]["result"]["ar_coefficients"][0],
        -0.75,
        rel_tol=0,
        abs_tol=1e-9,
    )


def test_call_tool_default_router_explicit_skill_id_wins_over_ar_keywords(
    engine: Engine,
) -> None:
    """Explicit skill_id must win over the request-text heuristic even when
    the request text itself contains AR/timeseries keywords -- routing by
    skill_id prefix is checked before the request-based fallback."""
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": "This mentions autocorrelation and Yule-Walker but asks for a root.",
            "skill_id": "mathematics.solve_root",
            "inputs": {"expression": "x**2 - 2", "bracket": [0, 2]},
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == "agent.applied_mathematics"
    assert payload["result"]["skill_id"] == "mathematics.solve_root"


def test_run_specialist_by_name_rejects_unknown_agent_tool(engine: Engine) -> None:
    """Defensive branch: unreachable through call_tool's `_AGENT_TOOL_SCHEMAS`
    gate, but guards `_run_specialist_by_name` itself against misuse."""
    with pytest.raises(ValueError, match="Unknown agent tool"):
        _run_specialist_by_name(engine, "agent.not_a_real_agent", {})


def test_call_tool_unknown_skill_fails_gracefully(engine: Engine) -> None:
    result = call_tool(engine, "mathematics.not_a_real_skill", {})
    assert result.isError is True
    payload = _parse_content(result)
    assert "error" in payload or "code" in payload
    # Must not raise — the MCP session stays up.


def test_mcp_conforms_to_engine_run(engine: Engine) -> None:
    """ADR 0005: same inputs via Engine.run and MCP call_tool yield the same
    scientific content (status + numeric result). Transport-only fields
    (run_id, timestamps) may differ across the two executions.
    """
    inputs = {"expression": "x**2 - 2", "bracket": [0, 2]}
    sdk_result = engine.run("mathematics.solve_root", inputs)
    mcp_result = call_tool(engine, "mathematics.solve_root", inputs)

    assert mcp_result.isError is False
    payload = _parse_content(mcp_result)
    assert payload["status"] == sdk_result.status.value
    assert math.isclose(
        payload["result"]["root"],
        sdk_result.result["root"],
        rel_tol=1e-12,
    )
    # Diagnostics/method identity should match for the same deterministic skill.
    assert payload["method"]["id"] == sdk_result.method.id
    assert payload["diagnostics"]["converged"] is sdk_result.diagnostics["converged"]


def test_build_server_registers_handlers(engine: Engine) -> None:
    server = build_server(engine)
    assert server.name == "oec"
    # Handlers are registered on the low-level Server request map.
    assert mcp_types.ListToolsRequest in server.request_handlers
    assert mcp_types.CallToolRequest in server.request_handlers


def test_registered_handler_reports_invalid_input_in_band(engine: Engine) -> None:
    """Regression guard (independent review of Sprint 07): the mcp SDK's
    call_tool() decorator pre-validates `arguments` against the tool's
    inputSchema *before* the handler runs, by default -- for a schema
    violation, that short-circuits straight to a bare isError=True
    result with no ExecutionResult at all, silently diverging from
    ADR 0005 (the SDK/CLI/REST all deliver a schema violation as an
    in-band ExecutionStatus.INVALID, not a transport-level error).
    build_server() registers with validate_input=False specifically so
    OEC's own pipeline stays the source of truth for INVALID -- this
    test drives the actual registered handler (server.request_handlers),
    not the inner call_tool() function directly, which is exactly the
    layer the original bug lived in and every other test in this file
    bypasses."""
    server = build_server(engine)
    handler = server.request_handlers[mcp_types.CallToolRequest]

    request = mcp_types.CallToolRequest(
        params=mcp_types.CallToolRequestParams(
            name="mathematics.solve_root",
            arguments={
                "expression": "x**2 - 2",
                "bracket": [0, 2],
                "unexpected_field": True,  # violates input.schema.json's additionalProperties
            },
        )
    )
    server_result = anyio.run(handler, request)

    result = server_result.root
    assert isinstance(result, mcp_types.CallToolResult)
    assert result.isError is False
    payload = json.loads(result.content[0].text)
    assert payload["status"] == "INVALID"


def test_run_stdio_server_warms_and_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entrypoint builds/warms Engine and hands off to anyio without a real stdio."""
    ran: dict[str, bool] = {}

    def fake_run(func: Any, *args: Any, **kwargs: Any) -> None:
        ran["called"] = True

    monkeypatch.setattr("oec.mcp.server.anyio.run", fake_run)
    run_stdio_server(skills_root="skills")
    assert ran.get("called") is True


def test_call_tool_oec_error_from_run_is_error_result(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If Engine.run raises OECError after the tool was listed, surface as error."""
    from oec.errors import SkillNotFoundError

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise SkillNotFoundError("gone", details={"skill_id": "mathematics.solve_root"})

    monkeypatch.setattr(engine, "run", boom)
    result = call_tool(
        engine,
        "mathematics.solve_root",
        {"expression": "x - 1", "bracket": [0, 2]},
    )
    assert result.isError is True
    payload = _parse_content(result)
    assert payload["code"] == "skill_not_found"
    assert "message" in payload


def test_call_tool_unexpected_exception_from_specialist_is_structured_error(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A specialist's lazy import (or any other unexpected exception, not
    just OECError/ValueError/TypeError) must still come back as the
    codebase's own structured {"error", "details": {"tool": ...}} shape --
    not fall through to the mcp SDK's generic plain-text error path, which
    drops the tool name and the structured details entirely."""
    import oec.mcp.server as server_module

    def boom(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise ModuleNotFoundError("No module named 'agents'")

    monkeypatch.setattr(server_module, "_run_specialist_by_name", boom)
    result = call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    assert result.isError is True
    payload = _parse_content(result)
    assert payload["error"] == "ModuleNotFoundError: No module named 'agents'"
    assert payload["details"] == {
        "tool": "agent.optimization_specialist",
        "error_type": "ModuleNotFoundError",
    }


def test_call_tool_unexpected_exception_from_engine_run_is_structured_error(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same guarantee on the raw-skill dispatch path: an unexpected,
    non-OECError exception from Engine.run() must not escape as a
    differently-shaped error."""

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(engine, "run", boom)
    result = call_tool(
        engine,
        "mathematics.solve_root",
        {"expression": "x - 1", "bracket": [0, 2]},
    )
    assert result.isError is True
    payload = _parse_content(result)
    assert payload["error"] == "RuntimeError: boom"
    assert payload["details"] == {
        "tool": "mathematics.solve_root",
        "error_type": "RuntimeError",
    }


def test_call_tool_non_dict_arguments_fails_gracefully(engine: Engine) -> None:
    """call_tool() is a public, directly-callable surface whose whole
    point is 'never raise' -- a non-dict `arguments` (not reachable
    through the real MCP transport, which types this as dict | None,
    but reachable if called directly, as this test does) must not crash
    it (independent review of Sprint 07)."""
    result = call_tool(engine, "mathematics.solve_root", ["not", "a", "dict"])  # type: ignore[arg-type]
    assert result.isError is True
    payload = _parse_content(result)
    assert "error" in payload


def test_exports_from_package() -> None:
    from oec.mcp import build_server as exported_build
    from oec.mcp import run_stdio_server as exported_run

    assert exported_build is build_server
    assert exported_run is run_stdio_server


@pytest.mark.parametrize(
    ("request_text", "expected_agent"),
    [
        ("maximize profit subject to capacity constraints", "agent.optimization_specialist"),
        ("design a PID controller", "agent.control_dynamics"),
        ("train a neural network MLP with pytorch", "agent.neural"),
        ("run NSGA2 multi-objective evolutionary optimization", "agent.neural"),
    ],
)
def test_default_router_uses_weighted_domain_intent(
    engine: Engine, request_text: str, expected_agent: str
) -> None:
    result = call_tool(engine, "agent.default", {"request": request_text})
    assert result.isError is False
    assert _parse_content(result)["selected_agent"] == expected_agent


def test_default_router_returns_structured_clarification_for_unknown_intent(engine: Engine) -> None:
    result = call_tool(engine, "agent.default", {"request": "hello engineering world"})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "needs_clarification"
    assert payload["reason"] == "intent_absent"
    assert len(payload["questions"]) == 3


def test_default_router_routes_new_demo_labels(engine: Engine) -> None:
    result = call_tool(engine, "agent.default", {"demo_label": "pid"})
    assert result.isError is False
    assert _parse_content(result)["selected_agent"] == "agent.control_dynamics"


_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_agent_tools_importable_outside_repo_root_cwd(tmp_path: Path) -> None:
    """Reproduces the real host agent/MCP failure mode: a host process that
    launches the installed ``oec`` package from a cwd other than the repo
    root, with no ``PYTHONPATH`` pointing back at it.

    ``agents/`` lives outside ``src/oec`` with no ``__init__.py``, so before
    ``oec.mcp.server`` learned to resolve its own repo root, importing it
    from a foreign cwd raised ``ModuleNotFoundError: No module named
    'agents'`` on every ``agent.*`` tool call -- even though the identical
    call succeeded under pytest, which happens to run from the repo root.
    This must not depend on the caller's cwd or on the caller manually
    exporting ``PYTHONPATH``.
    """
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    script = f"""
import json
from oec.mcp.server import call_tool
from oec.sdk import Engine

engine = Engine(skills_root={str(_REPO_ROOT / "skills")!r})
engine.warm()
result = call_tool(engine, "agent.optimization_specialist", {{"demo_label": "diet"}})
print(json.dumps({{"isError": result.isError, "text": result.content[0].text}}))
"""
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "No module named 'agents'" not in proc.stderr, proc.stderr
    assert proc.returncode == 0, proc.stderr

    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["isError"] is False, payload["text"]


# ---------------------------------------------------------------------------
# Wave 2 (v2.5.3): claimed_answer / host_output_diverged
# ---------------------------------------------------------------------------


def test_call_tool_optimization_agent_corrupted_claim_flags_divergence_without_altering_aa(
    engine: Engine,
) -> None:
    result = call_tool(
        engine,
        "agent.optimization_specialist",
        {"demo_label": "diet", "claimed_answer": {"objective_value": -999999.0}},
    )
    assert result.isError is False
    payload = _parse_content(result)

    # AA remains the numeric truth -- never overwritten by the host's claim.
    assert payload["authoritative_answer"]["values"]["objective_value"] == 1.0

    assert "host_output_diverged" in payload
    warning = payload["host_output_diverged"]
    assert warning["policy_version"] == "1.0"
    assert warning["reason"] == "value_mismatch"
    assert any(m["path"] == "$.objective_value" for m in warning["mismatches"])


def test_call_tool_optimization_agent_matching_claim_has_no_divergence_warning(
    engine: Engine,
) -> None:
    result = call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    payload = _parse_content(result)
    matching_claim = payload["authoritative_answer"]["values"]

    claimed_result = call_tool(
        engine,
        "agent.optimization_specialist",
        {"demo_label": "diet", "claimed_answer": matching_claim},
    )
    claimed_payload = _parse_content(claimed_result)
    assert "host_output_diverged" not in claimed_payload


def test_call_tool_without_claimed_answer_has_no_divergence_warning(engine: Engine) -> None:
    result = call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    payload = _parse_content(result)
    assert "host_output_diverged" not in payload


def test_call_tool_default_router_corrupted_claim_flags_divergence_on_top_level_result(
    engine: Engine,
) -> None:
    result = call_tool(
        engine,
        "agent.default",
        {"demo_label": "diet", "claimed_answer": {"objective_value": 0.0}},
    )
    assert result.isError is False
    payload = _parse_content(result)
    # Router still nests the specialist report under "result" (Wave 1 nesting
    # is untouched); the divergence warning mirrors at the top level like the
    # rest of the envelope.
    assert payload["result"]["skill_id"] == "optimization.lp"
    assert "host_output_diverged" in payload
    assert payload["authoritative_answer"]["values"]["objective_value"] == 1.0


def test_call_tool_scientific_reviewer_claimed_answer_coexists_with_claimed_objective(
    engine: Engine,
) -> None:
    solve = _parse_content(
        call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    )
    result = call_tool(
        engine,
        "agent.scientific_reviewer",
        {
            "ops_document": solve["ops"],
            "execution": solve["execution"],
            "claimed_objective": solve["execution"]["result"]["objective_value"],
            "claimed_solver_status": "optimal",
            "claimed_answer": {"passed": False},
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    # claimed_objective/claimed_solver_status still drive the reviewer's own
    # domain checks (unaffected -- review passes since both match).
    assert payload["passed"] is True
    # claimed_answer disagrees with the actual review verdict (True != False).
    assert "host_output_diverged" in payload
    assert payload["authoritative_answer"]["values"]["passed"] is True


def test_call_tool_claimed_answer_with_no_authoritative_answer_flags_no_authority(
    engine: Engine,
) -> None:
    result = call_tool(
        engine,
        "agent.default",
        {"request": "hello engineering world", "claimed_answer": {"x": 1.0}},
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "needs_clarification"
    assert "authoritative_answer" not in payload
    assert "host_output_diverged" not in payload
