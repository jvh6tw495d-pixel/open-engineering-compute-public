"""HiGHS backend adapter — an optional extra (``oec[optimization]``).

Moved here from ``registry.py``'s v2.2 ``_highs_capability()`` (ADR 0020),
unchanged in behavior. The sole HiGHS access point in the kernel remains
``oec.kernel.optimization.highs`` (``HighsNotAvailableError``); this probe
only reports availability for the registry/fallback layer, it is not a
second entry point into the solver.
"""

from __future__ import annotations

import importlib.metadata

BACKEND_NAME = "highs"


def probe() -> tuple[bool, str | None, str | None]:
    """Return ``(available, version, reason)`` for HiGHS (``highspy``)."""
    try:
        import highspy  # noqa: F401
    except ImportError as exc:
        return False, None, str(exc)

    try:
        version = importlib.metadata.version("highspy")
    except importlib.metadata.PackageNotFoundError:
        version = None
    return True, version, None
