"""Backend selection by declared capability domain (v2.4, ADR 0021).

No capability domain declared in ``oec.backends.capabilities`` currently
has more than one backend able to serve it (there is no real numpy-vs-scipy
or highs-vs-alternative choice to make today), so this is a real, honest 1:1
lookup — not a scoring/heuristic algorithm. It exists as the seam a future
multi-backend choice would extend, and so callers stop hand-coding "which
backend serves domain X" wherever they need it.
"""

from __future__ import annotations

from oec.backends.capabilities import DECLARED_CAPABILITIES
from oec.backends.registry import BackendCapability, get_backend_capabilities
from oec.core.errors import BackendUnavailableError


def select_backend_for(domain: str) -> BackendCapability:
    """Return the :class:`BackendCapability` that declares ``domain``.

    Raises :class:`~oec.core.errors.BackendUnavailableError` if no backend
    declares ``domain`` at all — a malformed/unknown domain name, not a
    "this backend happens to be missing" outcome (that is
    ``oec.backends.fallback``'s job, for a domain that *is* declared).
    """
    owners = [name for name, domains in DECLARED_CAPABILITIES.items() if domain in domains]
    if not owners:
        raise BackendUnavailableError(
            f"no backend declares capability domain {domain!r}",
            details={"domain": domain, "declared_domains": _all_declared_domains()},
        )

    by_name = {capability.name: capability for capability in get_backend_capabilities()}
    # Exactly one owner today (see module docstring); take the first
    # deterministically rather than assuming uniqueness silently.
    return by_name[owners[0]]


def _all_declared_domains() -> list[str]:
    domains: set[str] = set()
    for backend_domains in DECLARED_CAPABILITIES.values():
        domains |= backend_domains
    return sorted(domains)
