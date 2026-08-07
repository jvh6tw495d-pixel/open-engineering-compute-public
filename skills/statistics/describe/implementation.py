from __future__ import annotations

from typing import Any

from oec.kernel.statistics.describe import describe


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = describe(inputs["values"])
    return {"result": out, "diagnostics": {}}
