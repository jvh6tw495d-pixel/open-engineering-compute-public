"""Loads a single skill directory into a validated, in-memory :class:`LoadedSkill`.

The loader never imports or executes a skill's Python implementation — it
only checks that the entrypoint file exists (plan section 4.7: don't run
untrusted code without need). Importing and invoking the implementation is
the Skill Execution Service's job, arriving in Sprint 03.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from oec.errors import SkillEntrypointError, SkillFrontMatterError, SkillManifestError
from oec.skills.loader.frontmatter import SkillFrontMatter, parse_front_matter
from oec.skills.loader.models import LoadedSkill
from oec.skills.schemas.manifest import SkillManifest

_MANIFEST_FILENAME = "skill.yaml"
_DOC_FILENAME = "skill.md"
_CROSS_CHECKED_FIELDS = ("id", "version", "status", "domain", "title")


def load_skill(path: Path) -> LoadedSkill:
    """Load and fully validate the skill directory at ``path``.

    Raises :class:`~oec.errors.SkillManifestError`,
    :class:`~oec.errors.SkillFrontMatterError`, or
    :class:`~oec.errors.SkillEntrypointError` — all subclasses of
    :class:`~oec.errors.SkillError` — describing exactly what is wrong.
    Never raises for a well-formed skill; never silently accepts a
    malformed one.
    """
    if not path.is_dir():
        raise SkillManifestError("skill directory does not exist", details={"path": str(path)})

    manifest = _load_manifest(path)
    front_matter, body = _load_front_matter(path)
    _cross_check(manifest, front_matter)

    _check_entrypoint(path, manifest)
    input_schema = _load_schema(path, manifest.schemas.input, field="schemas.input")
    output_schema = _load_schema(path, manifest.schemas.output, field="schemas.output")

    return LoadedSkill(
        manifest=manifest,
        front_matter=front_matter,
        path=path,
        body=body,
        input_schema=input_schema,
        output_schema=output_schema,
    )


def _load_manifest(path: Path) -> SkillManifest:
    manifest_path = path / _MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise SkillManifestError(
            f"{_MANIFEST_FILENAME} not found in skill directory",
            details={"path": str(manifest_path)},
        )

    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SkillManifestError(
            f"{_MANIFEST_FILENAME} is not valid YAML: {exc}",
            details={"path": str(manifest_path)},
        ) from exc

    if not isinstance(raw, dict):
        raise SkillManifestError(
            f"{_MANIFEST_FILENAME} must be a YAML mapping",
            details={"path": str(manifest_path), "parsed_type": type(raw).__name__},
        )

    try:
        return SkillManifest(**raw)
    except ValidationError as exc:
        raise SkillManifestError(
            f"{_MANIFEST_FILENAME} failed validation: {exc}",
            details={"path": str(manifest_path), "errors": exc.errors(include_url=False)},
        ) from exc


def _load_front_matter(path: Path) -> tuple[SkillFrontMatter, str]:
    doc_path = path / _DOC_FILENAME
    if not doc_path.is_file():
        raise SkillFrontMatterError(
            f"{_DOC_FILENAME} not found in skill directory",
            details={"path": str(doc_path)},
        )
    return parse_front_matter(doc_path.read_text(encoding="utf-8"))


def _cross_check(manifest: SkillManifest, front_matter: SkillFrontMatter) -> None:
    mismatches = {
        field: {"skill.yaml": getattr(manifest, field), "skill.md": getattr(front_matter, field)}
        for field in _CROSS_CHECKED_FIELDS
        if getattr(manifest, field) != getattr(front_matter, field)
    }
    if mismatches:
        raise SkillFrontMatterError(
            "skill.md front matter disagrees with skill.yaml",
            details={"mismatches": mismatches},
        )


def _check_entrypoint(path: Path, manifest: SkillManifest) -> None:
    module_path = path / f"{manifest.entrypoint.module}.py"
    if not module_path.is_file():
        raise SkillEntrypointError(
            "entrypoint module file not found",
            details={"expected_path": str(module_path)},
        )


def _load_schema(path: Path, relative_path: str, *, field: str) -> dict[str, Any]:
    schema_path = path / relative_path
    if not schema_path.is_file():
        raise SkillEntrypointError(
            f"{field} file not found",
            details={"field": field, "expected_path": str(schema_path)},
        )
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SkillEntrypointError(
            f"{field} is not valid JSON: {exc}",
            details={"field": field, "path": str(schema_path)},
        ) from exc

    if not isinstance(schema, dict):
        raise SkillEntrypointError(
            f"{field} must be a JSON object",
            details={"field": field, "parsed_type": type(schema).__name__},
        )
    return schema
