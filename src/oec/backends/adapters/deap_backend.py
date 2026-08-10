"""DEAP backend adapter — optional via ``oec[evolutionary]`` (E3)."""

from __future__ import annotations

import importlib.metadata

BACKEND_NAME = "deap"


def probe() -> tuple[bool, str | None, str | None]:
    try:
        import deap  # noqa: F401
    except ImportError as exc:
        return False, None, str(exc)
    try:
        version = importlib.metadata.version("deap")
    except importlib.metadata.PackageNotFoundError:
        version = None
    return True, version, None
