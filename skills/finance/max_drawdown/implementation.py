from __future__ import annotations

from typing import Any

from oec.kernel.finance.metrics import max_drawdown


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = max_drawdown(inputs["prices"])
    return {"result": out, "diagnostics": {"max_drawdown": out["max_drawdown"]}}
