"""Evolutionary kernel errors."""

from __future__ import annotations

from oec.errors import OECError


class PymooNotAvailableError(OECError):
    """Raised when the optional ``pymoo`` extra is not installed."""

    default_code = "pymoo_not_available"


class DeapNotAvailableError(OECError):
    """Raised when the optional ``deap`` package is not installed (E3)."""

    default_code = "deap_not_available"


class NevergradNotAvailableError(OECError):
    """Raised when the optional ``nevergrad`` package is not installed (E4)."""

    default_code = "nevergrad_not_available"


class NeatNotAvailableError(OECError):
    """Raised when the optional ``neat-python`` package is not installed (ADR 0044)."""

    default_code = "neat_not_available"
