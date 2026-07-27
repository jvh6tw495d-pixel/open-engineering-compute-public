"""Backend Capability skeleton tests (ADR 0020)."""

from __future__ import annotations

from oec.backends.registry import BackendCapability, get_backend_capabilities


def test_get_backend_capabilities_covers_highs_and_scipy() -> None:
    capabilities = get_backend_capabilities()
    names = {capability.name for capability in capabilities}
    assert names == {"highs", "scipy"}


def test_scipy_is_always_available() -> None:
    capabilities = {c.name: c for c in get_backend_capabilities()}
    scipy_capability = capabilities["scipy"]
    assert scipy_capability.available is True
    assert scipy_capability.version is not None


def test_capability_model_is_frozen() -> None:
    capability = BackendCapability(name="test", available=True)
    try:
        capability.name = "changed"  # type: ignore[misc]
        raised = False
    except Exception:  # noqa: BLE001
        raised = True
    assert raised
