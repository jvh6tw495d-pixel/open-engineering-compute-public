"""Host-claim divergence detection for MCP agent-tool responses (v2.5.3 Wave 2).

Pure functions over plain dicts/JSON-shaped values — no Engine, no
``ExecutionResult`` imports. A host may voluntarily attach ``claimed_answer``
to an agent-tool call; this module compares that claim against the
``authoritative_answer`` OEC just minted and reports a structured
``host_output_diverged`` warning when they disagree. The comparison never
mutates or overrides ``authoritative_answer`` — it is fail-closed advisory
only, wired at the ``call_tool`` boundary (see ``server.py``).

All comparisons run on values as they'll actually round-trip through
``json.dumps(..., default=str)`` — the same canonicalization the MCP
transport uses — never on pre-serialization Python objects. This avoids
spurious divergence from types that only differ before serialization (e.g.
``tuple`` vs ``list``) and keeps NaN/Infinity handling explicit rather than
accidental.
"""

from __future__ import annotations

import json
import math
from typing import Any

DIVERGENCE_POLICY_VERSION = "1.0"

# Versioned tolerances: bump the policy version above if these ever change,
# since a looser/tighter tolerance is a contract change for hosts relying on
# ``host_output_diverged`` staying silent (or firing) at the margin.
DEFAULT_ABS_TOLERANCE = 1e-9
DEFAULT_REL_TOLERANCE = 1e-6

_MISSING = object()


