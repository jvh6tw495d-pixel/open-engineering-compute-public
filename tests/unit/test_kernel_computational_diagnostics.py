"""ComputationalDiagnostics shared shape tests (ADR 0022)."""

from __future__ import annotations

import pytest

from oec.kernel.computational.diagnostics import ComputationalDiagnostics


def test_core_fields_default_to_none_or_empty() -> None:
    diag = ComputationalDiagnostics(method="x", backend="scipy", converged=True)
    assert diag.iterations is None
    assert diag.function_calls is None
    assert diag.residual is None
    assert diag.message == ""


def test_converged_none_means_exact_non_iterative() -> None:
    diag = ComputationalDiagnostics(method="linear", backend="numpy", converged=None)
    assert diag.converged is None


def test_extra_fields_are_allowed_and_readable() -> None:
    diag = ComputationalDiagnostics(
        method="adaptive_quad", backend="scipy", converged=True, abs_error=1e-10
    )
    assert diag.abs_error == 1e-10
    assert diag.model_dump()["abs_error"] == 1e-10


def test_model_is_frozen() -> None:
    diag = ComputationalDiagnostics(method="x", backend="scipy", converged=True)
    with pytest.raises(Exception):  # noqa: B017 -- pydantic ValidationError on frozen assign
        diag.method = "changed"  # type: ignore[misc]
