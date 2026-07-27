"""control.pid_discrete entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.control.pid import pid_discrete


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = pid_discrete(
        inputs["reference"],
        inputs["measurement"],
        kp=float(inputs["kp"]),
        ki=float(inputs["ki"]),
        kd=float(inputs["kd"]),
        dt=float(inputs["dt"]),
        u_min=inputs.get("u_min"),
        u_max=inputs.get("u_max"),
    )
    return {
        "result": out,
        "diagnostics": {
            "n": out["n"],
            "saturated_steps": out["saturated_steps"],
            "converged": None,
            "backend": out["backend"],
        },
    }
