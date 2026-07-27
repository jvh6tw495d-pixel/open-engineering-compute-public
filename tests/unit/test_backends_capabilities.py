"""Static capability domain declaration tests (ADR 0021)."""

from __future__ import annotations

from oec.backends.capabilities import (
    DECLARED_CAPABILITIES,
    OPTIONAL_BACKENDS,
    REQUIRED_BACKENDS,
    domains_for,
    is_required,
)


def test_declared_backends_are_numpy_scipy_highs() -> None:
    assert set(DECLARED_CAPABILITIES) == {"numpy", "scipy", "highs"}


def test_required_and_optional_partition_declared_backends() -> None:
    assert {"numpy", "scipy"} == REQUIRED_BACKENDS
    assert {"highs"} == OPTIONAL_BACKENDS
    assert REQUIRED_BACKENDS.isdisjoint(OPTIONAL_BACKENDS)


def test_domains_for_known_backend() -> None:
    assert domains_for("numpy") == {"dense_linear_algebra", "rng"}


def test_domains_for_unknown_backend_is_empty() -> None:
    assert domains_for("not_a_backend") == frozenset()


def test_is_required() -> None:
    assert is_required("numpy") is True
    assert is_required("highs") is False
    assert is_required("not_a_backend") is False


def test_scipy_interpolate_is_not_declared() -> None:
    """Nothing in the kernel calls scipy.interpolate today (ADR 0021) --
    declaring it would be aspirational, not a real capability."""
    assert "interpolate" not in domains_for("scipy")
