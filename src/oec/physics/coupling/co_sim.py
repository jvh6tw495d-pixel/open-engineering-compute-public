"""Generic weak co-simulation engine (Gauss–Seidel staggered v0)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from oec.physics.coupling.checkpoint import CheckpointStore
from oec.physics.coupling.convergence import ConvergenceCriteria, residual_ok
from oec.physics.coupling.errors import CouplingConvergenceError, CouplingGraphError
from oec.physics.coupling.graph import CouplingGraph
from oec.physics.coupling.schedule import CouplingSchedule

DomainStepFn = Callable[[dict[str, Any]], float]
"""Domain step: mutates shared state, returns residual contribution for that domain."""


@dataclass
class CoupledStepResult:
    """Result of one coupled time step."""

    converged: bool
    iterations: int
    residual: float
    state: dict[str, Any] = field(default_factory=dict)
    residual_history: list[float] = field(default_factory=list)


def run_coupled(
    graph: CouplingGraph,
    domain_steps: Mapping[str, DomainStepFn],
    *,
    initial_state: Mapping[str, Any] | None = None,
    schedule: CouplingSchedule | None = None,
    criteria: ConvergenceCriteria | None = None,
) -> CoupledStepResult:
    """Advance one coupled step with staggered Gauss–Seidel iteration.

    Parameters
    ----------
    graph:
        Validated coupling graph (declares domains and clock owner).
    domain_steps:
        Map domain_id → callable(state) -> residual. Callables must be
        deterministic given state (ADR 0004).
    initial_state:
        Shared state dict (quantities exchanged between domains).
    schedule:
        Optional order override; defaults to sorted domain names with
        graph.clock_owner first.
    criteria:
        Convergence budget.
    """
    graph.validate()
    criteria = criteria or ConvergenceCriteria()
    state: dict[str, Any] = dict(initial_state or {})
    domains = sorted(graph.domains())
    if schedule is None:
        # clock owner first, then remaining domains alphabetically
        rest = [d for d in domains if d != graph.clock_owner]
        order = (graph.clock_owner, *rest)
        schedule = CouplingSchedule(clock_owner=graph.clock_owner, domain_order=order)
    else:
        if schedule.clock_owner != graph.clock_owner:
            raise CouplingGraphError(
                "schedule.clock_owner must match graph.clock_owner (single clock v0)"
            )
        order = schedule.domain_order

    for d in order:
        if d not in domain_steps:
            raise CouplingGraphError(f"missing domain step function for {d!r}")

    store = CheckpointStore()
    store.push(state)
    history: list[float] = []
    residual = float("inf")

    for it in range(1, criteria.max_iter + 1):
        residuals: list[float] = []
        for d in order:
            r = float(domain_steps[d](state))
            residuals.append(abs(r))
        residual = max(residuals) if residuals else 0.0
        history.append(residual)
        if residual_ok(residual, criteria):
            return CoupledStepResult(
                converged=True,
                iterations=it,
                residual=residual,
                state=dict(state),
                residual_history=history,
            )
        store.push(state)

    # failed — restore last good checkpoint (caller keeps initial_state intact)
    _restored = store.peek() or dict(initial_state or {})
    raise CouplingConvergenceError(
        f"coupling did not converge in {criteria.max_iter} iterations "
        f"(last residual={residual}, threshold={criteria.threshold()}); "
        f"checkpoint retained ({len(store)} snapshots)"
    )


__all__ = ["CoupledStepResult", "DomainStepFn", "run_coupled"]
