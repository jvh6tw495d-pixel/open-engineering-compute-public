"""neural.architecture_vary — closed IR mutate/crossover."""

from __future__ import annotations

from typing import Any

from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.graph import ArchitectureGraph
from oec.neural.architecture.operators import crossover_graphs, mutate_graph


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    mode = str(inputs["mode"])
    operator = str(inputs["operator"])
    seed = int(inputs.get("seed", 0))
    try:
        if mode == "mutate":
            raw = inputs.get("graph")
            if not isinstance(raw, dict):
                raise ArchitectureValidationError("mutate requires graph object")
            child = mutate_graph(
                ArchitectureGraph.model_validate(raw),
                operator=operator,  # type: ignore[arg-type]
                seed=seed,
            )
        elif mode == "crossover":
            first = inputs.get("first")
            second = inputs.get("second")
            if not isinstance(first, dict) or not isinstance(second, dict):
                raise ArchitectureValidationError("crossover requires first and second graphs")
            child = crossover_graphs(
                ArchitectureGraph.model_validate(first),
                ArchitectureGraph.model_validate(second),
                operator=operator,  # type: ignore[arg-type]
                seed=seed,
            )
        else:
            raise ArchitectureValidationError(f"unknown mode {mode!r}")
    except (ArchitectureValidationError, ValueError) as exc:
        msg = getattr(exc, "message", str(exc))
        return {
            "result": {"error": {"message": msg}},
            "diagnostics": {"converged": False, "message": msg},
        }
    payload = child.model_dump(mode="json")
    return {
        "result": {
            "graph": payload,
            "fingerprint": child.fingerprint(),
            "operator": operator,
            "seed": seed,
        },
        "diagnostics": {"converged": True, "fingerprint": child.fingerprint()},
    }
