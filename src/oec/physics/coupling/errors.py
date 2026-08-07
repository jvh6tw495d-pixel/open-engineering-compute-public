"""Coupling-domain exceptions (2.7)."""

from __future__ import annotations

from oec.physics.errors import PhysicsError


class CouplingError(PhysicsError):
    """Base error for multiphysics coupling."""

    default_code = "coupling_error"


class CouplingGraphError(CouplingError):
    """Invalid coupling graph (missing owner, units, or structure)."""

    default_code = "coupling_graph_error"


class CouplingConvergenceError(CouplingError):
    """Weak co-sim failed to converge within the iteration budget."""

    default_code = "coupling_convergence_error"


__all__ = [
    "CouplingConvergenceError",
    "CouplingError",
    "CouplingGraphError",
]
