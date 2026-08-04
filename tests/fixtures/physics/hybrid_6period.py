"""Public 6-period microgrid hybrid fixture (v2.6.1 Wave 1).

Canonical textbook multiperiod data used across OEC benchmarks
(LOAD / PV in MWh per period). Trajectories below are **hand-constructed**
feasible schedules for :func:`oec.physics.hybrid.hybrid_balance` — not an
LP optimum. ``grid_import < 0`` denotes export (single-field convention).
"""

from __future__ import annotations

from typing import Any

# Public multiperiod microgrid energies (MWh / period)
LOAD: list[float] = [3.1, 2.4, 1.6, 2.15, 2.35, 2.1]
PV: list[float] = [0.0, 1.45, 2.55, 1.35, 0.65, 0.25]
N: int = 6
UNIT: str = "MWh"

# Feasible hand trajectory (eta=1 bookkeeping; residual 0 each period).
# Period 2 has PV surplus: part charged, part exported (negative grid_import).
CHARGE: list[float] = [0.0, 0.0, 0.5, 0.0, 0.0, 0.0]
DISCHARGE: list[float] = [0.0, 0.5, 0.0, 0.3, 0.7, 0.85]
# grid_import[t] = LOAD - PV - discharge + charge
# t2: 1.6 - 2.55 - 0 + 0.5 = -0.45 (export)
GRID_IMPORT: list[float] = [3.1, 0.45, -0.45, 0.5, 1.0, 1.0]


def hybrid_6period_inputs() -> dict[str, Any]:
    """Keyword arguments for :func:`oec.physics.hybrid.hybrid_balance`."""
    return {
        "load": list(LOAD),
        "pv": list(PV),
        "grid_import": list(GRID_IMPORT),
        "charge": list(CHARGE),
        "discharge": list(DISCHARGE),
        "unit": UNIT,
    }
