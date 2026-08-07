"""Turns validator outcomes and a convergence flag into an ``ExecutionStatus``.

The precedence table this implements is
``docs/architecture/adr/0007-validation-status-model.md`` — that ADR is
the source of truth; this function is its only implementation. A
validator layer never computes status itself, only
:class:`~oec.validation.base.ValidationOutcome` entries.
"""

from __future__ import annotations

from oec.execution.models import ExecutionStatus
from oec.validation.base import Severity, ValidationOutcome


def compute_status(
    outcomes: list[ValidationOutcome],
    *,
    implementation_failed: bool = False,
    converged: bool | None = None,
) -> ExecutionStatus:
    """Compute the execution status per ADR 0007's precedence table.

    Args:
        outcomes: every input- and result-validator outcome collected
            for this execution.
        implementation_failed: whether the skill's implementation raised,
            timed out, or otherwise produced no result at all. Takes
            precedence over every ``outcomes`` entry.
        converged: ``None`` for an exact/closed-form method (no
            convergence concept applies); ``True``/``False`` for an
            iterative/numerical method that did or didn't converge.
            Ignored when ``implementation_failed`` is true or any
            ``outcomes`` entry is an error.
    """
    if implementation_failed:
        return ExecutionStatus.FAILED

    has_error = any(outcome.severity is Severity.ERROR for outcome in outcomes)
    if has_error:
        return ExecutionStatus.INVALID

    if converged is False:
        return ExecutionStatus.INCONCLUSIVE

    has_warning = any(outcome.severity is Severity.WARNING for outcome in outcomes)
    if has_warning:
        return ExecutionStatus.CONVERGED_WITH_WARNINGS

    if converged is None:
        return ExecutionStatus.VERIFIED
    return ExecutionStatus.VALIDATED
