"""Backend fallback policy tests (ADR 0021)."""

from __future__ import annotations

import pytest

import oec.backends.fallback as fallback
from oec.backends.registry import BackendCapability
from oec.validation.base import Severity


def test_unmapped_method_id_has_no_requirement() -> None:
    assert fallback.check_backend_availability("scipy_root") == []


def test_mapped_method_available_backend_passes() -> None:
    assert fallback.check_backend_availability("highs_lp") == []


@pytest.mark.parametrize(
    "method_id",
    [
        "highs_lp",
        "highs_milp",
        "highs_feasibility",
        "highs_lp_diagnostics",
        "highs_weighted_sum",
        "highs_scenario_batch",
    ],
)
def test_every_highs_method_id_is_mapped_to_highs(
    method_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        fallback,
        "get_backend_capabilities",
        lambda: [
            BackendCapability(
                name="highs",
                available=False,
                reason="not installed",
                domains=frozenset({"lp", "milp"}),
            )
        ],
    )
    outcomes = fallback.check_backend_availability(method_id)
    assert len(outcomes) == 1
    assert outcomes[0].severity is Severity.ERROR
    assert outcomes[0].layer == "backend_fit"


def test_unavailable_backend_yields_error_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        fallback,
        "get_backend_capabilities",
        lambda: [
            BackendCapability(
                name="highs",
                available=False,
                reason="highspy not installed",
                domains=frozenset({"lp"}),
            )
        ],
    )
    outcomes = fallback.check_backend_availability("highs_lp")
    assert len(outcomes) == 1
    assert "not available" in outcomes[0].messages[0]
    assert "highspy not installed" in outcomes[0].messages[0]


def test_available_backend_after_monkeypatch_yields_no_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        fallback,
        "get_backend_capabilities",
        lambda: [
            BackendCapability(
                name="highs", available=True, version="1.0", domains=frozenset({"lp"})
            )
        ],
    )
    assert fallback.check_backend_availability("highs_lp") == []
