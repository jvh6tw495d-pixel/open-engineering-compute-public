"""Human review workflow helpers for Method Change Proposals.

Flow (handbook §15.2)::

    Evidence or critique
            ↓
    Method Change Proposal
            ↓
    Experimental implementation   ← human only
            ↓
    Benchmark and golden tests
            ↓
    Human review
            ↓
    New skill version (never silent stable mutation)
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from import_proposal import OpenScienceError, validate_proposal

_FORWARD: dict[str, frozenset[str]] = {
    "draft": frozenset({"submitted", "closed"}),
    "submitted": frozenset({"under_review", "rejected", "closed"}),
    "under_review": frozenset({"approved", "rejected", "submitted"}),
    "approved": frozenset({"experimental_landed", "closed"}),
    "rejected": frozenset({"closed", "draft"}),
    "experimental_landed": frozenset({"closed"}),
    "closed": frozenset(),
}


def transition(
    proposal: dict[str, Any],
    new_status: str,
    *,
    reviewer: str | None = None,
    decision: str | None = None,
    notes: str | None = None,
    experimental_skill_version: str | None = None,
) -> dict[str, Any]:
    """Return a copy of ``proposal`` moved to ``new_status`` if legal."""
    validate_proposal(proposal)
    current = proposal["status"]
    allowed = _FORWARD.get(current, frozenset())
    if new_status not in allowed:
        raise OpenScienceError(
            f"illegal proposal transition: {current!r} -> {new_status!r} "
            f"(allowed: {sorted(allowed)})"
        )

    out = deepcopy(proposal)
    out["status"] = new_status
    out["updated_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()

    if new_status in {"approved", "rejected"} or decision is not None:
        review: dict[str, Any] = dict(out.get("human_review") or {})
        if reviewer:
            review["reviewer"] = reviewer
        if decision:
            review["decision"] = decision
        elif new_status == "approved":
            review["decision"] = "approve"
        elif new_status == "rejected":
            review["decision"] = "reject"
        if notes:
            review["notes"] = notes
        review["reviewed_at"] = out["updated_at"]
        out["human_review"] = review

    if new_status == "experimental_landed":
        if not experimental_skill_version:
            raise OpenScienceError(
                "experimental_landed requires experimental_skill_version "
                "(a non-stable skill version produced by hand)"
            )
        out["experimental_skill_version"] = experimental_skill_version

    validate_proposal(out)
    return out


def workflow_diagram() -> str:
    return (
        "Evidence → Method Change Proposal → Experimental implementation → "
        "Benchmark/golden tests → Human review → New skill version\n"
        "(stable skills are never modified by this pipeline automatically)"
    )
