"""The composable validator contract every validation layer implements.

Frozen ahead of the concrete layers (schema, dimensional, mathematical,
physical, numerical, invariants — plan section 12) so they can be built
independently against one agreed shape. See
``docs/architecture/adr/0007-validation-status-model.md`` for how a list
of :class:`ValidationOutcome` becomes an ``ExecutionStatus``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, ClassVar, Protocol

from pydantic import BaseModel, ConfigDict

from oec.skills.schemas.manifest import SkillManifest


class Severity(StrEnum):
    """How serious a single validation outcome is."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class ValidationOutcome(BaseModel):
    """One validator layer's verdict on one aspect of a skill's inputs or result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    layer: str
    severity: Severity
    messages: list[str] = []
    details: dict[str, Any] = {}


class InputValidator(Protocol):
    """A pre-execution validator: schema, dimensional, mathematical domain, physical limits.

    Runs against normalized inputs *before* the skill's implementation
    executes; an :data:`Severity.ERROR` outcome from any input validator
    means the implementation never runs at all (plan section 4.5, layers
    1-6).
    """

    layer: ClassVar[str]

    def validate(
        self, manifest: SkillManifest, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]: ...


class ResultValidator(Protocol):
    """A post-execution validator: numerical diagnostics, invariants.

    Runs against the skill's actual result and diagnostics *after* the
    implementation executes — numerical convergence/residual checks only
    make sense once a solver has actually run.
    """

    layer: ClassVar[str]

    def validate(
        self,
        manifest: SkillManifest,
        normalized_inputs: dict[str, Any],
        result: dict[str, Any],
        diagnostics: dict[str, Any],
    ) -> list[ValidationOutcome]: ...
