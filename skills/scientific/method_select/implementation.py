"""scientific.method_select — X3 evidence-oriented routing."""

from __future__ import annotations

from typing import Any

from oec.kernel.scientific.method_select import select_method


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    result = select_method(
        problem_class=str(inputs["problem_class"]),
        budget_seconds=inputs.get("budget_seconds"),
        prefer_backend=inputs.get("prefer_backend"),
        run_probe_benchmark=bool(inputs.get("run_probe_benchmark", False)),
        seed=int(inputs.get("seed", 42)),
    )
    selected = result.get("selected")
    return {
        "result": result,
        "diagnostics": {
            "converged": None,
            "message": result.get("message", "ok"),
            "backend": "registry",
            "selected_skill": selected["skill_id"] if selected else None,
            "n_available": len(result.get("available_candidates") or []),
        },
    }
