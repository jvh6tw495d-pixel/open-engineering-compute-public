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
    """One post-execution verification check's outcome."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    passed: bool
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class VerificationReport(BaseModel):
    """The structured pre/post verification report for one execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pre: list[PreVerificationCheck] = Field(default_factory=list)
    post: list[PostVerificationCheck] = Field(default_factory=list)
