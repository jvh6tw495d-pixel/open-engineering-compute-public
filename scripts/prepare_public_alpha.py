#!/usr/bin/env python3
"""Prepare (or dry-run) a clean Public Alpha tree (handbook Fase 9 / Sprint 11).

Does **not** publish, create remotes, or force-push. By default prints a
checklist and optionally copies approved paths into a sibling directory
with a *new* git history (``git init``), matching ADR 0008.

Usage::

    uv run python scripts/prepare_public_alpha.py --dry-run
    uv run python scripts/prepare_public_alpha.py --dest ../open-engineering-compute-public
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Paths copied into the public tree (relative to incubation root).
INCLUDE: tuple[str, ...] = (
    "src",
    "skills",
    "tests",
    "docs",
    "examples",
    "integrations",
    "scripts",
    "benchmarks",
    ".github",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "Dockerfile",
    ".gitignore",
    ".pre-commit-config.yaml",
)

# Subpaths of docs/ (relative to the incubation root) that describe the
# incubation process itself -- sprint reports, the codebase-map (which
# names Grok/agent-handoff internals), and the release runbook (which
# opens with "do not publish this repository"). None of this is useful
# or safe in a public tree; excluded by directory name below rather than
# trusted to a string-content scan after the fact.
DOCS_EXCLUDE: tuple[str, ...] = (
    "docs/sprints",
    "docs/release",
    "docs/development/codebase-map.md",
)

# Never copy into a public tree (matched by basename at every directory
# level during copytree -- see ignore_patterns below).
EXCLUDE_NAMES: frozenset[str] = frozenset(
    {
        "OEC_MASTER_HANDBOOK.md",
        "OEC_PLANO_MESTRE_CLAUDE_CODE_GRAPHIFY_SPRINTS_v2.md",
        ".venv",
        "graphify-out",
        "dist",
        "coverage.xml",
        ".git",
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
    }
)


def _run(cmd: list[str], *, cwd: Path) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def checklist(repo: Path) -> list[str]:
    lines = [
        "Public Alpha checklist (Fase 9)",
        "================================",
        f"incubation root: {repo}",
        "",
        "[ ] git remote -v is empty (incubation stays private)",
        "[ ] scripts/check_forbidden_names.py passes",
        "[ ] uv run ruff check . && uv run mypy && uv run pytest",
        "[ ] uv run bandit -c pyproject.toml -r src/oec",
        "[ ] uv build succeeds",
        "[ ] LICENSE / SECURITY / CONTRIBUTING / CHANGELOG present",
        "[ ] integrations are optional (core installs without them)",
        "[ ] Open Science cannot auto-mutate stable skills",
        "[ ] MCP demo path documented (docs/mcp + integrations/odysseus)",
        "[ ] create NEW directory open-engineering-compute-public/",
        "[ ] copy only approved artifacts (this script's INCLUDE list)",
        "[ ] git init fresh history (never publish incubation history)",
        "[ ] regenerate Graphify in the public tree if desired",
        "[ ] human review before any remote is added",
    ]
    remote = subprocess.run(
        ["git", "remote", "-v"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    lines.append("")
    lines.append("current remotes:")
    lines.append(remote.stdout.strip() or "(none)")
    return lines


def copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        raise SystemExit(f"destination already exists: {dest}")
    dest.mkdir(parents=True)
    ignore = shutil.ignore_patterns(*EXCLUDE_NAMES)
    for rel in INCLUDE:
        source = src / rel
        if not source.exists():
            print(f"skip missing: {rel}")
            continue
        target = dest / rel
        if source.is_dir():
            shutil.copytree(source, target, ignore=ignore)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    for rel in DOCS_EXCLUDE:
        excluded = dest / rel
        if excluded.is_dir():
            shutil.rmtree(excluded)
            print(f"excluded incubation-only dir: {rel}")
        elif excluded.is_file():
            excluded.unlink()
            print(f"excluded incubation-only file: {rel}")

    print(f"copied INCLUDE set -> {dest}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Destination directory for a clean public tree",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print checklist only (default if --dest omitted)",
    )
    parser.add_argument(
        "--init-git",
        action="store_true",
        help="After copy, run git init and an initial commit in dest",
    )
    args = parser.parse_args(argv)
    repo = args.repo.resolve()

    for line in checklist(repo):
        print(line)

    if args.dry_run or args.dest is None:
        if args.dest is None:
            print("\n(no --dest: dry-run only)")
        return 0

    dest = args.dest.resolve()
    copy_tree(repo, dest)

    # Sanitize pass on the copy -- a hard gate, not a warning: a leak here
    # means the copied tree is not safe to init a public git history from.
    gate = subprocess.run(
        [sys.executable, str(repo / "scripts" / "check_forbidden_names.py"), "--all-files"],
        cwd=dest,
        check=False,
    )
    if gate.returncode != 0:
        shutil.rmtree(dest)
        raise SystemExit(
            "forbidden-name gate reported hits in the copied tree -- "
            f"{dest} has been deleted; fix INCLUDE/DOCS_EXCLUDE/EXCLUDE_NAMES "
            "or the forbidden-names list before retrying"
        )

    if args.init_git:
        _run(["git", "init", "-b", "main"], cwd=dest)
        _run(["git", "add", "-A"], cwd=dest)
        _run(
            [
                "git",
                "commit",
                "-m",
                "chore: initial public alpha import (clean history)",
            ],
            cwd=dest,
        )
        print("fresh git history created (no remotes)")

    print("\nDone. Review dest, run tests there, then add a remote only when ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
