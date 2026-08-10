"""Backend registry coverage for torch / pymoo (ADR 0031)."""

from __future__ import annotations

from oec.backends.capabilities import OPTIONAL_BACKENDS, domains_for
from oec.backends.fallback import check_backend_availability
from oec.backends.registry import get_backend_capabilities
from oec.validation.base import Severity


def test_torch_and_pymoo_are_optional_backends() -> None:
    assert "torch" in OPTIONAL_BACKENDS
    assert "pymoo" in OPTIONAL_BACKENDS
    caps = {c.name: c for c in get_backend_capabilities()}
    assert "torch" in caps
    assert "pymoo" in caps
    assert caps["torch"].required is False
    assert caps["pymoo"].required is False


def test_neural_and_evolutionary_domains_declared() -> None:
    assert "neural_train" in domains_for("torch")
    assert "neural_eval" in domains_for("torch")
    assert "evolutionary_single" in domains_for("pymoo")
    assert "evolutionary_multi" in domains_for("pymoo")


def test_missing_torch_yields_backend_fit_error_for_train_method() -> None:
    caps = {c.name: c for c in get_backend_capabilities()}
    if caps["torch"].available:
        # Environment has torch; nothing to assert about missing extra.
        return
    outcomes = check_backend_availability("torch_mlp_regressor_train")
    assert len(outcomes) == 1
    assert outcomes[0].severity is Severity.ERROR
    assert "torch" in outcomes[0].messages[0]


def test_missing_pymoo_yields_backend_fit_error() -> None:
    caps = {c.name: c for c in get_backend_capabilities()}
    if caps["pymoo"].available:
        return
    outcomes = check_backend_availability("pymoo_de")
    assert len(outcomes) == 1
    assert outcomes[0].severity is Severity.ERROR


def test_unknown_method_has_no_backend_requirement() -> None:
    assert check_backend_availability("ols_closed_form") == []
