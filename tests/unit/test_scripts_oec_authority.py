"""Unit tests for the benchmark authority helper (v2.5.3 Wave 3a).

``scripts/_oec_authority.py`` is loaded by file path (same pattern as
``test_audit_physical_units.py``) and exercised offline with mocked tool
results — no MCP server, no network. Also pins the harness-side QuantityValue
guarantee: energy payloads keep ``{value, unit}`` through the envelope, and
``flatten_quantities`` recovers plain floats for scorers.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_SPEC = importlib.util.spec_from_file_location(
    "_oec_authority", _ROOT / "scripts" / "_oec_authority.py"
)
assert _SPEC is not None and _SPEC.loader is not None
authority = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = authority
_SPEC.loader.exec_module(authority)

from oec.mcp.envelope import AUTHORITATIVE_ANSWER_SCHEMA_VERSION, normalize  # noqa: E402


def _energy_execution() -> dict[str, Any]:
    """ExecutionResult wire dict with QuantityValue-shaped energy result."""
    return {
        "run_id": "run-energy-1",
        "status": "VALIDATED",
        "skill": {"id": "energy.load_metrics", "version": "0.2.0"},
        "method": {"id": "peak_average_load_factor", "version": "0.1.0"},
        "result": {
            "n": 4,
            "peak": {"value": 15.0, "unit": "W"},
            "average": {"value": 11.5, "unit": "W"},
            "load_factor": 0.7667,
            "min": {"value": 9.0, "unit": "W"},
        },
        "provenance": {"input_hash": "hash-energy-1"},
        "diagnostics": {},
        "started_at": "2026-08-02T00:00:00Z",
    }


def _energy_envelope() -> dict[str, Any]:
    report = {
        "agent": "agent.energy",
        "skill_id": "energy.load_metrics",
        "execution": _energy_execution(),
        "narrative": "Load metrics computed.",
    }
    return normalize(report, tool_name="agent.energy")


class _TextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeCallToolResult:
    """Minimal CallToolResult-like stub (mcp types not needed here)."""

    def __init__(self, payload: dict[str, Any], *, is_error: bool = False) -> None:
        self.content = [_TextBlock(json.dumps(payload))]
        self.isError = is_error


# ---------------------------------------------------------------------------
# read_authority / envelope coercion
# ---------------------------------------------------------------------------


def test_read_authority_from_envelope_dict() -> None:
    envelope = _energy_envelope()
    aa = authority.read_authority(envelope)
    assert aa is not None
    assert aa["kind"] == "energy_result"
    assert aa["provenance"]["run_id"] == "run-energy-1"


def test_read_authority_from_call_tool_result_stub() -> None:
    result = _FakeCallToolResult(_energy_envelope())
    aa = authority.read_authority(result)
    assert aa is not None
    assert aa["kind"] == "energy_result"


def test_read_authority_from_raw_json_text() -> None:
    aa = authority.read_authority(json.dumps(_energy_envelope()))
    assert aa is not None
    assert aa["values"]["n"] == 4


def test_read_authority_none_for_non_envelopes() -> None:
    assert authority.read_authority(None) is None
    assert authority.read_authority("host prose with no json") is None
    assert authority.read_authority({"some": "raw skill result"}) is None
    assert authority.read_authority({"error": "boom", "details": {"tool": "x"}}) is None
    assert authority.read_authority({"status": "needs_clarification"}) is None
    legacy = _energy_envelope()
    legacy["authoritative_answer_schema_version"] = "0.9"
    assert authority.read_authority(legacy) is None
    no_aa = _energy_envelope()
    no_aa.pop("authoritative_answer")
    assert authority.read_authority(no_aa) is None


def test_quantity_value_payloads_survive_envelope_and_flatten() -> None:
    """Energy QuantityValue payloads are not broken by the envelope (GATE-W3)."""
    envelope = _energy_envelope()
    aa = authority.read_authority(envelope)
    assert aa is not None
    # Verbatim QuantityValue shape preserved inside authoritative_answer.values.
    assert aa["values"]["peak"] == {"value": 15.0, "unit": "W"}
    assert aa["values"]["average"] == {"value": 11.5, "unit": "W"}
    # Harness scorers read plain floats via authority_values / flatten_quantities.
    values = authority.authority_values(envelope)
    assert values == {
        "n": 4,
        "peak": 15.0,
        "average": 11.5,
        "load_factor": 0.7667,
        "min": 9.0,
    }
    raw_values = authority.authority_values(envelope, flatten=False)
    assert raw_values is not None and raw_values["min"] == {"value": 9.0, "unit": "W"}
    nested = authority.flatten_quantities({"a": [{"value": 1, "unit": "Wh"}], "b": "x"})
    assert nested == {"a": [1.0], "b": "x"}


def test_routing_state_and_error_readers() -> None:
    assert authority.read_routing_state({"status": "needs_clarification"}) == "needs_clarification"
    assert authority.read_routing_state(_energy_envelope()) is None
    assert authority.read_error({"error": "boom"}) == "boom"
    assert authority.read_error({"code": "X", "message": "bad", "details": {}}) == "bad"
    assert authority.read_error(_energy_envelope()) is None


def test_envelope_contract_issues() -> None:
    assert authority.envelope_contract_issues(_energy_envelope()) == []
    issues = authority.envelope_contract_issues({"status": "ok"})
    assert "authoritative_answer_schema_version_missing_or_mismatch" in issues
    assert "problem_classification_missing_or_incomplete" in issues
    assert "method_summary_missing_or_incomplete" in issues
    no_aa = _energy_envelope()
    no_aa.pop("authoritative_answer")
    assert authority.envelope_contract_issues(no_aa) == []
    assert authority.envelope_contract_issues(no_aa, require_authority=True) == [
        "authoritative_answer_missing"
    ]
    assert authority.envelope_contract_issues("nope") == ["payload_not_object"]


# ---------------------------------------------------------------------------
# three_verdicts
# ---------------------------------------------------------------------------


def test_three_verdicts_transport_failure_short_circuits() -> None:
    verdicts = authority.three_verdicts(transport_error="hermes exit 1")
    assert verdicts.transport == authority.TRANSPORT_FAILURE
    assert verdicts.oec_execution == authority.NOT_REACHED
    assert verdicts.host_corruption == authority.NOT_EVALUATED
    assert verdicts.primary == authority.TRANSPORT_FAILURE
    assert "hermes exit 1" in verdicts.detail


def test_three_verdicts_oec_execution_failure_when_no_authority() -> None:
    verdicts = authority.three_verdicts({"error": "solver blew up"})
    assert verdicts.transport == authority.OK
    assert verdicts.oec_execution == authority.OEC_EXECUTION_FAILURE
    assert verdicts.host_corruption == authority.NOT_EVALUATED
    assert verdicts.primary == authority.OEC_EXECUTION_FAILURE
    assert "solver blew up" in verdicts.detail


def test_three_verdicts_routing_state_without_expectation_is_ok() -> None:
    payload = {"status": "needs_clarification", "questions": ["which domain?"]}
    relaxed = authority.three_verdicts(payload, expect_authority=False)
    assert relaxed.oec_execution == authority.OK
    assert relaxed.primary == authority.OK
    strict = authority.three_verdicts(payload, expect_authority=True)
    assert strict.oec_execution == authority.OEC_EXECUTION_FAILURE


def test_three_verdicts_success_defaults_host_corruption_pending_3b() -> None:
    verdicts = authority.three_verdicts(_FakeCallToolResult(_energy_envelope()))
    assert verdicts.transport == authority.OK
    assert verdicts.oec_execution == authority.OK
    assert verdicts.host_corruption == authority.PENDING_WAVE_3B
    assert verdicts.primary == authority.OK


def test_three_verdicts_host_corruption_comparator_hook() -> None:
    envelope = _energy_envelope()
    claim = {"peak": 15.0}

    def matches(claim_map: Any, aa: Any) -> bool:
        return float(claim_map["peak"]) == float(aa["values"]["peak"]["value"])

    clean = authority.three_verdicts(envelope, host_claim=claim, claim_compare=matches)
    assert clean.host_corruption == authority.OK
    assert clean.primary == authority.OK

    def diverges(claim_map: Any, aa: Any) -> bool:
        return float(claim_map["peak"]) == 999.0

    dirty = authority.three_verdicts(envelope, host_claim=claim, claim_compare=diverges)
    assert dirty.host_corruption == authority.HOST_CORRUPTION
    assert dirty.primary == authority.HOST_CORRUPTION


def test_three_verdicts_not_exercised_legs() -> None:
    verdicts = authority.three_verdicts(transport_error=None, oec_exercised=False)
    assert verdicts.transport == authority.OK
    assert verdicts.oec_execution == authority.NOT_EXERCISED
    assert verdicts.host_corruption == authority.NOT_APPLICABLE
    assert verdicts.primary == authority.OK

    oracle = authority.three_verdicts(
        _energy_envelope(), transport_exercised=False, detail="oracle: no host leg"
    )
    assert oracle.transport == authority.NOT_EXERCISED
    assert oracle.oec_execution == authority.OK
    assert oracle.primary == authority.OK

    skipped = authority.ThreeVerdicts.not_exercised("control arm")
    assert skipped.primary == authority.NOT_EXERCISED
    assert skipped.host_corruption == authority.NOT_APPLICABLE


def test_verdict_counts_labeled() -> None:
    sample = [
        authority.three_verdicts(_energy_envelope()),
        authority.three_verdicts(transport_error="cli died"),
        authority.three_verdicts({"error": "no aa"}),
        authority.ThreeVerdicts.not_exercised("arm A"),
    ]
    counts = authority.verdict_counts(sample)
    assert counts == {
        "total": 4,
        authority.OK: 1,
        authority.TRANSPORT_FAILURE: 1,
        authority.OEC_EXECUTION_FAILURE: 1,
        authority.HOST_CORRUPTION: 0,
        authority.NOT_EXERCISED: 1,
    }


def test_schema_version_constant_matches_envelope() -> None:
    assert authority.AUTHORITATIVE_ANSWER_SCHEMA_VERSION == AUTHORITATIVE_ANSWER_SCHEMA_VERSION
