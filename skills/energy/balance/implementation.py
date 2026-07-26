from __future__ import annotations

from typing import Any

from oec.kernel.energy.metrics import energy_balance


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = energy_balance(
        inputs.get("energy_in", []),
        inputs.get("energy_out", []),
        storage_delta=float(inputs.get("storage_delta", 0.0)),
        tolerance=float(inputs.get("tolerance", 1e-6)),
    )
    return {"result": out, "diagnostics": {}}
