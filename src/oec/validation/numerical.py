"""Non-fatal numerical diagnostics on a skill's result (plan section 12.5).

Does **not** re-decide convergence — that is a separate input to
:func:`~oec.execution.status.compute_status` (ADR 0007). This layer only
surfaces warning-level signals already present in ``diagnostics`` (near
iteration limits, poor conditioning, residual above tolerance) so a
converged-but-shaky result can become ``CONVERGED_WITH_WARNINGS``.
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
        del skill, normalized_inputs, result  # interface contract; unused here
        outcomes: list[ValidationOutcome] = []

        iterations = diagnostics.get("iterations")
        max_iterations = diagnostics.get("max_iterations")
        if (
            isinstance(iterations, int | float)
            and isinstance(max_iterations, int | float)
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

        residual = diagnostics.get("residual")
        tolerance = diagnostics.get("tolerance")
        if (
            isinstance(residual, int | float)
            and isinstance(tolerance, int | float)
            and abs(residual) > tolerance
        ):
            outcomes.append(
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.WARNING,
                    messages=["residual exceeds tolerance"],
                    details={"residual": residual, "tolerance": tolerance},
                )
            )

        return outcomes
