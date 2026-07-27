"""numpy backend adapter — a hard runtime dependency."""

from __future__ import annotations

BACKEND_NAME = "numpy"


def probe() -> tuple[bool, str | None, str | None]:
    """Return ``(available, version, reason)`` for numpy.

    numpy is a hard dependency (declared in ``pyproject.toml``, imported
    directly by 20+ kernel modules) — same convention as the pre-existing
    scipy probe: treated as always available, not wrapped in a
    try/except for a graceful-missing case the rest of the kernel
    couldn't survive anyway.
    """
    import numpy

    return True, numpy.__version__, None
