"""linear.eig entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.linear.analysis.eigendecomposition`` — no SciPy/NumPy code is
reimplemented here.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.linear.analysis import eigendecomposition


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = eigendecomposition(inputs["A"])
    return {
        "result": {
            "eigenvalues_real": out["eigenvalues_real"],
            "eigenvalues_imag": out["eigenvalues_imag"],
            "eigenvector_columns": out["eigenvector_columns"],
            "eigenvector_norms": out["eigenvector_norms"],
            "n": out["n"],
            "backend": out["backend"],
            "converged": out["converged"],
        },
        "diagnostics": {
            "n": out["n"],
            "converged": out["converged"],
            "backend": out["backend"],
        },
    }