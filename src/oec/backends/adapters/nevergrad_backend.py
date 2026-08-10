"""Nevergrad backend adapter — optional via ``oec[evolutionary]`` (E4)."""

from __future__ import annotations

import importlib.metadata

BACKEND_NAME = "nevergrad"


def probe() -> tuple[bool, str | None, str | None]:
    try:
        import nevergrad  # noqa: F401
    except ImportError as exc:
        return False, None, str(exc)
    try:
        version = importlib.metadata.version("nevergrad")
    except importlib.metadata.PackageNotFoundError:
        version = None
    return True, version, None
