"""X3 method selection unit tests (no extras required)."""

from __future__ import annotations

import pytest

from oec.kernel.scientific.method_select import select_method


def test_unknown_class_raises() -> None:
    with pytest.raises(ValueError, match="unknown problem_class"):
        select_method(problem_class="not_a_class")


def test_catalog_returns_structure() -> None:
    out = select_method(problem_class="symbolic_regression", run_probe_benchmark=False)
    assert out["problem_class"] == "symbolic_regression"
    assert "available_candidates" in out
    assert "policy" in out
