"""Import / validate Method Change Proposals (Open Science, handbook §15.2).

Hard rule: Open Science **never** mutates a ``stable`` skill automatically.
Applying an approved proposal to a stable target requires an explicit
``human_approved=True`` flag *and* still only records a review decision —
it does not rewrite skill packages. Landing code is always a separate,
human-driven experimental version.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema

_HERE = Path(__file__).resolve().parent
_SCHEMA_PATH = _HERE / "proposal.schema.json"

# Terminal statuses that still must not touch stable skill trees.
_APPLY_BLOCKED_WITHOUT_HUMAN = frozenset(
    {"approved", "experimental_landed", "submitted", "under_review", "draft"}
)


class OpenScienceError(Exception):
    """Raised when a proposal is invalid or violates the stable-skill rule."""


def load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_proposal(proposal: dict[str, Any]) -> None:
    """Validate ``proposal`` against ``proposal.schema.json``."""
    schema = load_schema()
    try:
        jsonschema.validate(instance=proposal, schema=schema)
    except jsonschema.ValidationError as exc:
        raise OpenScienceError(f"proposal schema invalid: {exc.message}") from exc


def load_proposal(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise OpenScienceError("proposal root must be a JSON object")
    validate_proposal(data)
    return data


def resolve_target_status(skills_root: Path, skill_id: str, version: str | None = None) -> str:
    """Return the lifecycle status string of the target skill."""
    from oec.skills.registry.registry import SkillRegistry

    registry = SkillRegistry()
    report = registry.register_all(skills_root)
    if report.failures:
        raise OpenScienceError(f"skill registration failures: {report.failures}")
    skill = registry.get_skill(skill_id, version) if version else registry.get_skill(skill_id)
    return skill.manifest.status.value


def assert_may_not_auto_mutate_stable(
    proposal: dict[str, Any],
    *,
    skills_root: Path,
    human_approved: bool = False,
    apply_to_tree: bool = False,
) -> None:
    """Enforce handbook rule: never auto-alter a stable skill.

    - Reading / validating a proposal is always allowed.
    - ``apply_to_tree=True`` (would write skill files) is refused for
      ``stable`` targets unless ``human_approved`` — and even then this
      module still refuses to write; it only signals that a human may
      open an experimental version workflow.
    """
    validate_proposal(proposal)
    status = resolve_target_status(
        skills_root,
        proposal["target_skill_id"],
        proposal.get("target_skill_version"),
    )
    if status != "stable":
        return
    if apply_to_tree and not human_approved:
        raise OpenScienceError(
            "refusing to apply proposal to a stable skill without explicit "
            "human_approved=True (Open Science never auto-mutates stable skills)"
        )
    if apply_to_tree and human_approved:
        # Still do not write — stable code changes are out of band.
        raise OpenScienceError(
            "human approval recorded, but this integration never writes "
            "stable skill packages; open an experimental skill version "
            "manually after review (status may become experimental_landed)"
        )


def import_proposal(
    path: Path,
    *,
    skills_root: Path,
    human_approved: bool = False,
    apply_to_tree: bool = False,
) -> dict[str, Any]:
    """Load, validate, and (optionally) check apply permissions.

    Returns a report dict; never mutates skill files.
    """
    proposal = load_proposal(path)
    target_status = resolve_target_status(
        skills_root,
        proposal["target_skill_id"],
        proposal.get("target_skill_version"),
    )
    report: dict[str, Any] = {
        "proposal_id": proposal["proposal_id"],
        "target_skill_id": proposal["target_skill_id"],
        "target_skill_version": proposal["target_skill_version"],
        "proposal_status": proposal["status"],
        "target_lifecycle_status": target_status,
        "schema_valid": True,
        "would_mutate_stable": target_status == "stable" and apply_to_tree,
        "human_approved": human_approved,
        "action": "validated_only",
    }

    if apply_to_tree:
        assert_may_not_auto_mutate_stable(
            proposal,
            skills_root=skills_root,
            human_approved=human_approved,
            apply_to_tree=True,
        )
        # Unreachable for stable; for non-stable we still do not write trees
        # in this Alpha — application is a manual experimental landing.
        report["action"] = "apply_refused_use_experimental_workflow"
        raise OpenScienceError(
            "Alpha Open Science import validates and reviews only; "
            "it does not write skill packages. Land experimental versions by hand."
        )

    if target_status == "stable" and proposal["status"] in _APPLY_BLOCKED_WITHOUT_HUMAN:
        report["stable_guard"] = (
            "target is stable — any landing requires human review and a new "
            "experimental version; stable files will not be modified by this tool"
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import/validate an Open Science proposal")
    parser.add_argument("proposal", type=Path)
    parser.add_argument("--skills-root", type=Path, default=Path("skills"))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Attempt apply (Alpha: always refused; proves stable guard)",
    )
    parser.add_argument(
        "--human-approved",
        action="store_true",
        help="Record that a human approved review (still does not write stable)",
    )
    args = parser.parse_args(argv)
    try:
        report = import_proposal(
            args.proposal,
            skills_root=args.skills_root,
            human_approved=args.human_approved,
            apply_to_tree=args.apply,
        )
    except OpenScienceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
