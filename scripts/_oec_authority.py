"""Shared OEC-authority helpers for benchmark harnesses (v2.5.3 Wave 3a).

Benchmarks measure OEC **authority**: the ``authoritative_answer`` carried by
the agent-tool envelope (``src/oec/mcp/envelope.py``), never numbers scraped
from host prose. This module gives the core harnesses
(``hermes_supertest.py``, ``multiagent_with_without_oec.py``,
``ollama_agent_stress_test.py``) one shared way to:

1. ``read_authority`` — pull the ``authoritative_answer`` out of an MCP tool
   result (parsed payload dict, raw JSON text, or a ``CallToolResult``-like
   object with ``.content`` text blocks). Returns ``None`` when the payload is
   not a schema-1.0 envelope or carries no authoritative answer.
2. ``three_verdicts`` — classify a run into the three labeled verdicts
   required by GATE-W3:

   - ``transport_failure``: the host/channel broke before authority could be
     read (CLI error, timeout, unparseable host output).
   - ``oec_execution_failure``: OEC was invoked but produced no authoritative
     answer (structured error, blocked execution status, missing envelope).
   - ``host_corruption``: OEC answered authoritatively but the host's
     presented answer diverges from it. The full claim/compare verdict lands
     in **Wave 3b** on top of the Wave-2 ``claimed_answer`` channel; 3a ships
     the labeled slot (``pending_wave_3b``) plus the ``claim_compare`` hook
     that 3b will wire to the real comparator.

Anti-pattern enforced here: ``with_oec_*`` paths must take their numeric truth
from ``read_authority(...)`` / ``authority_values(...)`` — never from
``extract_json`` over host prose. ``extract_json`` remains legitimate only for
(a) host-only control arms and (b) host *claims* recorded for 3b comparison.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from oec.mcp.divergence import detect_divergence  # noqa: E402
from oec.mcp.envelope import AUTHORITATIVE_ANSWER_SCHEMA_VERSION  # noqa: E402

# ---------------------------------------------------------------------------
# Verdict labels (GATE-W3) — exactly three failure classes + state markers.
# ---------------------------------------------------------------------------
TRANSPORT_FAILURE = "transport_failure"
OEC_EXECUTION_FAILURE = "oec_execution_failure"
HOST_CORRUPTION = "host_corruption"

OK = "ok"
PENDING_WAVE_3B = "pending_wave_3b"
NOT_EXERCISED = "not_exercised"
NOT_APPLICABLE = "not_applicable"
NOT_EVALUATED = "not_evaluated"
NOT_REACHED = "not_reached"

#: The three failure classes, in precedence order (first failure wins primary).
VERDICT_LABELS = (TRANSPORT_FAILURE, OEC_EXECUTION_FAILURE, HOST_CORRUPTION)

_ROUTING_STATES = ("needs_clarification", "needs_more_information")


@dataclass(frozen=True)
class ThreeVerdicts:
    """Three labeled verdict slots for one benchmark run.

    ``primary`` is the first failure in precedence order
    (transport → OEC execution → host corruption), else ``ok`` (or
    ``not_exercised`` for runs that never touch the OEC-authority pipeline).
    """

    transport: str
    oec_execution: str
    host_corruption: str
    primary: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def not_exercised(cls, reason: str = "") -> ThreeVerdicts:
        """Verdicts for a run that never touches the OEC-authority pipeline."""
        return cls(
            transport=NOT_EXERCISED,
            oec_execution=NOT_EXERCISED,
            host_corruption=NOT_APPLICABLE,
            primary=NOT_EXERCISED,
            detail=reason,
        )


def coerce_payload(tool_result: Any) -> dict[str, Any] | None:
    """Coerce a tool result into its payload dict, or ``None``.

    Accepts an already-parsed payload mapping, raw JSON text, or a
    ``CallToolResult``-like object whose ``.content`` blocks carry ``.text``.
    Strict JSON only — host prose is *not* scraped here on purpose.
    """
    if tool_result is None:
        return None
    if isinstance(tool_result, Mapping):
        return dict(tool_result)
    if isinstance(tool_result, str | bytes):
        try:
            parsed = json.loads(tool_result)
        except (ValueError, TypeError):
            return None
        return parsed if isinstance(parsed, dict) else None
    content = getattr(tool_result, "content", None)
    if isinstance(content, list | tuple):
        text = "\n".join(str(getattr(c, "text", "")) for c in content if hasattr(c, "text"))
        if text.strip():
            return coerce_payload(text)
    return None


def is_envelope(payload: Mapping[str, Any] | None) -> bool:
    """True when ``payload`` carries the current authoritative-envelope version."""
    return (
        isinstance(payload, Mapping)
        and payload.get("authoritative_answer_schema_version")
        == AUTHORITATIVE_ANSWER_SCHEMA_VERSION
    )


def read_authority(tool_result: Any) -> dict[str, Any] | None:
    """Extract the ``authoritative_answer`` from an envelope tool result.

    Returns the ``{"kind", "values", "provenance"}`` dict, or ``None`` when the
    payload is not a schema-1.0 envelope or carries no authoritative answer
    (routing states, structured errors, raw-skill results, legacy servers).
    """
    payload = coerce_payload(tool_result)
    if not is_envelope(payload):
        return None
    answer = payload.get("authoritative_answer") if isinstance(payload, dict) else None
    return dict(answer) if isinstance(answer, Mapping) else None


def authority_values(tool_result: Any, *, flatten: bool = True) -> dict[str, Any] | None:
    """``read_authority`` → the ``values`` mapping (QuantityValue-flattened by default)."""
    answer = read_authority(tool_result)
    if answer is None:
        return None
    values = answer.get("values")
    if not isinstance(values, Mapping):
        return None
    out: dict[str, Any] = dict(values)
    return flatten_quantities(out) if flatten else out


def flatten_quantities(value: Any) -> Any:
    """Recursively collapse ``{"value": number, "unit": str}`` dicts to floats.

    Energy skills (``energy.load_metrics``, ``energy.balance``, …) emit
    QuantityValue-shaped fields; the envelope mirrors them verbatim into
    ``authoritative_answer.values``. Scorers need plain numbers — units are
    validated server-side before the envelope is built.
    """
    if isinstance(value, Mapping):
        if set(value) == {"value", "unit"} and isinstance(value.get("value"), int | float):
            return float(value["value"])
        return {key: flatten_quantities(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [flatten_quantities(item) for item in value]
    return value


def read_routing_state(tool_result: Any) -> str | None:
    """Return ``needs_clarification`` / ``needs_more_information`` if routed so."""
    payload = coerce_payload(tool_result)
    if payload is None:
        return None
    status = payload.get("status")
    if isinstance(status, str) and status in _ROUTING_STATES:
        return status
    return None


def read_error(tool_result: Any) -> str | None:
    """Return the message of a structured OEC error payload, if it is one."""
    payload = coerce_payload(tool_result)
    if payload is None:
        return None
    error = payload.get("error")
    if isinstance(error, str):
        return error
    if {"code", "message"} <= set(payload) and isinstance(payload.get("message"), str):
        return str(payload["message"])
    return None


def envelope_contract_issues(
    payload: Mapping[str, Any] | None,
    *,
    require_authority: bool = False,
) -> list[str]:
    """Validate the agent-tool envelope surface of a (success) payload.

    Meant for harness contract checks on ``agent.*`` tool results. Routing
    states (``needs_*``) are legitimate non-envelope passthroughs — callers
    should skip them via :func:`read_routing_state` first.
    """
    if not isinstance(payload, Mapping):
        return ["payload_not_object"]
    issues: list[str] = []
    if payload.get("authoritative_answer_schema_version") != AUTHORITATIVE_ANSWER_SCHEMA_VERSION:
        issues.append("authoritative_answer_schema_version_missing_or_mismatch")
    classification = payload.get("problem_classification")
    if not isinstance(classification, Mapping) or not classification.get("domain"):
        issues.append("problem_classification_missing_or_incomplete")
    summary = payload.get("method_summary")
    if not isinstance(summary, Mapping) or not summary.get("specialist"):
        issues.append("method_summary_missing_or_incomplete")
    if payload.get("status") != "ok":
        issues.append("status_missing_or_not_ok")
    if require_authority and not isinstance(payload.get("authoritative_answer"), Mapping):
        issues.append("authoritative_answer_missing")
    return issues


def three_verdicts(
    tool_result: Any = None,
    *,
    transport_error: BaseException | str | None = None,
    transport_exercised: bool = True,
    oec_exercised: bool = True,
    expect_authority: bool = True,
    host_claim: Mapping[str, Any] | None = None,
    claim_compare: Callable[[Mapping[str, Any], Mapping[str, Any]], bool] | None = None,
    detail: str = "",
) -> ThreeVerdicts:
    """Classify one run into the three labeled GATE-W3 verdict slots.

    Parameters
    ----------
    tool_result:
        The OEC tool result for the run (payload dict / JSON text /
        ``CallToolResult``-like), when OEC was exercised.
    transport_error:
        Set when the host/channel leg failed (CLI error, timeout, unparseable
        host output). Short-circuits: OEC and host legs are then
        ``not_reached`` / ``not_evaluated``.
    transport_exercised / oec_exercised:
        False marks legs the run never used (e.g. oracle has no host
        transport; the without-OEC control arm never runs OEC).
    expect_authority:
        False for runs where a non-authoritative outcome is legitimate
        (routing clarification, intentionally malformed stress prompts).
    host_claim / claim_compare:
        Wave-3b hook: a claim mapping plus a comparator
        ``(claim, authoritative_answer) -> bool`` (True = matches). Only when
        both are given is the host-corruption slot decided; otherwise it stays
        ``pending_wave_3b``.
    """
    details = [detail] if detail else []

    # 1. Transport leg.
    if not transport_exercised:
        transport = NOT_EXERCISED
    elif transport_error is not None:
        transport = TRANSPORT_FAILURE
        details.append(f"transport error: {str(transport_error)[:200]}")
    else:
        transport = OK
    if transport == TRANSPORT_FAILURE:
        return ThreeVerdicts(
            transport=transport,
            oec_execution=NOT_REACHED,
            host_corruption=NOT_EVALUATED,
            primary=TRANSPORT_FAILURE,
            detail="; ".join(details),
        )

    # 2. OEC execution leg.
    authority = read_authority(tool_result) if oec_exercised else None
    if not oec_exercised:
        oec_execution = NOT_EXERCISED
    elif authority is not None:
        oec_execution = OK
    else:
        error = read_error(tool_result)
        routing = read_routing_state(tool_result)
        payload = coerce_payload(tool_result)
        if error is not None:
            details.append(f"oec structured error: {error[:200]}")
        elif routing is not None:
            details.append(f"routing state without execution: {routing}")
        elif payload is None:
            details.append("no parseable tool-result payload")
        elif not is_envelope(payload):
            details.append("tool result is not a schema-1.0 envelope")
        else:
            details.append("envelope carries no authoritative_answer")
        oec_execution = OK if not expect_authority and error is None else OEC_EXECUTION_FAILURE

    # 3. Host-corruption leg (full claim/compare is Wave 3b).
    if not oec_exercised:
        host_corruption = NOT_APPLICABLE
    elif oec_execution != OK:
        host_corruption = NOT_EVALUATED
    elif host_claim is not None and claim_compare is not None and authority is not None:
        try:
            matches = bool(claim_compare(host_claim, authority))
        except Exception as exc:  # comparator bugs must not fabricate corruption
            matches = True
            details.append(f"claim_compare raised: {type(exc).__name__}: {exc}")
        host_corruption = OK if matches else HOST_CORRUPTION
        if not matches:
            details.append("host claim diverges from authoritative_answer")
    else:
        host_corruption = PENDING_WAVE_3B

    # Primary = first failure in precedence order.
    primary = OK
    for label in VERDICT_LABELS:
        if label in (transport, oec_execution, host_corruption):
            primary = label
            break

    return ThreeVerdicts(
        transport=transport,
        oec_execution=oec_execution,
        host_corruption=host_corruption,
        primary=primary,
        detail="; ".join(details),
    )


def verdict_counts(verdicts: Iterable[ThreeVerdicts]) -> dict[str, int]:
    """Labeled primary-verdict tally for report summaries (never a bare score)."""
    counts: dict[str, int] = {
        "total": 0,
        OK: 0,
        TRANSPORT_FAILURE: 0,
        OEC_EXECUTION_FAILURE: 0,
        HOST_CORRUPTION: 0,
        NOT_EXERCISED: 0,
    }
    for verdict in verdicts:
        counts["total"] += 1
        key = verdict.primary if verdict.primary in counts else OK
        counts[key] += 1
    return counts


def default_claim_compare(
    claim: Mapping[str, Any], authoritative_answer: Mapping[str, Any]
) -> bool:
    """Wave-3b default host-corruption comparator.

    Wraps ``oec.mcp.divergence.detect_divergence`` — the exact fail-closed,
    post-serialization policy the MCP server itself runs for a host-supplied
    ``claimed_answer`` (Wave 2) — so benchmarks judge host corruption by the
    same policy the product enforces, not a second ad-hoc comparator. Matches
    the ``claim_compare`` signature :func:`three_verdicts` expects: ``True``
    means the claim matches within policy.

    Only valid when ``claim`` and ``authoritative_answer["values"]`` share the
    same key schema. Some harnesses (``hermes_supertest.py``) ask the host for
    a curated answer schema (``load_sum_mwh``, ``min_tou_cost``, ...) that
    differs from the raw envelope values of the representative tool call it
    probes (e.g. an LP's ``primal``/``objective_value``). In that case, build
    a synthetic ``{"values": <curated dict in the host's schema>}`` mapping
    and pass that as ``authoritative_answer`` instead of the raw envelope
    answer — comparing across mismatched schemas would flag every field as
    ``claimed_key_not_in_authoritative`` regardless of correctness.
    """
    return detect_divergence(dict(authoritative_answer), claim) is None
