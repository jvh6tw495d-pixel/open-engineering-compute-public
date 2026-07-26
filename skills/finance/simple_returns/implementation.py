from __future__ import annotations

from typing import Any

from oec.kernel.finance.metrics import simple_returns


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = simple_returns(inputs["prices"])
    return {"result": out, "diagnostics": {"n_returns": out["n_returns"]}}
