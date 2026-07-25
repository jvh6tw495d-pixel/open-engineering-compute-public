"""Non-fatal numerical diagnostics on a skill's result (plan section 12.5).

Does **not** re-decide convergence — that is a separate input to
:func:`~oec.execution.status.compute_status` (ADR 0007). This layer only
surfaces warning-level signals already present in ``diagnostics``/
``normalized_inputs`` (near iteration limits, poor conditioning,
residual above tolerance) so a converged-but-shaky result can become
``CONVERGED_WITH_WARNINGS``.

Field names are read with fallbacks across the shapes real skills
actually use (ADR 0014): ``iterations``/``n_iterations``,
``residual``/``abs_error``/the max of a ``residuals`` list, and
``max_iterations``/``tolerance`` read from the *caller's inputs*
(``normalized_inputs``) since no skill echoes either back into
``diagnostics`` — reading them from ``diagnostics`` alone (the original
Sprint 03 shape) meant these checks could never fire for any of the six
skills shipped through Sprint 05, an independent review caught.
"""

from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class NumericalDiagnosticsValidator:
    """Inspect post-execution diagnostics for non-fatal numerical warnings."""

    layer: ClassVar[str] = "numerical"

    def validate(
        self,
        skill: LoadedSkill,
        normalized_inputs: dict[str, Any],
        result: dict[str, Any],
        diagnostics: dict[str, Any],
    ) -> list[ValidationOutcome]:
        del skill, result  # interface contract; unused here
        outcomes: list[ValidationOutcome] = []

        iterations = _first_number(diagnostics, "iterations", "n_iterations")
        max_iterations = _first_number(normalized_inputs, "max_iterations")
        if (
            iterations is not None
            and max_iterations is not None
            and max_iterations > 0
            and iterations >= 0.9 * max_iterations
        ):
            outcomes.append(
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.WARNING,
                    messages=["near iteration limit"],
                    details={
                        "iterations": iterations,
                        "max_iterations": max_iterations,
                    },
                )
            )

        condition_number = diagnostics.get("condition_number")
        if isinstance(condition_number, int | float) and condition_number > 1e8:
            outcomes.append(
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.WARNING,
                    messages=["poorly conditioned"],
                    details={"condition_number": condition_number},
                )
            )

        residual = _first_number(diagnostics, "residual", "abs_error")
        if residual is None:
            residuals = diagnostics.get("residuals")
            if isinstance(residuals, list) and residuals:
                magnitudes = [abs(r) for r in residuals if isinstance(r, int | float)]
                residual = max(magnitudes) if magnitudes else None
        tolerance = _first_number(normalized_inputs, "tolerance") or _first_number(
            diagnostics, "tolerance"
        )
        if residual is not None and tolerance is not None and abs(residual) > tolerance:
            outcomes.append(
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.WARNING,
                    messages=["residual exceeds tolerance"],
                    details={"residual": residual, "tolerance": tolerance},
                )
            )

        return outcomes


def _first_number(mapping: dict[str, Any], *keys: str) -> float | None:
    """The first of ``keys`` present in ``mapping`` with a numeric (non-bool) value."""
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
    return None
