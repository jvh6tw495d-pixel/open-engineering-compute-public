"""Convergence helpers for weak co-sim (ADR 0025 residual style)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConvergenceCriteria:
    """Absolute/relative residual thresholds and iteration budget."""

    atol: float = 1e-6
    rtol: float = 1e-6
    max_iter: int = 100
    scale: float = 1.0

    def threshold(self) -> float:
        return float(self.atol) + float(self.rtol) * abs(float(self.scale))


def residual_ok(residual: float, criteria: ConvergenceCriteria) -> bool:
    """Return True when |residual| is within atol + rtol×scale."""
    return abs(float(residual)) <= criteria.threshold()


__all__ = ["ConvergenceCriteria", "residual_ok"]
