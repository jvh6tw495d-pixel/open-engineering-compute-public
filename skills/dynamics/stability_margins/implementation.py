"""dynamics.stability_margins entrypoint."""

from __future__ import annotations

from typing import Any

from oec.kernel.dynamics.stability import stability_margins


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = stability_margins(
        inputs["A"],
        time_base=str(inputs.get("time_base", "continuous")),
    )
    return {
        "result": out,
        "diagnostics": {
            "stable": out["stable"],
            "converged": None,
            "backend": out["backend"],
        },
    }
