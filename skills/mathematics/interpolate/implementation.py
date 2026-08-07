"""mathematics.interpolate entrypoint.

Runs inside the sandboxed subprocess (ADR 0012) — imported only by
``oec.execution.runner``, never by the Skill Loader or the parent
process. Constructs a 1-D interpolant from discrete samples and
evaluates it at the requested query points; see ``skill.md``'s
"Official methodology" for why ``method`` is mandatory (no auto-select).

This method is closed-form construction + evaluation, not iterative —
``method.iterative: false`` in ``skill.yaml``, so ``diagnostics`` does
**not** report ``converged`` (ADR 0013: only iterative methods must).
"""

from __future__ import annotations

from typing import Any

from oec.kernel.computational.interpolation import interpolate


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    result = interpolate(inputs["x"], inputs["y"], inputs["query_points"], method=inputs["method"])
    return {
        "result": {"values": result.values},
        "diagnostics": {
            "method": result.diagnostics.method,
            "n_samples": len(inputs["x"]),
            "n_query": len(inputs["query_points"]),
        },
    }
