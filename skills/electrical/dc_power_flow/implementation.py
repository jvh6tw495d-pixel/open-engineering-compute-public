"""electrical.dc_power_flow entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Thin adapter (skill-first,
per plan section 8): validates/adapts inputs into
``oec.physics.electrical`` domain objects and calls the canonical meshed
DC linear power-flow solver (D4). This module performs no physics
arithmetic of its own — every number in ``result`` comes from
``dc_power_flow``'s executed ``PhysicalLaw``/``ConservationLaw`` path.
"""

from __future__ import annotations

from typing import Any

from oec.physics.electrical import NetworkLine, dc_power_flow


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    lines = [
        NetworkLine(
            from_bus=line["from_bus"],
            to_bus=line["to_bus"],
            susceptance=float(line["susceptance"]),
        )
        for line in inputs["lines"]
    ]
    injections = {bus: float(value) for bus, value in inputs["injections"].items()}
    slack_bus: str = inputs["slack_bus"]

    tolerance_kwargs: dict[str, float] = {}
    if "atol" in inputs:
        tolerance_kwargs["atol"] = float(inputs["atol"])
    if "rtol" in inputs:
        tolerance_kwargs["rtol"] = float(inputs["rtol"])

    result = dc_power_flow(lines, injections, slack_bus=slack_bus, **tolerance_kwargs)

    return {"result": result.model_dump(mode="json"), "diagnostics": {}}
