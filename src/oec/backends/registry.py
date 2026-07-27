"""Minimal Backend Capability descriptors for the two backends the Math IR
compilers use today (``highs``, ``scipy``). Not a selection/fallback engine —
that is a v2.4 item; see the package docstring.
"""

from __future__ import annotations

import importlib.metadata

from pydantic import BaseModel, ConfigDict


class BackendCapability(BaseModel):
    """Whether a named computational backend is available in this environment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    available: bool
    version: str | None = None
    reason: str | None = None


def _highs_capability() -> BackendCapability:
    try:
        import highspy  # noqa: F401
    except ImportError as exc:
        return BackendCapability(name="highs", available=False, reason=str(exc))

    try:
        version = importlib.metadata.version("highspy")
    except importlib.metadata.PackageNotFoundError:
        version = None
    return BackendCapability(name="highs", available=True, version=version)


def _scipy_capability() -> BackendCapability:
    import scipy

    return BackendCapability(name="scipy", available=True, version=scipy.__version__)


def get_backend_capabilities() -> list[BackendCapability]:
    """Return the capability descriptors for every backend the Math IR uses."""
    return [_highs_capability(), _scipy_capability()]
