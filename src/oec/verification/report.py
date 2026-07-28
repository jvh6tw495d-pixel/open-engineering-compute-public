"""The `VerificationReport` shape (v2.4, ADR 0021)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PreVerificationCheck(BaseModel):
    """One pre-execution verification check's outcome."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    passed: bool
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class PostVerificationCheck(BaseModel):
    """One post-execution verification check's outcome.

    ``passed`` is ``None`` for a check that is purely informational --
    reported, not evaluated -- rather than fabricating a verdict where no
    documented target exists to evaluate against (same convention as
    :class:`~oec.kernel.computational.diagnostics.ComputationalDiagnostics
    .converged`, ADR 0022). A check with ``passed`` always ``True`` and
    never ``False`` is a reporting field, not a check; give it ``None``
    instead so callers can't mistake "always reported clean" for "actually
    evaluated."
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    passed: bool | None
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class VerificationReport(BaseModel):
    """The structured pre/post verification report for one execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pre: list[PreVerificationCheck] = Field(default_factory=list)
    post: list[PostVerificationCheck] = Field(default_factory=list)
