"""Typed diagnostics for scientific runs (v2.0 kernel)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DiagnosticSeverity = Literal["info", "warning", "error"]


class Diagnostic(BaseModel):
    """One structured diagnostic item (post-execution or validation)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    severity: DiagnosticSeverity = "info"
    details: dict[str, Any] = Field(default_factory=dict)


def diagnostics_from_mapping(raw: dict[str, Any] | None) -> list[Diagnostic]:
    """Best-effort parse of legacy diagnostics dict → typed list.

    Unknown shapes become a single ``legacy_diagnostics`` info item so data
    is not lost when adapting ExecutionResult.
    """
    if not raw:
        return []
    items: list[Diagnostic] = []
    # Common pattern: { "converged": bool, "message": str, ... }
    if "converged" in raw:
        items.append(
            Diagnostic(
                code="converged",
                message=str(raw.get("message") or f"converged={raw['converged']}"),
                severity="info" if raw.get("converged") else "warning",
                details={"converged": raw.get("converged")},
            )
        )
    if "message" in raw and "converged" not in raw:
        items.append(
            Diagnostic(
                code="message",
                message=str(raw["message"]),
                severity="info",
            )
        )
    # Preserve remainder as opaque details
    known = {"converged", "message"}
    rest = {k: v for k, v in raw.items() if k not in known}
    if rest:
        items.append(
            Diagnostic(
                code="legacy_diagnostics",
                message="Unstructured diagnostics payload from ExecutionResult",
                severity="info",
                details=rest,
            )
        )
    return items
