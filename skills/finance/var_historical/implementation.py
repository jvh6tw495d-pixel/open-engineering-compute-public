from __future__ import annotations

from typing import Any

from oec.kernel.finance.metrics import historical_var


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = historical_var(
        inputs["returns"],
        confidence=float(inputs.get("confidence", 0.95)),
    )
    return {"result": out, "diagnostics": {"var": out["var"], "confidence": out["confidence"]}}
