import pytest
from pydantic import ValidationError

from oec.validation.base import Severity, ValidationOutcome


def test_validation_outcome_defaults() -> None:
    outcome = ValidationOutcome(layer="schema", severity=Severity.OK)
    assert outcome.messages == []
    assert outcome.details == {}


def test_validation_outcome_is_frozen() -> None:
    outcome = ValidationOutcome(layer="schema", severity=Severity.OK)
    with pytest.raises(ValidationError):
        outcome.severity = Severity.ERROR  # type: ignore[misc]


def test_severity_has_exactly_three_levels() -> None:
    assert {s.value for s in Severity} == {"ok", "warning", "error"}
