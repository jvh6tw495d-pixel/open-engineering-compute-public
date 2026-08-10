"""Unit tests for the free-text discovery fallback (oec.mcp.discovery)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oec.mcp.discovery import (
    SkillCandidate,
    _first_example,
    build_skill_suggestion_payload,
    needs_domain_clarification,
    rank_candidate_skills,
    rank_domain_intents,
)
from oec.sdk import Engine


@pytest.fixture(scope="module")
def engine() -> Engine:
    eng = Engine(skills_root="skills")
    eng.warm()
    return eng


def test_rank_candidate_skills_restricts_to_requested_domains(engine: Engine) -> None:
    candidates = rank_candidate_skills(
        engine, "resample this series", domains=("timeseries",), limit=10
    )
    assert candidates
    assert all(candidate.skill_id.startswith("timeseries.") for candidate in candidates)


def test_rank_candidate_skills_ranks_keyword_matches_first(engine: Engine) -> None:
    candidates = rank_candidate_skills(
        engine, "partial autocorrelation function", domains=("timeseries",), limit=3
    )
    assert candidates
    assert candidates[0].skill_id == "timeseries.pacf"


def test_rank_candidate_skills_never_empty_even_with_no_keyword_overlap(engine: Engine) -> None:
    """No keyword overlap at all must still surface something on-topic
    (bounded by domain) rather than an empty candidate list -- an empty
    list would be as much of a dead end as the ValueError this fallback
    replaces."""
    candidates = rank_candidate_skills(
        engine, "xyzzy plugh qwerty", domains=("timeseries",), limit=3
    )
    assert candidates
    assert len(candidates) <= 3


def test_rank_candidate_skills_respects_limit(engine: Engine) -> None:
    candidates = rank_candidate_skills(
        engine, "time series analysis", domains=("timeseries",), limit=2
    )
    assert len(candidates) <= 2


def test_rank_candidate_skills_each_candidate_has_real_schema(engine: Engine) -> None:
    candidates = rank_candidate_skills(engine, "levinson durbin", domains=("timeseries",), limit=5)
    assert candidates
    for candidate in candidates:
        assert candidate.input_schema
        assert candidate.input_schema.get("type") == "object"


def test_rank_candidate_skills_populates_example_when_skill_ships_one(engine: Engine) -> None:
    candidates = rank_candidate_skills(engine, "pacf order", domains=("timeseries",), limit=5)
    pacf = next(c for c in candidates if c.skill_id == "timeseries.pacf")
    assert pacf.example_inputs is not None
    assert isinstance(pacf.example_inputs, dict)


def test_first_example_unwraps_description_input_envelope(tmp_path: Path) -> None:
    """``example_inputs`` is an executable payload, never presentation metadata."""
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "wrapped.json").write_text(
        json.dumps({"description": "illustrative", "input": {"alpha": 0.5}}),
        encoding="utf-8",
    )

    assert _first_example(tmp_path) == {"alpha": 0.5}


def test_first_example_keeps_legacy_flat_payload(tmp_path: Path) -> None:
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "flat.json").write_text(json.dumps({"alpha": 0.5}), encoding="utf-8")

    assert _first_example(tmp_path) == {"alpha": 0.5}


def test_domain_intents_use_router_compatible_combined_names() -> None:
    intents = rank_domain_intents("design a PID controller")
    assert intents[0].domain == "control_dynamics"
    assert needs_domain_clarification(intents) is False


def test_domain_intents_rank_neural_and_evolutionary() -> None:
    """ADR 0031/0033 free-text vocabulary → neural specialist domain."""
    for request in (
        "train an MLP regressor with pytorch",
        "run NSGA2 multi-objective evolutionary search",
        "busca de arquitetura neural com neuroevolution",
    ):
        intents = rank_domain_intents(request)
        assert intents, request
        assert intents[0].domain == "neural", request
        assert needs_domain_clarification(intents) is False


def test_rank_candidate_skills_neural_domain(engine: Engine) -> None:
    candidates = rank_candidate_skills(
        engine, "train mlp regressor", domains=("neural", "evolutionary"), limit=10
    )
    assert candidates
    assert all(c.skill_id.startswith(("neural.", "evolutionary.")) for c in candidates)


def test_domain_intents_rank_dc_power_flow_under_energy() -> None:
    """Wave 4 discovery aliases: power-flow vocabulary → energy specialist domain."""
    intents = rank_domain_intents("solve a dc power flow on a meshed network")
    assert intents
    assert intents[0].domain == "energy"
    assert needs_domain_clarification(intents) is False


def test_domain_intents_empty_request_requires_clarification() -> None:
    assert needs_domain_clarification(rank_domain_intents("hello world")) is True


def test_build_skill_suggestion_payload_default_hint_and_shape() -> None:
    candidate = SkillCandidate(
        skill_id="timeseries.pacf",
        title="Partial Autocorrelation Function",
        description="Compute PACF via Levinson-Durbin.",
        input_schema={"type": "object"},
        example_inputs={"series": [1.0, 2.0], "nlags": 1},
    )
    payload = build_skill_suggestion_payload("agent.time_series", "compute the pacf", [candidate])
    assert payload["status"] == "needs_more_information"
    assert payload["agent"] == "agent.time_series"
    assert payload["request"] == "compute the pacf"
    assert "skill_id" in payload["hint"] or "candidates" in payload["hint"]
    assert payload["candidates"] == [
        {
            "skill_id": "timeseries.pacf",
            "title": "Partial Autocorrelation Function",
            "description": "Compute PACF via Levinson-Durbin.",
            "input_schema": {"type": "object"},
            "example_inputs": {"series": [1.0, 2.0], "nlags": 1},
        }
    ]


def test_build_skill_suggestion_payload_custom_hint_and_empty_candidates() -> None:
    payload = build_skill_suggestion_payload(
        "agent.scientific_reviewer",
        "check my result",
        [],
        hint="run another agent first",
    )
    assert payload["candidates"] == []
    assert payload["hint"] == "run another agent first"
