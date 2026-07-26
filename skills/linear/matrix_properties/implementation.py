from __future__ import annotations

from typing import Any

from oec.kernel.linear.analysis import matrix_properties


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = matrix_properties(inputs["A"])
    return {
        "result": out,
        "diagnostics": {
            "rank": out["rank"],
            "condition_number": out["condition_number"],
        },
    }
