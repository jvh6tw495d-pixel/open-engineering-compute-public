"""Legacy skill ↔ physics parity stress harness (v2.6.2).

Compares side-by-side:
- battery.soc_step backend: kernel.soc_update vs physics.energy_based_soc_update
- energy.balance backend: kernel.energy_balance vs conservation-owner candidate

Strict numerical tolerance (atol 1e-9) and bit-identical output shape
(keys / types / nesting). Migration of skill thin-wraps is allowed only
while this harness stays green.
"""

from __future__ import annotations

from itertools import product
from typing import Any

import pytest

from oec.kernel.energy.metrics import energy_balance as kernel_energy_balance
from oec.kernel.energy.metrics import soc_update as kernel_soc_update
from oec.physics.conservation import evaluate_residual
from oec.physics.storage import energy_based_soc_update

ATOL = 1e-9


# ---------------------------------------------------------------------------
# Candidate backends (physics / conservation) — same public numeric contract
# ---------------------------------------------------------------------------


def conservation_energy_balance(
    energy_in: list[float],
    energy_out: list[float],
    *,
    storage_delta: float = 0.0,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Parity candidate for energy.balance via conservation residual owner.

    Maps the legacy absolute tolerance to the conservation policy with
    ``rtol=0`` so ``abs(residual) <= tolerance`` is preserved exactly.
    """
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


# ---------------------------------------------------------------------------
# Shape / numeric comparison helpers
# ---------------------------------------------------------------------------


def _assert_same_shape(left: Any, right: Any, path: str = "root") -> None:
    assert type(left) is type(right), f"{path}: type {type(left)} != {type(right)}"
    if isinstance(left, dict):
        assert set(left.keys()) == set(
            right.keys()
        ), f"{path}: keys {set(left.keys())} != {set(right.keys())}"
        for key in left:
            _assert_same_shape(left[key], right[key], f"{path}.{key}")
    elif isinstance(left, list):
        assert len(left) == len(right), f"{path}: len {len(left)} != {len(right)}"
        for i, (a, b) in enumerate(zip(left, right, strict=True)):
            _assert_same_shape(a, b, f"{path}[{i}]")


def _assert_numeric_equal(left: Any, right: Any, path: str = "root") -> None:
    if isinstance(left, dict):
        for key in left:
            _assert_numeric_equal(left[key], right[key], f"{path}.{key}")
    elif isinstance(left, list):
        for i, (a, b) in enumerate(zip(left, right, strict=True)):
            _assert_numeric_equal(a, b, f"{path}[{i}]")
    elif isinstance(left, bool):
        assert left is right, f"{path}: {left!r} is not {right!r}"
    elif isinstance(left, int | float):
        assert left == pytest.approx(
            right, abs=ATOL, rel=0.0
        ), f"{path}: {left!r} != {right!r} (atol={ATOL})"
    else:
        assert left == right, f"{path}: {left!r} != {right!r}"


def assert_parity(legacy: dict[str, Any], candidate: dict[str, Any]) -> None:
    _assert_same_shape(legacy, candidate)
    _assert_numeric_equal(legacy, candidate)


# ---------------------------------------------------------------------------
# Grids
# ---------------------------------------------------------------------------


def _soc_grid() -> list[dict[str, float]]:
    socs = [0.0, 0.25, 0.5, 0.75, 1.0]
    powers = [-50.0, -10.0, -1.0, 0.0, 1.0, 10.0, 50.0, 100.0]
    dts = [0.0, 0.25, 0.5, 1.0, 2.0]
    capacities = [50.0, 100.0, 1000.0]
    etas = [
        (1.0, 1.0),
        (0.98, 0.95),
        (0.9, 0.85),
        (0.5, 1.0),
        (1.0, 0.5),
    ]
    cases: list[dict[str, float]] = []
    for soc, power, dt, cap, (eta_c, eta_d) in product(socs, powers, dts, capacities, etas):
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


def _balance_grid() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = [
        {
            "energy_in": [100.0],
            "energy_out": [100.0],
            "storage_delta": 0.0,
            "tolerance": 1e-6,
        },
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
        {
            "energy_in": [1.0],
            "energy_out": [0.0],
            "storage_delta": 0.0,
            "tolerance": 1e-6,
        },
        {
            "energy_in": [0.0],
            "energy_out": [1.0],
            "storage_delta": 0.0,
            "tolerance": 1e-6,
        },
        {
            "energy_in": [1e6, 2e6],
            "energy_out": [2.5e6],
            "storage_delta": 5e5,
            "tolerance": 1e-3,
        },
        {
            "energy_in": [1e-9],
            "energy_out": [1e-9],
            "storage_delta": 0.0,
            "tolerance": 1e-12,
        },
        {
            "energy_in": [100.0],
            "energy_out": [90.0],
            "storage_delta": 5.0,  # residual = 5 → unbalanced at tol 1e-6
            "tolerance": 1e-6,
        },
        {
            "energy_in": [100.0],
            "energy_out": [90.0],
            "storage_delta": 5.0,  # residual = 5 → balanced at tol 10
            "tolerance": 10.0,
        },
        {
            "energy_in": [],
            "energy_out": [0.0],
            "storage_delta": 0.0,
            "tolerance": 1e-6,
        },
        {
            "energy_in": [0.0],
            "energy_out": [],
            "storage_delta": 0.0,
            "tolerance": 1e-6,
        },
        {
            "energy_in": [10.0, -2.0],  # signed terms allowed at metric layer
            "energy_out": [3.0, 4.0],
            "storage_delta": 1.0,
            "tolerance": 1e-6,
        },
    ]
    # Cartesian product of a few simple magnitudes
    for a, b, s, tol in product(
        [0.0, 1.0, 100.0],
        [0.0, 1.0, 50.0],
        [-10.0, 0.0, 10.0],
        [1e-9, 1e-6, 1.0],
    ):
        cases.append(
            {
                "energy_in": [a],
                "energy_out": [b],
                "storage_delta": s,
                "tolerance": tol,
            }
        )
    return cases


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    _soc_grid(),
    ids=lambda k: (
        f"soc={k['soc']}_P={k['power']}_dt={k['dt_hours']}_C={k['capacity']}"
        f"_ηc={k['efficiency_charge']}_ηd={k['efficiency_discharge']}"
    ),
)
def test_soc_step_kernel_vs_physics_parity(kwargs: dict[str, float]) -> None:
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


@pytest.mark.parametrize(
    "case",
    _balance_grid(),
    ids=lambda c: (
        f"in={c['energy_in']}_out={c['energy_out']}_ds={c['storage_delta']}_tol={c['tolerance']}"
    ),
)
def test_energy_balance_kernel_vs_conservation_parity(case: dict[str, Any]) -> None:
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


def test_both_backends_reject_empty_energy_lists() -> None:
    with pytest.raises(ValueError, match="cannot both be empty"):
        kernel_energy_balance([], [])
    with pytest.raises(ValueError, match="cannot both be empty"):
        conservation_energy_balance([], [])


def _load_skill_module(relative: str, name: str) -> Any:
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "skills" / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_soc_skill_shape_matches_kernel_envelope() -> None:
    """Skill public envelope: result.{soc,delta_soc,clipped,energy_delta{value,unit}}."""
    mod = _load_skill_module("battery/soc_step/implementation.py", "soc_step_impl")
    out = mod.execute(
        {
            "soc": 0.5,
            "power": {"value": 10.0, "unit": "W"},
            "dt_hours": {"value": 1.0, "unit": "h"},
            "capacity": {"value": 100.0, "unit": "Wh"},
            "efficiency_charge": 1.0,
            "efficiency_discharge": 1.0,
        }
    )

    kernel = kernel_soc_update(0.5, 10.0, 1.0, 100.0)
    assert set(out.keys()) == {"result", "diagnostics"}
    result = out["result"]
    assert set(result.keys()) == {"soc", "delta_soc", "clipped", "energy_delta"}
    assert result["soc"] == pytest.approx(kernel["soc"], abs=ATOL)
    assert result["delta_soc"] == pytest.approx(kernel["delta_soc"], abs=ATOL)
    assert result["clipped"] is kernel["clipped"]
    assert result["energy_delta"]["unit"] == "Wh"
    assert result["energy_delta"]["value"] == pytest.approx(kernel["energy_delta"], abs=ATOL)


def test_balance_skill_shape_matches_kernel_envelope() -> None:
    mod = _load_skill_module("energy/balance/implementation.py", "energy_balance_impl")

    out = mod.execute(
        {
            "energy_in": [{"value": 100.0, "unit": "Wh"}],
            "energy_out": [{"value": 40.0, "unit": "Wh"}],
            "storage_delta": {"value": 60.0, "unit": "Wh"},
            "tolerance": {"value": 1e-6, "unit": "Wh"},
        }
    )
    kernel = kernel_energy_balance([100.0], [40.0], storage_delta=60.0, tolerance=1e-6)
    assert set(out.keys()) == {"result", "diagnostics"}
    result = out["result"]
    expected_keys = {"total_in", "total_out", "storage_delta", "residual", "balanced", "tolerance"}
    assert set(result.keys()) == expected_keys
    for field in ("total_in", "total_out", "storage_delta", "residual", "tolerance"):
        assert result[field]["unit"] == "Wh"
        assert result[field]["value"] == pytest.approx(kernel[field], abs=ATOL)
    assert result["balanced"] is kernel["balanced"]
