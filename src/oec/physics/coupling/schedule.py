"""Temporal schedule for coupled simulation (single clock owner v0)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CouplingSchedule:
    """Master time grid for one coupled step (v0: single step or fixed order)."""

    clock_owner: str
    domain_order: tuple[str, ...]
    dt: float = 1.0
    unit: str = "s"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.domain_order:
            raise ValueError("domain_order must be non-empty")
        if self.clock_owner not in self.domain_order:
            raise ValueError("clock_owner must appear in domain_order")
        if self.dt <= 0:
            raise ValueError("dt must be > 0")


__all__ = ["CouplingSchedule"]
