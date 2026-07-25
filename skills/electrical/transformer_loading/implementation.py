"""electrical.transformer_loading entrypoint.

Closed-form loading ratio for a transformer nameplate rating. Units
already canonical (ADR 0016). Apparent power is reported in VA
(dimensionally identical to the W canonical input).
"""

from __future__ import annotations

from typing import Any


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    rated_s = float(inputs["rated_apparent_power"]["value"])
    load_type: str = inputs["load_type"]
    threshold = float(inputs.get("overload_threshold_percent", 100.0))

    if load_type == "apparent_power":
        load_s = float(inputs["load_apparent_power"]["value"])
    else:
        load_current = float(inputs["load_current"]["value"])
        rated_current = float(inputs["rated_current"]["value"])
        load_s = rated_s * (load_current / rated_current)

    loading_percent = 100.0 * load_s / rated_s
    headroom = rated_s - load_s
    overload_warning = loading_percent >= threshold

    return {
        "result": {
            "load_apparent_power": {"value": load_s, "unit": "VA"},
            "loading_percent": loading_percent,
            "headroom": {"value": headroom, "unit": "VA"},
            "overload_warning": overload_warning,
            "overload_threshold_percent": threshold,
        },
        "diagnostics": {},
    }
