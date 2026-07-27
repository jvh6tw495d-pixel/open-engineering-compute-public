"""linear.residual_norms entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.linear.analysis.residual_norms`` — no LAPACK code is
reimplemented here.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.linear.analysis import residual_norms


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = residual_norms(inputs["r"])
    return {
        "result": {
            "l1": out["l1"],
            "l2": out["l2"],
            "linf": out["linf"],
            "n": out["n"],
            "backend": out["backend"],
            "converged": out["converged"],
        },
        "diagnostics": {
            "n": out["n"],
            "l1": out["l1"],
            "l2": out["l2"],
            "linf": out["linf"],
            "converged": out["converged"],
        },
    }