def canonical_json(value: Any) -> str:
    """Serialize ``value`` the same way the MCP transport does, canonically.

    ``sort_keys`` + fixed separators give a single deterministic string for
    structural-equality checks; ``default=str`` mirrors ``server._json_text``
    so a claim is judged against what actually crosses the wire.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _round_trip(value: Any) -> Any:
    """Normalize ``value`` through canonical JSON encode/decode.

    Collapses pre-serialization-only distinctions (tuple vs list, custom
    ``__str__`` objects, etc.) so comparison always happens post-serialization,
    per the anti-spurious contract. NaN/Infinity survive Python's
    ``json.dumps`` (non-standard but accepted with default settings) and are
    handled explicitly by the caller — never silently coerced here.
    """
    return json.loads(canonical_json(value))


def _is_nan_or_inf(value: Any) -> bool:
    return isinstance(value, float) and (math.isnan(value) or math.isinf(value))


def numbers_equal(
    a: float | int,
    b: float | int,
    *,
    abs_tol: float = DEFAULT_ABS_TOLERANCE,
    rel_tol: float = DEFAULT_REL_TOLERANCE,
) -> bool | None:
    """Compare two JSON numbers with versioned abs/rel tolerance.

    Returns ``None`` (not a bool) when either operand is NaN/Infinity: those
    values never round-trip losslessly and are fail-closed — the caller must
    treat ``None`` as "cannot verify, flag it," never as "equal."
    """
    if _is_nan_or_inf(a) or _is_nan_or_inf(b):
        return None
    fa, fb = float(a), float(b)
    if fa == fb:
        return True
    return math.isclose(fa, fb, rel_tol=rel_tol, abs_tol=abs_tol)


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def structural_equal(a: Any, b: Any) -> bool:
    """Hash-style structural equality via canonical JSON (``sort_keys`` + fixed
    separators) — key insertion order and tuple-vs-list never cause a false
    mismatch. Strict (no numeric tolerance); a passing fast path ahead of the
    tolerant :func:`compare_values` diff, not a replacement for it.
    """
    return canonical_json(a) == canonical_json(b)


def compare_values(
    authoritative: Any,
    claimed: Any,
    *,
    path: str = "$",
    abs_tol: float = DEFAULT_ABS_TOLERANCE,
    rel_tol: float = DEFAULT_REL_TOLERANCE,
) -> list[dict[str, Any]]:
    """Recursively diff ``claimed`` against ``authoritative``, subset-first.

    Policy (documented in ``docs/contracts/authoritative-answer.md``):

    - dict: only keys *present in the claim* are checked (subset claims are
      not divergence — a host may claim a partial answer). A claim key
      absent from the authoritative side is flagged (fabricated field).
    - explicit ``null`` in the claim is compared against the authoritative
      value like any other value — it is *not* treated as "key absent."
      Distinguishing "key omitted" (no check) from "key explicitly null"
      (checked, mismatches if the authority is non-null) is the point.
    - list: length must match, then element-wise recursion.
    - number: abs/rel tolerance; NaN/Infinity anywhere fail-closed (flagged).
    - bool: exact type + value match (never coerced to/from a number).
    - everything else: structural equality post round-trip.
    """
    authoritative = _round_trip(authoritative) if authoritative is not _MISSING else _MISSING
    claimed = _round_trip(claimed)
    return _compare(authoritative, claimed, path=path, abs_tol=abs_tol, rel_tol=rel_tol)


def _mismatch(
    path: str, reason: str, *, authoritative: Any = _MISSING, claimed: Any = _MISSING
) -> dict[str, Any]:
    record: dict[str, Any] = {"path": path, "reason": reason}
    if authoritative is not _MISSING:
        record["authoritative"] = authoritative
    if claimed is not _MISSING:
        record["claimed"] = claimed
    return record


def _compare(
    authoritative: Any,
    claimed: Any,
    *,
    path: str,
    abs_tol: float,
    rel_tol: float,
) -> list[dict[str, Any]]:
    if authoritative is _MISSING:
        return [_mismatch(path, "claimed_key_not_in_authoritative", claimed=claimed)]

    if isinstance(claimed, dict):
        if not isinstance(authoritative, dict):
            return [_mismatch(path, "type_mismatch", authoritative=authoritative, claimed=claimed)]
        mismatches: list[dict[str, Any]] = []
        for key, claimed_value in claimed.items():
            child_path = f"{path}.{key}"
            authoritative_value = authoritative.get(key, _MISSING)
            mismatches.extend(
                _compare(
                    authoritative_value,
                    claimed_value,
                    path=child_path,
                    abs_tol=abs_tol,
                    rel_tol=rel_tol,
                )
            )
        return mismatches

    if isinstance(claimed, list):
        if not isinstance(authoritative, list):
            return [_mismatch(path, "type_mismatch", authoritative=authoritative, claimed=claimed)]
        if len(claimed) != len(authoritative):
            return [
                _mismatch(
                    path,
                    "list_length_mismatch",
                    authoritative=len(authoritative),
                    claimed=len(claimed),
                )
            ]
        mismatches = []
        for index, (a_item, c_item) in enumerate(zip(authoritative, claimed, strict=False)):
            mismatches.extend(
                _compare(
                    a_item,
                    c_item,
                    path=f"{path}[{index}]",
                    abs_tol=abs_tol,
                    rel_tol=rel_tol,
                )
            )
        return mismatches

    if isinstance(claimed, bool) or isinstance(authoritative, bool):
        if claimed is authoritative:
            return []
        return [_mismatch(path, "value_mismatch", authoritative=authoritative, claimed=claimed)]

    if _is_number(claimed) and _is_number(authoritative):
        equal = numbers_equal(authoritative, claimed, abs_tol=abs_tol, rel_tol=rel_tol)
        if equal is None:
            return [
                _mismatch(
                    path, "nan_or_inf_unverifiable", authoritative=authoritative, claimed=claimed
                )
            ]
        if equal:
            return []
        return [_mismatch(path, "value_mismatch", authoritative=authoritative, claimed=claimed)]

    if claimed is None or authoritative is None:
        if claimed is authoritative:
            return []
        return [_mismatch(path, "null_vs_value", authoritative=authoritative, claimed=claimed)]

    if claimed == authoritative:
        return []
    return [_mismatch(path, "value_mismatch", authoritative=authoritative, claimed=claimed)]


def detect_divergence(
    authoritative_answer: dict[str, Any] | None,
    claimed_answer: Any,
    *,
    abs_tol: float = DEFAULT_ABS_TOLERANCE,
    rel_tol: float = DEFAULT_REL_TOLERANCE,
) -> dict[str, Any] | None:
    """Compare a host's voluntary ``claimed_answer`` against OEC's authority.

    Returns ``None`` when there is nothing to flag (no claim, or claim
    matches within policy). Returns a structured ``host_output_diverged``
    body otherwise — never raises, never mutates ``authoritative_answer``.
    Callers must treat the return value as advisory: ``authoritative_answer``
    remains the numerical truth regardless of this result (fail-closed means
    "flag it," not "trust the claim" nor "trust the authority blindly" —
    OEC's own value simply never gets overwritten by a host claim, ever).
    """
    if claimed_answer is None:
        return None

    if authoritative_answer is None:
        return {
            "policy_version": DIVERGENCE_POLICY_VERSION,
            "reason": "no_authoritative_answer",
            "mismatches": [
                _mismatch("$", "authoritative_answer_absent", claimed=_round_trip(claimed_answer))
            ],
        }

    authoritative_values = authoritative_answer.get("values", {})
    mismatches = compare_values(
        authoritative_values, claimed_answer, abs_tol=abs_tol, rel_tol=rel_tol
    )
    if not mismatches:
        return None
    return {
        "policy_version": DIVERGENCE_POLICY_VERSION,
        "reason": "value_mismatch",
        "mismatches": mismatches,
    }
