"""Backend Capability Registry tests (v2.4, ADR 0021 — grows the ADR 0020 skeleton)."""

from __future__ import annotations

from oec.backends.registry import BackendCapability, get_backend_capabilities


def test_get_backend_capabilities_covers_numpy_scipy_highs() -> None:
    capabilities = get_backend_capabilities()
    names = {capability.name for capability in capabilities}
    # ADR 0031 + E3/E4: torch/pymoo/deap/nevergrad optional probes.
    assert names == {
        "highs",
        "scipy",
        "numpy",
        "torch",
        "pymoo",
        "deap",
        "nevergrad",
    }


def test_numpy_and_scipy_are_required_and_always_available() -> None:
    capabilities = {c.name: c for c in get_backend_capabilities()}
    for name in ("numpy", "scipy"):
        assert capabilities[name].available is True
        assert capabilities[name].version is not None
        assert capabilities[name].required is True


def test_highs_is_optional() -> None:
    capabilities = {c.name: c for c in get_backend_capabilities()}
    assert capabilities["highs"].required is False


def test_domains_are_populated_per_backend() -> None:
    capabilities = {c.name: c for c in get_backend_capabilities()}
    assert "rng" in capabilities["numpy"].domains
    assert "root_finding" in capabilities["scipy"].domains
    assert "lp" in capabilities["highs"].domains


def test_capability_model_is_frozen() -> None:
    capability = BackendCapability(name="test", available=True)
    try:
        capability.name = "changed"  # type: ignore[misc]
        raised = False
    except Exception:  # noqa: BLE001
        raised = True
    assert raised
