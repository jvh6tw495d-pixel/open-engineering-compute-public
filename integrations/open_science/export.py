"""Export a Method Change Proposal from a target skill + author intent.

Optional integration — not imported by ``oec`` core (handbook §15.2).

Usage::

    python integrations/open_science/export.py \\
        --skill-id mathematics.solve_root \\
        --skills-root skills \\
        --title "Prefer brentq default when bracket given" \\
        --out proposals/mcp-001.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Allow running as a script without installing the integration package.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from import_proposal import validate_proposal  # noqa: E402


def build_proposal(
    *,
    proposal_id: str,
    skill_id: str,
    skill_version: str,
    title: str,
    summary: str,
    rationale: str,
    change_kind: str,
    change_description: str,
    evidence: list[dict[str, Any]],
    author: str,
    status: str = "draft",
    affects_public_contract: bool = False,
    benchmark_plan: str | None = None,
) -> dict[str, Any]:
    """Build a schema-valid proposal document (does not write skills)."""
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    proposal: dict[str, Any] = {
        "proposal_id": proposal_id,
        "schema_version": "1.0.0",
        "status": status,
        "target_skill_id": skill_id,
        "target_skill_version": skill_version,
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "proposed_changes": {
            "kind": change_kind,
            "description": change_description,
            "affects_public_contract": affects_public_contract,
        },
        "evidence": evidence,
        "author": author,
        "created_at": now,
        "updated_at": now,
    }
    if benchmark_plan:
        proposal["benchmark_plan"] = benchmark_plan
    validate_proposal(proposal)
    return proposal


def export_from_skill(
    *,
    skills_root: Path,
    skill_id: str,
    proposal_id: str,
    title: str,
    summary: str,
    rationale: str,
    change_kind: str,
    change_description: str,
    author: str,
    evidence_citation: str,
) -> dict[str, Any]:
    """Resolve the skill via OEC registry and stamp version into a proposal."""
    from oec.skills.registry.registry import SkillRegistry

    registry = SkillRegistry()
    report = registry.register_all(skills_root)
    if report.failures:
        msg = f"skill registration failures: {report.failures}"
        raise RuntimeError(msg)
    skill = registry.get_skill(skill_id)
    return build_proposal(
        proposal_id=proposal_id,
        skill_id=skill.manifest.id,
        skill_version=skill.manifest.version,
        title=title,
        summary=summary,
        rationale=rationale,
        change_kind=change_kind,
        change_description=change_description,
        evidence=[{"type": "review_note", "citation": evidence_citation}],
        author=author,
        affects_public_contract=skill.manifest.status.value == "stable",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export an Open Science Method Change Proposal")
    parser.add_argument("--skill-id", required=True)
    parser.add_argument("--skills-root", type=Path, default=Path("skills"))
    parser.add_argument("--proposal-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument(
        "--change-kind",
        default="methodology",
        choices=[
            "methodology",
            "formulation",
            "validation",
            "references",
            "assumptions",
            "limits",
            "implementation",
            "other",
        ],
    )
    parser.add_argument("--change-description", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--evidence", default="Author-supplied critique pending references.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    proposal = export_from_skill(
        skills_root=args.skills_root,
        skill_id=args.skill_id,
        proposal_id=args.proposal_id,
        title=args.title,
        summary=args.summary,
        rationale=args.rationale,
        change_kind=args.change_kind,
        change_description=args.change_description,
        author=args.author,
        evidence_citation=args.evidence,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
