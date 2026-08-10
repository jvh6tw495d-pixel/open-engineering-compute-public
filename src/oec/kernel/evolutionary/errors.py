"""Evolutionary kernel errors."""

from __future__ import annotations

from oec.errors import OECError


class PymooNotAvailableError(OECError):
    """Raised when the optional ``pymoo`` extra is not installed."""

    default_code = "pymoo_not_available"
