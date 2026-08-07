"""v2.6.2 legacy skill ↔ physics parity stress harness.

Side-by-side comparison of:
  * battery.soc_step: kernel.soc_update vs physics.energy_based_soc_update
  * energy.balance: kernel.energy_balance vs conservation-owner candidate

Exit 0 only if every case passes shape + numeric parity (atol 1e-9).

Usage:
  .venv/Scripts/python.exe scripts/stress_parity_v262.py
  uv run python scripts/stress_parity_v262.py
"""

from __future__ import annotations

import sys
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oec.kernel.energy.metrics import energy_balance as kernel_energy_balance  # noqa: E402
from oec.kernel.energy.metrics import soc_update as kernel_soc_update  # noqa: E402
from oec.physics.conservation import evaluate_residual  # noqa: E402
from oec.physics.storage import energy_based_soc_update  # noqa: E402

ATOL = 1e-9


def conservation_energy_balance(
    energy_in: list[float],
    energy_out: list[float],
    *,
    storage_delta: float = 0.0,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    if len(energy_in) == 0 and len(energy_out) == 0:
        raise ValueError("energy_in and energy_out cannot both be empty")
    total_in = float(sum(energy_in))
    total_out = float(sum(energy_out))
    residual = total_in - total_out - float(storage_delta)
    check = evaluate_residual(
        residual,
        atol=float(tolerance),
        rtol=0.0,
        scale=1.0,
        unit="Wh",
    )
    return {
        "total_in": total_in,
        "total_out": total_out,
        "storage_delta": float(storage_delta),
        "residual": residual,
        "balanced": check.balanced,
        "tolerance": float(tolerance),
    }


def same_shape(left: Any, right: Any, path: str = "root") -> None:
    if type(left) is not type(right):
        raise AssertionError(f"{path}: type {type(left)} != {type(right)}")
    if isinstance(left, dict):
        if set(left.keys()) != set(right.keys()):
            raise AssertionError(f"{path}: keys {set(left.keys())} != {set(right.keys())}")
        for key in left:
            same_shape(left[key], right[key], f"{path}.{key}")
    elif isinstance(left, list):
        if len(left) != len(right):
            raise AssertionError(f"{path}: len {len(left)} != {len(right)}")
        for i, (a, b) in enumerate(zip(left, right, strict=True)):
            same_shape(a, b, f"{path}[{i}]")


def numeric_equal(left: Any, right: Any, path: str = "root") -> None:
    if isinstance(left, dict):
        for key in left:
            numeric_equal(left[key], right[key], f"{path}.{key}")
    elif isinstance(left, list):
        for i, (a, b) in enumerate(zip(left, right, strict=True)):
            numeric_equal(a, b, f"{path}[{i}]")
    elif isinstance(left, bool):
        if left is not right:
            raise AssertionError(f"{path}: {left!r} is not {right!r}")
    elif isinstance(left, int | float):
        if abs(float(left) - float(right)) > ATOL:
            raise AssertionError(f"{path}: {left!r} != {right!r} (atol={ATOL})")
    elif left != right:
        raise AssertionError(f"{path}: {left!r} != {right!r}")


def assert_parity(legacy: dict[str, Any], candidate: dict[str, Any]) -> None:
    same_shape(legacy, candidate)
    numeric_equal(legacy, candidate)


def soc_cases() -> list[dict[str, float]]:
    cases: list[dict[str, float]] = []
    for soc, power, dt, cap, (eta_c, eta_d) in product(
        [0.0, 0.25, 0.5, 0.75, 1.0],
        [-50.0, -10.0, -1.0, 0.0, 1.0, 10.0, 50.0, 100.0],
        [0.0, 0.25, 0.5, 1.0, 2.0],
        [50.0, 100.0, 1000.0],
        [(1.0, 1.0), (0.98, 0.95), (0.9, 0.85), (0.5, 1.0), (1.0, 0.5)],
    ):
        cases.append(
            {
                "soc": soc,
                "power": power,
                "dt_hours": dt,
                "capacity": cap,
                "efficiency_charge": eta_c,
                "efficiency_discharge": eta_d,
            }
        )
    return cases


def balance_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = [
        {"energy_in": [100.0], "energy_out": [100.0], "storage_delta": 0.0, "tolerance": 1e-6},
        {
            "energy_in": [50.0, 50.0],
            "energy_out": [30.0, 20.0],
            "storage_delta": 50.0,
            "tolerance": 1e-6,
        },
        {
            "energy_in": [10.0, 20.0, 30.0],
            "energy_out": [5.0, 5.0],
            "storage_delta": 50.0,
            "tolerance": 1e-9,
        },
        {"energy_in": [1.0], "energy_out": [0.0], "storage_delta": 0.0, "tolerance": 1e-6},
        {"energy_in": [0.0], "energy_out": [1.0], "storage_delta": 0.0, "tolerance": 1e-6},
        {"energy_in": [1e6, 2e6], "energy_out": [2.5e6], "storage_delta": 5e5, "tolerance": 1e-3},
        {"energy_in": [100.0], "energy_out": [90.0], "storage_delta": 5.0, "tolerance": 1e-6},
        {"energy_in": [100.0], "energy_out": [90.0], "storage_delta": 5.0, "tolerance": 10.0},
        {"energy_in": [], "energy_out": [0.0], "storage_delta": 0.0, "tolerance": 1e-6},
        {
            "energy_in": [10.0, -2.0],
            "energy_out": [3.0, 4.0],
            "storage_delta": 1.0,
            "tolerance": 1e-6,
        },
    ]
    for a, b, s, tol in product(
        [0.0, 1.0, 100.0],
        [0.0, 1.0, 50.0],
        [-10.0, 0.0, 10.0],
        [1e-9, 1e-6, 1.0],
    ):
        cases.append({"energy_in": [a], "energy_out": [b], "storage_delta": s, "tolerance": tol})
    return cases


def main() -> int:
    soc_ok = 0
    bal_ok = 0
    failures: list[str] = []

    for kwargs in soc_cases():
        try:
            legacy = kernel_soc_update(
                kwargs["soc"],
                kwargs["power"],
                kwargs["dt_hours"],
                kwargs["capacity"],
                efficiency_charge=kwargs["efficiency_charge"],
                efficiency_discharge=kwargs["efficiency_discharge"],
            )
            candidate = energy_based_soc_update(
                kwargs["soc"],
                kwargs["power"],
                kwargs["dt_hours"],
                kwargs["capacity"],
                efficiency_charge=kwargs["efficiency_charge"],
                efficiency_discharge=kwargs["efficiency_discharge"],
            )
            assert_parity(legacy, candidate)
            soc_ok += 1
        except Exception as exc:  # noqa: BLE001 — harness reports all failures
            failures.append(f"soc_step {kwargs}: {exc}")

    for case in balance_cases():
        try:
            legacy = kernel_energy_balance(
                case["energy_in"],
                case["energy_out"],
                storage_delta=case["storage_delta"],
                tolerance=case["tolerance"],
            )
            candidate = conservation_energy_balance(
                case["energy_in"],
                case["energy_out"],
                storage_delta=case["storage_delta"],
                tolerance=case["tolerance"],
            )
            assert_parity(legacy, candidate)
            bal_ok += 1
        except Exception as exc:  # noqa: BLE001
            failures.append(f"energy.balance {case}: {exc}")

    total_soc = len(soc_cases())
    total_bal = len(balance_cases())
    print(f"battery.soc_step  parity: {soc_ok}/{total_soc}")
    print(f"energy.balance    parity: {bal_ok}/{total_bal}")
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for line in failures[:20]:
            print(f"  - {line}")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")
        return 1
    print("ALL PARITY CASES PASS (atol=1e-9, shape bit-identical)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
