"""Neural kernel errors."""

from __future__ import annotations

from oec.errors import OECError


class TorchNotAvailableError(OECError):
    """Raised when the optional ``torch`` extra is not installed."""

    default_code = "torch_not_available"


class JaxNotAvailableError(OECError):
    """Raised when the optional ``jax`` extra is not installed."""

    default_code = "jax_not_available"
