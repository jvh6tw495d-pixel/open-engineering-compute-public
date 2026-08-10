"""Evolutionary kernel — thin pymoo wrappers (ADR 0031)."""

from __future__ import annotations

from oec.kernel.evolutionary.errors import PymooNotAvailableError
from oec.kernel.evolutionary.optimize import optimize_single

__all__ = ["PymooNotAvailableError", "optimize_single"]
