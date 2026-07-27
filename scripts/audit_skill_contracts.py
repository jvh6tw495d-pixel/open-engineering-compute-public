#!/usr/bin/env python3
"""Audit skill packages under ``skills/`` for v1.5 contract completeness (C3).

Walks every directory that contains ``skill.yaml`` and checks:

* required package files (manifest, docs, schemas, implementation, validation,
  references, at least one example JSON, and at least one ``tests/*.py``)
* ``skill.yaml`` fields: ``id``, ``version``, ``method.id``, ``method.iterative``

Prints a console report, always writes
``docs/implementation/v1.5-skill-contract-audit.md``, and exits 1 when any
ERROR-level finding is present.

Usage::

    uv run python scripts/audit_skill_contracts.py
    uv run python scripts/audit_skill_contracts.py --no-write-report
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _ROOT / "skills"
_DEFAULT_REPORT = _ROOT / "docs" / "implementation" / "v1.5-skill-contract-audit.md"

REQUIRED_FILES: tuple[str, ...] = (
    "skill.yaml",
    "skill.md",
    "input.schema.json",
    "output.schema.json",
    "implementation.py",
    "validation.py",
    "references.md",
)


@dataclass
class Finding:
    """One audit finding for a skill package."""

    level: str  # ERROR | WARN
    skill_rel: str
    message: str

    def format(self) -> str:
        return f"{self.level}: {self.skill_rel}: {self.message}"


@dataclass
class SkillAudit:
    """Per-package audit result."""

    path: Path
    skill_id: str | None = None
    findings: list[Finding] = field(default_factory=list)

    @property
    def rel(self) -> str:
        return self.path.relative_to(_ROOT).as_posix()

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.level == "ERROR")

    @property
    def ok(self) -> bool:
        return self.error_count == 0


def find_skill_dirs(root: Path) -> list[Path]:
    """Return skill package directories (those containing ``skill.yaml``), sorted."""
    if not root.is_dir():
        return []
    return sorted(p.parent for p in root.rglob("skill.yaml"))


def _has_examples(skill_dir: Path) -> bool:
    examples_dir = skill_dir / "examples"
    if not examples_dir.is_dir():
        return False
    return any(examples_dir.glob("*.json"))


def _has_tests(skill_dir: Path) -> bool:
    """Accept ``tests/test_golden.py`` or any ``tests/*.py`` / ``tests/test_*.py``."""
    tests_dir = skill_dir / "tests"
    if not tests_dir.is_dir():
        return False
    if (tests_dir / "test_golden.py").is_file():
        return True
    return any(tests_dir.glob("*.py"))


def audit_one(skill_dir: Path) -> SkillAudit:
    """Audit a single skill package directory."""
    result = SkillAudit(path=skill_dir)
    rel = result.rel

    for name in REQUIRED_FILES:
        if not (skill_dir / name).is_file():
            result.findings.append(
                Finding(level="ERROR", skill_rel=rel, message=f"missing required file {name}")
            )

    if not _has_examples(skill_dir):
        result.findings.append(
            Finding(
                level="ERROR",
                skill_rel=rel,
                message="missing examples/*.json (at least one required)",
            )
        )

    if not _has_tests(skill_dir):
        result.findings.append(
            Finding(
                level="ERROR",
                skill_rel=rel,
                message="missing tests/test_golden.py (or any tests/*.py)",
            )
        )

    yaml_path = skill_dir / "skill.yaml"
    if not yaml_path.is_file():
        return result

    try:
        data: Any = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — surface parse failures as ERROR
        result.findings.append(
            Finding(level="ERROR", skill_rel=rel, message=f"skill.yaml parse error: {exc}")
        )
        return result

    if not isinstance(data, dict):
        result.findings.append(
            Finding(level="ERROR", skill_rel=rel, message="skill.yaml is not a mapping")
        )
        return result

    skill_id = data.get("id")
    if isinstance(skill_id, str) and skill_id:
        result.skill_id = skill_id
    else:
        result.findings.append(
            Finding(level="ERROR", skill_rel=rel, message="skill.yaml missing id")
        )

    if "version" not in data or data.get("version") in (None, ""):
        result.findings.append(
            Finding(level="ERROR", skill_rel=rel, message="skill.yaml missing version")
        )

    method = data.get("method")
    if not isinstance(method, dict):
        result.findings.append(
            Finding(level="ERROR", skill_rel=rel, message="skill.yaml missing method mapping")
        )
    else:
        if "id" not in method or method.get("id") in (None, ""):
            result.findings.append(
                Finding(level="ERROR", skill_rel=rel, message="method.id missing")
            )
        if "iterative" not in method:
            result.findings.append(
                Finding(level="ERROR", skill_rel=rel, message="method.iterative missing")
            )
        elif not isinstance(method.get("iterative"), bool):
            result.findings.append(
                Finding(
                    level="ERROR",
                    skill_rel=rel,
                    message="method.iterative must be a boolean",
                )
            )

    return result


def render_report(audits: list[SkillAudit]) -> str:
    """Build the markdown audit report body."""
    errors = [f for a in audits for f in a.findings if f.level == "ERROR"]
    warns = [f for a in audits for f in a.findings if f.level == "WARN"]
    clean = [a for a in audits if a.ok]
    dirty = [a for a in audits if not a.ok]

    lines: list[str] = [
        "# v1.5 skill contract audit",
        "",
        "Generated by `scripts/audit_skill_contracts.py` (V3 closeout C3).",
        "",
        f"**Skills scanned:** {len(audits)}",
        f"**Clean packages:** {len(clean)}",
        f"**Packages with ERROR:** {len(dirty)}",
        f"**ERROR lines:** {len(errors)}",
        f"**WARN lines:** {len(warns)}",
        "",
        "## Required files",
        "",
        ", ".join(f"`{f}`" for f in REQUIRED_FILES),
        "",
        "Plus:",
        "",
        "- at least one `examples/*.json`",
        "- `tests/test_golden.py` **or** any `tests/*.py`",
        "",
        "## Manifest fields",
        "",
        "`id`, `version`, `method.id`, `method.iterative` (boolean)",
        "",
    ]

    if errors:
        lines += ["## Errors", ""]
        for e in errors:
            lines.append(f"- `{e.skill_rel}`: {e.message}")
        lines.append("")
    else:
        lines += [
            "## Status",
            "",
            "All skill packages satisfy the v1.5 contract checklist.",
            "",
        ]

    if warns:
        lines += ["## Warnings", ""]
        for w in warns:
            lines.append(f"- `{w.skill_rel}`: {w.message}")
        lines.append("")

    lines += ["## Clean skill IDs", ""]
    if clean:
        for a in sorted(clean, key=lambda x: x.skill_id or x.rel):
            sid = a.skill_id or a.rel
            lines.append(f"- `{sid}`")
    else:
        lines.append("_none_")
    lines.append("")

    if dirty:
        lines += ["## Packages with errors", ""]
        for a in dirty:
            sid = a.skill_id or a.rel
            lines.append(f"- `{sid}` (`{a.rel}`) — {a.error_count} ERROR(s)")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit skills/ packages for v1.5 contract completeness."
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=_DEFAULT_REPORT,
        help="Markdown report path (default: docs/implementation/v1.5-skill-contract-audit.md)",
    )
    parser.add_argument(
        "--no-write-report",
        action="store_true",
        help="Print only; do not write the markdown report",
    )
    parser.add_argument(
        "--skills-root",
        type=Path,
        default=_SKILLS,
        help="Skills tree root (default: <repo>/skills)",
    )
    args = parser.parse_args(argv)

    skills_root = args.skills_root if args.skills_root.is_absolute() else _ROOT / args.skills_root
    skill_dirs = find_skill_dirs(skills_root)
    audits = [audit_one(d) for d in skill_dirs]

    errors = [f for a in audits for f in a.findings if f.level == "ERROR"]
    warns = [f for a in audits for f in a.findings if f.level == "WARN"]
    clean = sum(1 for a in audits if a.ok)

    print("OEC skill contract audit (v1.5)")
    print("=" * 40)
    print(f"skills root : {skills_root}")
    print(f"scanned     : {len(audits)}")
    print(f"clean       : {clean}")
    print(f"ERROR lines : {len(errors)}")
    print(f"WARN lines  : {len(warns)}")
    print()

    for finding in errors + warns:
        print(finding.format())

    if not errors and not warns and audits:
        print("OK: all skill packages satisfy the v1.5 contract checklist.")
    elif not audits:
        print("ERROR: no skill.yaml packages found under skills root.")
        errors.append(
            Finding(level="ERROR", skill_rel="skills", message="no skill.yaml packages found")
        )

    if not args.no_write_report:
        report_path: Path = args.report
        if not report_path.is_absolute():
            report_path = _ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_report(audits), encoding="utf-8")
        print()
        print(f"Wrote {report_path}")

    # Exit 1 on any ERROR-level finding (missing required files / fields).
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
