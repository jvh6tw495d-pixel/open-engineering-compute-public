"""pymoo backend adapter — optional extra ``oec[evolutionary]`` (ADR 0031).

Probe only for the registry/fallback layer. Algorithm dispatch lives in
``oec.kernel.evolutionary``; this module does not import pymoo at module
level so a core install without the extra stays import-clean.
"""

from __future__ import annotations

import importlib.metadata

BACKEND_NAME = "pymoo"


def probe() -> tuple[bool, str | None, str | None]:
    """Return ``(available, version, reason)`` for pymoo."""
    try:
        import pymoo  # noqa: F401
    except ImportError as exc:
        return False, None, str(exc)

    try:
        version = importlib.metadata.version("pymoo")
    except importlib.metadata.PackageNotFoundError:
        version = None
    return True, version, None
