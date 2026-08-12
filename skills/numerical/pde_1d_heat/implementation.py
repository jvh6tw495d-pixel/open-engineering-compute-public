"""numerical.pde_1d_heat — 1D FDM heat / Poisson foundation."""

from __future__ import annotations

from typing import Any

from oec.kernel.computational.pde import heat_1d


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = heat_1d(
        length=float(inputs.get("length", 1.0)),
        n_intervals=int(inputs.get("n_intervals", 20)),
        left_value=float(inputs.get("left_value", 0.0)),
        right_value=float(inputs.get("right_value", 0.0)),
        source=float(inputs.get("source", 0.0)),
        diffusivity=float(inputs.get("diffusivity", 1.0)),
        mode=str(inputs.get("mode", "steady")),
        n_steps=int(inputs.get("n_steps", 50)),
        dt=inputs.get("dt"),
        initial=inputs.get("initial"),
    )
    diagnostics = dict(out.pop("diagnostics"))
    return {"result": out, "diagnostics": diagnostics}
