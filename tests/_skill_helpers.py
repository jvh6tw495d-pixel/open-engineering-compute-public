"""Test-only helper for writing minimal, overridable skill directories on disk.

Used by loader, registry, CLI, and property-based tests to construct valid
and deliberately-broken skill directories without hand-writing YAML/JSON
in every test. Lives directly under ``tests/`` (rather than ``tests/unit``)
so it is importable from every test subpackage — see ``tests/conftest.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

DEFAULT_MANIFEST: dict[str, Any] = {
    "id": "mathematics.identity",
    "version": "0.1.0",
    "status": "experimental",
    "domain": "mathematics",
    "title": "Identity",
    "entrypoint": {"module": "implementation", "function": "execute"},
    "schemas": {"input": "input.schema.json", "output": "output.schema.json"},
    "method": {"id": "identity", "version": "1"},
}

DEFAULT_FRONT_MATTER: dict[str, Any] = {
    "id": "mathematics.identity",
    "version": "0.1.0",
    "status": "experimental",
    "domain": "mathematics",
    "title": "Identity",
}


def write_skill_dir(
    base: Path,
    *,
    name: str = "skill",
    manifest_overrides: dict[str, Any] | None = None,
    front_matter_overrides: dict[str, Any] | None = None,
    manifest_raw: str | None = None,
    front_matter_raw: str | None = None,
    skip_manifest: bool = False,
    skip_front_matter: bool = False,
    skip_entrypoint: bool = False,
    skip_input_schema: bool = False,
    skip_output_schema: bool = False,
    input_schema_raw: str | None = None,
) -> Path:
    """Write a minimal skill directory under ``base / name`` and return its path.

    Starts from a valid ``mathematics.identity`` skill and applies the
    given overrides/omissions, so each test only has to spell out what
    makes it different from a valid skill.
    """
    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    if manifest_raw is not None:
        (skill_dir / "skill.yaml").write_text(manifest_raw, encoding="utf-8")
    elif not skip_manifest:
        manifest = {**DEFAULT_MANIFEST, **(manifest_overrides or {})}
        (skill_dir / "skill.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")

    if front_matter_raw is not None:
        (skill_dir / "skill.md").write_text(front_matter_raw, encoding="utf-8")
    elif not skip_front_matter:
        front_matter = {**DEFAULT_FRONT_MATTER, **(front_matter_overrides or {})}
        front_matter_yaml = yaml.safe_dump(front_matter)
        (skill_dir / "skill.md").write_text(
            f"---\n{front_matter_yaml}---\n\n# Purpose\n\nFixture skill.\n",
            encoding="utf-8",
        )

    if not skip_entrypoint:
        (skill_dir / "implementation.py").write_text(
            "def execute(inputs):\n    return inputs\n", encoding="utf-8"
        )

    if input_schema_raw is not None:
        (skill_dir / "input.schema.json").write_text(input_schema_raw, encoding="utf-8")
    elif not skip_input_schema:
        (skill_dir / "input.schema.json").write_text(
            json.dumps({"type": "object"}), encoding="utf-8"
        )

    if not skip_output_schema:
        (skill_dir / "output.schema.json").write_text(
            json.dumps({"type": "object"}), encoding="utf-8"
        )

    return skill_dir
