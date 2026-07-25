import pytest

from oec.execution.models import ExecutionStatus
from oec.execution.status import compute_status
from oec.validation.base import Severity, ValidationOutcome

_OK = ValidationOutcome(layer="schema", severity=Severity.OK)
_WARNING = ValidationOutcome(layer="physical", severity=Severity.WARNING, messages=["near limit"])
_ERROR = ValidationOutcome(layer="schema", severity=Severity.ERROR, messages=["missing field"])


def test_implementation_failure_takes_precedence_over_everything() -> None:
    status = compute_status([_ERROR, _WARNING], implementation_failed=True, converged=True)
    assert status is ExecutionStatus.FAILED


def test_any_error_outcome_yields_invalid() -> None:
    status = compute_status([_OK, _ERROR], converged=True)
    assert status is ExecutionStatus.INVALID


def test_non_convergence_yields_inconclusive() -> None:
    status = compute_status([_OK], converged=False)
    assert status is ExecutionStatus.INCONCLUSIVE


def test_non_convergence_beats_warnings() -> None:
    """Per ADR 0007's precedence: a non-converged solver is worse than a
    warning, even if a warning was also raised."""
    status = compute_status([_WARNING], converged=False)
    assert status is ExecutionStatus.INCONCLUSIVE


def test_warning_with_convergence_yields_converged_with_warnings() -> None:
    status = compute_status([_OK, _WARNING], converged=True)
    assert status is ExecutionStatus.CONVERGED_WITH_WARNINGS


def test_warning_with_exact_method_yields_converged_with_warnings() -> None:
    status = compute_status([_WARNING], converged=None)
    assert status is ExecutionStatus.CONVERGED_WITH_WARNINGS


def test_exact_method_with_no_warnings_yields_verified() -> None:
    status = compute_status([_OK], converged=None)
    assert status is ExecutionStatus.VERIFIED


def test_converged_iterative_method_with_no_warnings_yields_validated() -> None:
    status = compute_status([_OK], converged=True)
    assert status is ExecutionStatus.VALIDATED


def test_empty_outcomes_with_no_convergence_info_yields_verified() -> None:
    status = compute_status([], converged=None)
    assert status is ExecutionStatus.VERIFIED


@pytest.mark.parametrize("converged", [True, False, None])
def test_error_always_wins_regardless_of_convergence(converged: bool | None) -> None:
    status = compute_status([_ERROR], converged=converged)
    assert status is ExecutionStatus.INVALID
