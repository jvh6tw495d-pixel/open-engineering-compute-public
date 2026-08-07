"""scipy backend adapter — a hard runtime dependency.

Moved here from ``registry.py``'s v2.2 ``_scipy_capability()`` (ADR 0020),
unchanged in behavior.
"""

from __future__ import annotations

BACKEND_NAME = "scipy"


def probe() -> tuple[bool, str | None, str | None]:
    """Return ``(available, version, reason)`` for scipy — always available."""
    import scipy

    return True, scipy.__version__, None
