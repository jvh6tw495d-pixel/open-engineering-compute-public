"""The ``SkillManifest`` model: the operational contract declared by ``skill.yaml``.

See ``docs/architecture/adr/0002-markdown-plus-manifest.md`` for why a skill
is described by a human-readable ``skill.md`` plus this machine-readable
manifest, and ``0001-skill-first-architecture.md`` for why the manifest,
not any interface, is the source of truth for a skill's contract.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from oec.common import SEMVER_PATTERN, VersionedRef

_SKILL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


class SkillStatus(StrEnum):
    """Lifecycle state of a skill, per the plan's lifecycle rules (section 8.3)."""

    EXPERIMENTAL = "experimental"
    VALIDATED = "validated"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class EntrypointSpec(BaseModel):
    """Where the skill's deterministic implementation lives."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    module: str
    function: str


class SchemaRefs(BaseModel):
    """Paths to the skill's input/output JSON Schemas, relative to the skill directory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    input: str
    output: str


class ExecutionPolicy(BaseModel):
    """Execution constraints enforced by the Skill Execution Service."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    deterministic: bool = True
    timeout_seconds: float = 5.0
    network_access: bool = False
    filesystem_access: bool = False


class ValidationPolicy(BaseModel):
    """Which validation layers apply to this skill's executions."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    schema_layer: bool = Field(default=True, alias="schema")
    dimensional: bool = True
    mathematical: bool = True
    physical: bool = True
    numerical: bool = True


class SkillManifest(BaseModel):
    """The operational manifest of a skill, parsed from ``skill.yaml``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    status: SkillStatus
    domain: str
    title: str
    description: str = ""
    entrypoint: EntrypointSpec
    input_schema: str
    output_schema: str
    method: VersionedRef
    execution_policy: ExecutionPolicy = ExecutionPolicy()
    validation_policy: ValidationPolicy = ValidationPolicy()
    references: list[str] = []
    tags: list[str] = []

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        if not _SKILL_ID_PATTERN.match(value):
            raise ValueError(
                f"skill id {value!r} must look like 'domain.skill_name' (lowercase, dot-separated)"
            )
        return value

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        if not re.match(SEMVER_PATTERN, value):
            raise ValueError(f"skill version {value!r} must be semantic (e.g. '0.1.0')")
        return value
