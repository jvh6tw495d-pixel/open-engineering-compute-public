"""Static capability domain declaration tests (ADR 0021 + W6/W8)."""

from __future__ import annotations

from oec.backends.capabilities import (
    DECLARED_CAPABILITIES,
    OPTIONAL_BACKENDS,
    REQUIRED_BACKENDS,
    domains_for,
    is_required,
)


def test_required_core_backends() -> None:
    assert {"numpy", "scipy", "sympy"} <= REQUIRED_BACKENDS


def test_optional_includes_extras() -> None:
    for name in ("highs", "torch", "pymoo", "deap", "nevergrad", "transformers"):
        assert name in OPTIONAL_BACKENDS
    assert REQUIRED_BACKENDS.isdisjoint(OPTIONAL_BACKENDS)


def test_declared_contains_registry_backends() -> None:
    for name in ("numpy", "scipy", "highs", "torch", "transformers", "sympy"):
        assert name in DECLARED_CAPABILITIES


def test_domains_for_known_backend() -> None:
    assert domains_for("numpy") == {"dense_linear_algebra", "rng"}
    assert "foundation_embed" in domains_for("transformers")
    assert "symbolic" in domains_for("sympy")


def test_domains_for_unknown_backend_is_empty() -> None:
    assert domains_for("not_a_backend") == frozenset()


def test_is_required() -> None:
    assert is_required("numpy") is True
    assert is_required("sympy") is True
    assert is_required("highs") is False
    assert is_required("transformers") is False
    assert is_required("not_a_backend") is False


def test_scipy_interpolate_is_not_declared() -> None:
    """Nothing in the kernel calls scipy.interpolate today (ADR 0021)."""
    assert "interpolate" not in domains_for("scipy")
