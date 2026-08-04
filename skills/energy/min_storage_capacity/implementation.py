"""energy.min_storage_capacity — multiperiod min capacity via optimization.lp.

Formulates a grid-zero energy storage sizing LP (OPS v0.1) and **composes**
the ``optimization.lp`` skill entrypoint. Does **not** import HiGHS directly
and does **not** embed a heuristic loop in physics.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.ops.schema import OPS_SCHEMA_VERSION

_ENERGY_UNIT = "Wh"
_TIME_UNIT = "h"

# Soft upper bound for charge/discharge/curtail when capacity is free.
# Large enough for textbook horizons; not a physical power limit.
_FLOW_UB = 1.0e9


def _energy(raw: dict[str, Any]) -> float:
    return QuantityValue(**raw).convert_to(_ENERGY_UNIT).value


def _hours(raw: dict[str, Any]) -> float:
    return QuantityValue(**raw).convert_to(_TIME_UNIT).value


def _load_optimization_lp_execute() -> Any:
    """Load ``skills/optimization/lp/implementation.execute`` by path composition."""
    skills_root = Path(__file__).resolve().parents[2]
    lp_dir = skills_root / "optimization" / "lp"
    module_file = lp_dir / "implementation.py"
    if not module_file.is_file():
        raise RuntimeError(f"composition target missing: {module_file}")
    unique = f"oec_composed_optimization_lp_{abs(hash(str(lp_dir)))}"
    spec = importlib.util.spec_from_file_location(unique, module_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load composition target: {module_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute


def build_min_storage_ops(
    load: list[float],
    pv: list[float],
    *,
    eta_charge: float,
    eta_discharge: float,
    soc_min: float,
    soc_max: float,
    initial_soc: float,
    curtailment_allowed: bool,
) -> dict[str, Any]:
    """Build OPS v0.1 for grid-zero min energy capacity (public textbook form).

    Variables
    ---------
    capacity : energy capacity (objective)
    c{t}, d{t} : charge / discharge energy at the bus
    g{t} : grid import (fixed to 0 — grid-zero sizing)
    e{t} : stored energy after period t
    u{t} : optional PV curtailment

    Dynamics (energy-based)::

        e[t] = e[t-1] + η_c · c[t] − d[t] / η_d
        soc_min · capacity ≤ e[t] ≤ soc_max · capacity
        e before t=0 is initial_soc · capacity

    Balance (grid-zero)::

        load[t] + u[t] = pv[t] + g[t] + d[t] − c[t]
        with g[t] = 0 and u[t] = 0 when curtailment is disallowed.
    """
    n = len(load)
    if n == 0:
        raise ValueError("load series must be non-empty")
    if len(pv) != n:
        raise ValueError(f"pv length ({len(pv)}) must match load length ({n})")
    if not 0.0 < eta_charge <= 1.0:
        raise ValueError("eta_charge must be in (0, 1]")
    if not 0.0 < eta_discharge <= 1.0:
        raise ValueError("eta_discharge must be in (0, 1]")
    if not 0.0 <= soc_min <= soc_max <= 1.0:
        raise ValueError("require 0 <= soc_min <= soc_max <= 1")
    if not 0.0 <= initial_soc <= 1.0:
        raise ValueError("initial_soc must be in [0, 1]")

    inv_eta_d = 1.0 / float(eta_discharge)
    eta_c = float(eta_charge)

    variables: list[dict[str, Any]] = [
        {
            "name": "capacity",
            "kind": "continuous",
            "lower": 0.0,
            "upper": None,
            "objective_coeff": 1.0,
        }
    ]
    constraints: list[dict[str, Any]] = []

    for t in range(n):
        variables.append({"name": f"c{t}", "kind": "continuous", "lower": 0.0, "upper": _FLOW_UB})
        variables.append({"name": f"d{t}", "kind": "continuous", "lower": 0.0, "upper": _FLOW_UB})
        # Grid import forced to 0 (grid-zero sizing contract).
        variables.append({"name": f"g{t}", "kind": "continuous", "lower": 0.0, "upper": 0.0})
        variables.append({"name": f"e{t}", "kind": "continuous", "lower": 0.0, "upper": None})
        if curtailment_allowed:
            variables.append(
                {"name": f"u{t}", "kind": "continuous", "lower": 0.0, "upper": _FLOW_UB}
            )

        # Balance: g + d - c [- u] = load - pv  (u only when allowed)
        # load + u = pv + g + d - c  =>  g + d - c - u = load - pv
        rhs_bal = float(load[t]) - float(pv[t])
        bal_coeffs: dict[str, float] = {f"g{t}": 1.0, f"d{t}": 1.0, f"c{t}": -1.0}
        if curtailment_allowed:
            bal_coeffs[f"u{t}"] = -1.0
        constraints.append(
            {
                "name": f"bal{t}",
                "coeffs": bal_coeffs,
                "sense": "=",
                "rhs": rhs_bal,
            }
        )

        # SOC energy dynamics
        if t == 0:
            # e0 - η_c c0 + (1/η_d) d0 - initial_soc * capacity = 0
            constraints.append(
                {
                    "name": "soc0",
                    "coeffs": {
                        "e0": 1.0,
                        "c0": -eta_c,
                        "d0": inv_eta_d,
                        "capacity": -float(initial_soc),
                    },
                    "sense": "=",
                    "rhs": 0.0,
                }
            )
        else:
            # e_t - e_{t-1} - η_c c_t + (1/η_d) d_t = 0
            constraints.append(
                {
                    "name": f"soc{t}",
                    "coeffs": {
                        f"e{t}": 1.0,
                        f"e{t - 1}": -1.0,
                        f"c{t}": -eta_c,
                        f"d{t}": inv_eta_d,
                    },
                    "sense": "=",
                    "rhs": 0.0,
                }
            )

        # soc_min * capacity <= e[t]  =>  e[t] - soc_min * capacity >= 0
        constraints.append(
            {
                "name": f"e_ge_soc_min{t}",
                "coeffs": {f"e{t}": 1.0, "capacity": -float(soc_min)},
                "sense": ">=",
                "rhs": 0.0,
            }
        )
        # e[t] <= soc_max * capacity  =>  e[t] - soc_max * capacity <= 0
        constraints.append(
            {
                "name": f"e_le_soc_max{t}",
                "coeffs": {f"e{t}": 1.0, "capacity": -float(soc_max)},
                "sense": "<=",
                "rhs": 0.0,
            }
        )

    return {
        "ops_version": OPS_SCHEMA_VERSION,
        "problem_class": "lp",
        "sense": "min",
        "name": "min_storage_capacity_grid_zero",
        "assumptions": [
            f"T={n} periods, grid_import fixed to 0 (grid-zero sizing)",
            f"eta_charge={eta_c}, eta_discharge={eta_discharge}",
            f"soc_min={soc_min}, soc_max={soc_max}, initial_soc={initial_soc}",
            f"curtailment_allowed={curtailment_allowed}",
            "Linear relaxation: simultaneous charge+discharge not forbidden",
            "Public energy-only sizing — not commercial BTM dispatch",
        ],
        "variables": variables,
        "constraints": constraints,
        "objective": {"coeffs": {"capacity": 1.0}},
    }


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    load = [_energy(v) for v in inputs["load"]]
    pv = [_energy(v) for v in inputs["pv"]]
    eta_c = float(inputs["eta_charge"])
    eta_d = float(inputs["eta_discharge"])
    soc_min = float(inputs["soc_min"])
    soc_max = float(inputs["soc_max"])
    initial_soc = float(inputs["initial_soc"])
    horizon = _hours(inputs["horizon_hours"])
    curtailment_allowed = bool(inputs.get("curtailment_allowed", False))
    n = len(load)

    ops = build_min_storage_ops(
        load,
        pv,
        eta_charge=eta_c,
        eta_discharge=eta_d,
        soc_min=soc_min,
        soc_max=soc_max,
        initial_soc=initial_soc,
        curtailment_allowed=curtailment_allowed,
    )

    lp_execute = _load_optimization_lp_execute()
    lp_out = lp_execute({"ops": ops})
    lp_result = lp_out["result"]
    diagnostics = dict(lp_out.get("diagnostics") or {})

    primal = dict(lp_result.get("primal") or {})
    dual = dict(lp_result.get("dual") or {})
    status = str(lp_result.get("solver_status", "other"))
    obj = lp_result.get("objective_value")

    capacity_val = float(obj) if obj is not None and status == "optimal" else None
    if capacity_val is None and "capacity" in primal:
        capacity_val = float(primal["capacity"])

    charge = [float(primal.get(f"c{t}", 0.0)) for t in range(n)]
    discharge = [float(primal.get(f"d{t}", 0.0)) for t in range(n)]
    grid_import = [float(primal.get(f"g{t}", 0.0)) for t in range(n)]
    stored = [float(primal.get(f"e{t}", 0.0)) for t in range(n)]
    soc = (
        [e / capacity_val for e in stored]
        if capacity_val is not None and capacity_val > 0
        else [0.0] * n
    )
    trajectory: dict[str, Any] = {
        "charge": charge,
        "discharge": discharge,
        "grid_import": grid_import,
        "stored_energy": stored,
        "soc": soc,
    }
    if curtailment_allowed:
        trajectory["curtailment"] = [float(primal.get(f"u{t}", 0.0)) for t in range(n)]

    result: dict[str, Any] = {
        "optimal_capacity": {"value": capacity_val, "unit": _ENERGY_UNIT},
        "trajectory": trajectory,
        "solver_status": status,
        "backend": str(lp_result.get("backend", "highs")),
        "feasibility_issues": list(lp_result.get("feasibility_issues") or []),
        "horizon_hours": {"value": float(horizon), "unit": _TIME_UNIT},
        "n": n,
    }
    if dual:
        result["dual_values"] = {str(k): float(v) for k, v in dual.items()}

    diagnostics["composed_skill"] = "optimization.lp"
    diagnostics["ops_name"] = "min_storage_capacity_grid_zero"
    return {"result": result, "diagnostics": diagnostics}
