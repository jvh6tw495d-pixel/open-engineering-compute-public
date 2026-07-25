#!/usr/bin/env python3
"""Sanitization gate: refuse private / forbidden nomenclature (ADR 0008 / Fase 9).

Scans tracked text sources (and optionally the whole working tree) for terms
that must never appear in a public OEC tree. Exit code 1 on any match.

Usage::

    uv run python scripts/check_forbidden_names.py
    uv run python scripts/check_forbidden_names.py --all-files
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Handbook §2.1 — keep in sync with docs/release/public-alpha.md
FORBIDDEN: tuple[str, ...] = (
    "AELE",
    "AELE OS",
    "AOS",
    "Apollo",
    "Horizon",
    "Orion",
    "Argos",
    "Hermes",
    "AELE Score",
    "DELE",
)

# Word-boundary-ish match; multi-word terms matched as literal substrings.
_PATTERNS = [
    re.compile(rf"(?i)(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])")
    if " " not in term
    else re.compile(re.escape(term), re.IGNORECASE)
    for term in FORBIDDEN
]

_SKIP_DIR_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "graphify-out",
    ".pytest_cache",
}

_TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
    ".rst",
    ".ini",
    ".cfg",
    ".sh",
    ".ps1",
    ".csv",
}


def _iter_git_files(repo: Path) -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return [repo / p for p in proc.stdout.decode().split("\0") if p]


def _iter_all_files(repo: Path) -> list[Path]:
    out: list[Path] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIR_PARTS for part in path.parts):
            continue
        if path.suffix.lower() in _TEXT_SUFFIXES or path.name in {
            "LICENSE",
            "Dockerfile",
            "Makefile",
        }:
            out.append(path)
    return out


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for term, pattern in zip(FORBIDDEN, _PATTERNS, strict=True):
            if pattern.search(line):
                hits.append((lineno, term, line.strip()[:200]))
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Scan the working tree (not only git-tracked files)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: cwd)",
    )
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    files = _iter_all_files(repo) if args.all_files else _iter_git_files(repo)

    failures = 0

    # The master handbook must never be *present* in this tree at all
    # (ADR 0008) -- checked by existence, not content, since its mere
    # presence is the violation regardless of what it says.
    for handbook_name in (
        "OEC_MASTER_HANDBOOK.md",
        "OEC_PLANO_MESTRE_CLAUDE_CODE_GRAPHIFY_SPRINTS_v2.md",
    ):
        handbook_path = repo / handbook_name
        if handbook_path.exists():
            print(f"{handbook_name}: the master handbook must never be copied into this repo")
            failures += 1

    for path in files:
        rel = path.relative_to(repo) if path.is_relative_to(repo) else path
        # The scanner's own source is the only legitimate exemption: it
        # must hold the FORBIDDEN tuple as literal strings to scan for
        # them. Every other file -- including this project's own ADRs
        # and release docs -- is expected to actually be clean, not
        # exempted by filename.
        if path.name == "check_forbidden_names.py":
            continue
        for lineno, term, snippet in scan_file(path):
            print(f"{rel}:{lineno}: forbidden term {term!r}: {snippet}")
            failures += 1

    if failures:
        print(f"\n{failures} forbidden-name hit(s)", file=sys.stderr)
        return 1
    print(f"ok: scanned {len(files)} files, zero forbidden terms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
