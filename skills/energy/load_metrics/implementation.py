from __future__ import annotations

from typing import Any

from oec.kernel.energy.metrics import load_metrics


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = load_metrics(inputs["power_values"])
    return {"result": out, "diagnostics": {}}
