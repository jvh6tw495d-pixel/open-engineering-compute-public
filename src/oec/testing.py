"""Testing utilities for skill authors and OEC's own test suite (plan section 8).

Not part of the runtime execution path — see ``oec.execution.runner``
for how a skill's ``implementation.py`` is loaded when actually
executed (in a sandboxed subprocess). This module is a small, public
testing SDK: it's what lets a skill's own
``tests/test_golden.py``/``test_properties.py``/``test_validation.py``
import their sibling ``implementation.py``/``validation.py`` directly
(``load_skill_module``, without ``sys.path`` tricks or collisions
between skills that both happen to have an ``implementation.py``), and
what lets any test — a skill author's or OEC's own — construct a
throwaway skill directory on disk without hand-writing YAML/JSON
(``write_skill_dir``).

Importable from anywhere regardless of pytest's import mode or a test
file's location, because it's part of the installed ``oec`` package,
not a ``sys.path``-dependent sibling file.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

from oec.errors import SkillEntrypointError

DEFAULT_MANIFEST: dict[str, Any] = {
    "id": "mathematics.identity",
    "version": "0.1.0",
    "status": "experimental",
    "domain": "mathematics",
    "title": "Identity",
    "entrypoint": {"module": "implementation", "function": "execute"},
    "schemas": {"input": "input.schema.json", "output": "output.schema.json"},
    "method": {"id": "identity", "version": "1", "iterative": False},
}

DEFAULT_FRONT_MATTER: dict[str, Any] = {
    "id": "mathematics.identity",
    "version": "0.1.0",
    "status": "experimental",
    "domain": "mathematics",
    "title": "Identity",
}


def load_skill_module(skill_dir: Path, module_name: str) -> ModuleType:
    """Import ``<skill_dir>/<module_name>.py`` under a name unique to this skill dir."""
    skill_dir = skill_dir.resolve()
    module_file = skill_dir / f"{module_name}.py"
    if not module_file.is_file():
        raise SkillEntrypointError(
            f"skill module not found: {module_file}", details={"path": str(module_file)}
        )

    unique_name = f"oec_skill_test_{abs(hash(str(skill_dir)))}_{module_name}"
    spec = importlib.util.spec_from_file_location(unique_name, module_file)
    if spec is None or spec.loader is None:
        raise SkillEntrypointError(
            f"cannot load skill module from {module_file}", details={"path": str(module_file)}
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    implementation_code: str | None = None,
) -> Path:
    """Write a minimal skill directory under ``base / name`` and return its path.

    Starts from a valid ``mathematics.identity``-shaped skill and applies
    the given overrides/omissions, so a test only has to spell out what
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
        code = implementation_code or (
            "def execute(inputs):\n    return {'result': inputs, 'diagnostics': {}}\n"
        )
        (skill_dir / "implementation.py").write_text(code, encoding="utf-8")

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
