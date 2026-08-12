from __future__ import annotations

from typing import Any

from oec.chemistry.thermochemistry import vanthoff_k2


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = vanthoff_k2(
        k1=float(inputs["k1"]),
        t1_k=float(inputs["t1_k"]),
        t2_k=float(inputs["t2_k"]),
        delta_h_j_per_mol=float(inputs["delta_h_j_per_mol"]),
    )
    assumptions = [a.text if hasattr(a, "text") else str(a) for a in out["assumptions"]]
    result = {k: v for k, v in out.items() if k != "assumptions"}
    result["assumptions"] = assumptions
    return {"result": result, "diagnostics": {}}
