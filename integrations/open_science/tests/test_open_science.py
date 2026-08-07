"""Tests for Open Science Method Change Proposal tools (Fase 8)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from export import build_proposal, export_from_skill  # noqa: E402
from import_proposal import (  # noqa: E402
    OpenScienceError,
    import_proposal,
    load_proposal,
    validate_proposal,
)
from workflow import transition, workflow_diagram  # noqa: E402

_EXAMPLES = _ROOT / "examples"
_SKILLS = Path("skills")


def test_sample_proposal_validates() -> None:
    proposal = load_proposal(_EXAMPLES / "sample_proposal.json")
    assert proposal["proposal_id"] == "mcp-2026-001"
    validate_proposal(proposal)


def test_build_proposal_round_trip_schema() -> None:
    proposal = build_proposal(
        proposal_id="mcp-test-1",
        skill_id="mathematics.solve_root",
        skill_version="0.1.0",
        title="Test proposal title here",
        summary="Short summary of the proposed methodological change.",
        rationale="Longer rationale explaining why the change improves auditability.",
        change_kind="references",
        change_description="Add an additional textbook reference for the algorithm.",
        evidence=[{"type": "reference", "citation": "Example textbook, ch. 1"}],
        author="tester",
    )
    validate_proposal(proposal)


def test_export_from_real_skill() -> None:
    proposal = export_from_skill(
        skills_root=_SKILLS,
        skill_id="mathematics.solve_root",
        proposal_id="mcp-export-1",
        title="Export path stamps skill version",
        summary="Ensures export reads the live registry version field.",
        rationale="Integration test for the export_from_skill helper path.",
        change_kind="validation",
        change_description="No production change; export smoke only.",
        author="tester",
        evidence_citation="automated test",
    )
    assert proposal["target_skill_id"] == "mathematics.solve_root"
    assert proposal["target_skill_version"] == "0.1.0"


def test_import_validates_without_writing() -> None:
    report = import_proposal(
        _EXAMPLES / "sample_proposal.json",
        skills_root=_SKILLS,
        apply_to_tree=False,
    )
    assert report["schema_valid"] is True
    assert report["action"] == "validated_only"
    assert report["target_lifecycle_status"] == "experimental"


def test_apply_always_refused_in_alpha() -> None:
    with pytest.raises(OpenScienceError, match="does not write skill packages"):
        import_proposal(
            _EXAMPLES / "sample_proposal.json",
            skills_root=_SKILLS,
            apply_to_tree=True,
            human_approved=True,
        )


def test_workflow_transitions() -> None:
    proposal = load_proposal(_EXAMPLES / "sample_proposal.json")
    submitted = transition(proposal, "submitted")
    assert submitted["status"] == "submitted"
    under = transition(submitted, "under_review")
    approved = transition(under, "approved", reviewer="joao", notes="LGTM docs-only")
    assert approved["human_review"]["decision"] == "approve"
    landed = transition(
        approved,
        "experimental_landed",
        experimental_skill_version="0.1.1-exp.1",
    )
    assert landed["experimental_skill_version"] == "0.1.1-exp.1"


def test_illegal_workflow_transition() -> None:
    proposal = load_proposal(_EXAMPLES / "sample_proposal.json")
    with pytest.raises(OpenScienceError, match="illegal proposal transition"):
        transition(proposal, "approved")


def test_workflow_diagram_mentions_stable_guard() -> None:
    text = workflow_diagram()
    assert "stable" in text.lower()


def test_invalid_proposal_rejected() -> None:
    bad = json.loads((_EXAMPLES / "sample_proposal.json").read_text(encoding="utf-8"))
    del bad["rationale"]
    with pytest.raises(OpenScienceError):
        validate_proposal(bad)
