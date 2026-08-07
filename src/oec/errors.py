"""Base exception hierarchy for the Open Engineering Compute framework.

All OEC-specific exceptions carry a machine-readable ``code`` and a
structured ``details`` mapping so that interfaces (CLI, REST, MCP) can
surface errors consistently without leaking internal state or secrets.
Domain-specific hierarchies (skill loading, execution, validation) extend
:class:`OECError` in later sprints; this module only defines the shared
root and the top-level categories referenced by the execution pipeline.
"""

from __future__ import annotations

from typing import Any


class OECError(Exception):
    """Root of every exception raised by the OEC framework."""

    default_code = "oec_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Structured, secret-free representation suitable for API responses."""
        return {"code": self.code, "message": self.message, "details": self.details}


class SkillError(OECError):
    """Raised for failures in locating, loading, or resolving a skill."""

    default_code = "skill_error"


class SkillNotFoundError(SkillError):
    """Raised when a referenced skill id/version cannot be resolved."""

    default_code = "skill_not_found"


class SkillManifestError(SkillError):
    """Raised when a ``skill.yaml`` manifest is missing or malformed."""

    default_code = "skill_manifest_invalid"


class SkillFrontMatterError(SkillError):
    """Raised when ``skill.md`` front matter is missing, malformed, or disagrees
    with the ``skill.yaml`` manifest for the same skill."""

    default_code = "skill_frontmatter_invalid"


class SkillEntrypointError(SkillError):
    """Raised when a skill's entrypoint module or declared schema files are missing."""

    default_code = "skill_entrypoint_invalid"


class SkillVersionConflictError(SkillError):
    """Raised when two skill directories declare the same id and version."""

    default_code = "skill_version_conflict"


class OECValidationError(OECError):
    """Raised when input, dimensional, mathematical, or physical validation fails.

    Named to avoid colliding with :class:`pydantic.ValidationError`.
    """

    default_code = "validation_error"


class ExecutionError(OECError):
    """Raised when a skill implementation fails during execution."""

    default_code = "execution_error"


class UnitError(OECValidationError):
    """Raised when a quantity's unit is dimensionally incompatible with the
    unit it is being normalized or compared against."""

    default_code = "unit_incompatible"


class NumericalDomainError(OECValidationError):
    """Raised when a numerical method's kernel call is malformed at the
    mathematical domain level (e.g. a root-finding bracket that doesn't
    actually bracket a sign change, an unknown method name). Distinct
    from non-convergence, which is a valid diagnostic outcome (ADR 0007),
    not an error the kernel raises."""

    default_code = "numerical_domain_invalid"
