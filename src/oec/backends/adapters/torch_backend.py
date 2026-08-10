"""PyTorch backend adapter — optional extra ``oec[neural]`` (ADR 0031).

Probe only for the registry/fallback layer. Training/eval entry points live
in ``oec.kernel.neural``; this module does not import torch at module level
so a core install without the extra stays import-clean.
"""

from __future__ import annotations

import importlib.metadata

BACKEND_NAME = "torch"


def probe() -> tuple[bool, str | None, str | None]:
    """Return ``(available, version, reason)`` for PyTorch."""
    try:
        import torch  # noqa: F401
    except ImportError as exc:
        return False, None, str(exc)

    try:
        version = importlib.metadata.version("torch")
    except importlib.metadata.PackageNotFoundError:
        version = None
    return True, version, None
