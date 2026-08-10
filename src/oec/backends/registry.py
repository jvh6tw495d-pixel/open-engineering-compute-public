"""Backend Capability Registry (v2.4, ADR 0021): the source of truth for
which computational backends are available and what capability domains
they declare.

Grows the v2.2 skeleton (ADR 0020, which covered only availability for
``highs``/``scipy``): probing now lives in ``oec.backends.adapters`` (one
thin module per backend), and each :class:`BackendCapability` record is
enriched with the static ``domains``/``required`` declarations from
``oec.backends.capabilities``. This is deliberately separate from
``oec.execution.provenance.installed_backends()`` (ADR 0017), which records
environment bookkeeping for audit trails, not capability truth for
selection/fallback — see ADR 0021 for why the two are not merged.
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from oec.backends import capabilities
from oec.backends.adapters import (
    deap_backend,
    highs_backend,
    nevergrad_backend,
    numpy_backend,
    pymoo_backend,
    scipy_backend,
    torch_backend,
)


class BackendCapability(BaseModel):
    """Whether a named computational backend is available, and what it declares."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    available: bool
    version: str | None = None
    reason: str | None = None
    domains: frozenset[str] = Field(default_factory=frozenset)
    required: bool = False


_PROBES: dict[str, Callable[[], tuple[bool, str | None, str | None]]] = {
    numpy_backend.BACKEND_NAME: numpy_backend.probe,
    scipy_backend.BACKEND_NAME: scipy_backend.probe,
    highs_backend.BACKEND_NAME: highs_backend.probe,
    torch_backend.BACKEND_NAME: torch_backend.probe,
    pymoo_backend.BACKEND_NAME: pymoo_backend.probe,
    deap_backend.BACKEND_NAME: deap_backend.probe,
    nevergrad_backend.BACKEND_NAME: nevergrad_backend.probe,
}


def get_backend_capabilities() -> list[BackendCapability]:
    """Return the capability descriptor for every declared backend."""
    result: list[BackendCapability] = []
    for name, probe in _PROBES.items():
        available, version, reason = probe()
        result.append(
            BackendCapability(
                name=name,
                available=available,
                version=version,
                reason=reason,
                domains=capabilities.domains_for(name),
                required=capabilities.is_required(name),
            )
        )
    return result
