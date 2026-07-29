"""Phase A3: every registered skill returns the same ExecutionResult top-level keys."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oec.execution.factory import build_validators
from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry

_SKILLS = Path("skills")

# Minimal valid inputs per skill (canonical units where needed).
_FIXTURES: dict[str, dict[str, Any]] = {
    "mathematics.solve_root": {"expression": "x**2 - 2", "bracket": [0, 2]},
    "mathematics.interpolate": {
        "x": [0.0, 1.0, 2.0],
        "y": [0.0, 1.0, 4.0],
        "query_points": [0.5],
        "method": "linear",
    },
    "mathematics.integrate": {
        "expression": "x",
        "bounds": [0.0, 1.0],
    },
    "mathematics.differentiate": {
        "expression": "x**2",
        "at": 3.0,
    },
    "mathematics.optimize_scalar": {
        "expression": "(x-2)**2",
        "bounds": [0.0, 5.0],
    },
    "mathematics.optimize_constrained": {
        "expression": "x**2 + y**2",
        "variables": ["x", "y"],
        "x0": [1.0, 1.0],
    },
    "mathematics.curve_fit": {
        "x": [0.0, 1.0, 2.0],
        "y": [1.0, 2.0, 3.0],
        "model": "a + b*x",
        "parameter_names": ["a", "b"],
        "initial_guess": [0.0, 1.0],
    },
    "electrical.three_phase_power": {
        "voltage_line_to_line": {"value": 380.0, "unit": "V"},
        "current_line": {"value": 10.0, "unit": "A"},
        "power_factor": 0.8,
    },
    "electrical.current_from_power": {
        "power": {"value": 1000.0, "unit": "W"},
        "power_type": "active",
        "voltage": {"value": 230.0, "unit": "V"},
        "phase_count": 1,
        "power_factor": 0.9,
    },
    "electrical.voltage_drop": {
        "load_type": "current",
        "phase_count": 1,
        "voltage_reference": {"value": 230.0, "unit": "V"},
        "power_factor": 0.8,
        "length": {"value": 50.0, "unit": "m"},
        "current": {"value": 10.0, "unit": "A"},
        "resistance_per_length": {"value": 0.001, "unit": "ohm/m"},
    },
    "electrical.power_factor_correction": {
        "active_power": {"value": 10000.0, "unit": "W"},
        "existing_power_factor": 0.8,
        "desired_power_factor": 0.95,
        "voltage": {"value": 380.0, "unit": "V"},
        "frequency": {"value": 50.0, "unit": "Hz"},
        "phase_count": 3,
        "connection": "delta",
    },
    "electrical.transformer_loading": {
        "rated_apparent_power": {"value": 1000.0, "unit": "kVA"},
        "load_type": "apparent_power",
        "load_apparent_power": {"value": 800.0, "unit": "kVA"},
    },
    "electrical.per_unit_conversion": {
        "operation": "to_per_unit",
        "quantity_kind": "impedance",
        "phase_count": 3,
        "voltage_base": {"value": 13800.0, "unit": "V"},
        "power_base": {"value": 100.0, "unit": "MVA"},
        "value": {"value": 0.5, "unit": "ohm"},
    },
    "optimization.lp": {
        "ops": {
            "ops_version": "0.1.0",
            "problem_class": "lp",
            "sense": "min",
            "variables": [
                {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
                {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
            ],
            "constraints": [
                {
                    "name": "cover",
                    "coeffs": {"x": 1, "y": 1},
                    "sense": ">=",
                    "rhs": 1,
                }
            ],
            "objective": {"coeffs": {"x": 1, "y": 1}},
        }
    },
    "optimization.milp": {
        "ops": {
            "ops_version": "0.1.0",
            "problem_class": "milp",
            "sense": "max",
            "variables": [
                {"name": "a", "kind": "binary"},
                {"name": "b", "kind": "binary"},
            ],
            "constraints": [
                {
                    "name": "weight",
                    "coeffs": {"a": 2, "b": 1},
                    "sense": "<=",
                    "rhs": 2,
                }
            ],
            "objective": {"coeffs": {"a": 3, "b": 2}},
        }
    },
    # Phase D
    "timeseries.resample": {
        "timestamps": [
            "2024-01-01T00:00:00",
            "2024-01-01T00:30:00",
            "2024-01-01T01:00:00",
            "2024-01-01T01:30:00",
        ],
        "values": [1.0, 3.0, 2.0, 4.0],
        "freq": "1h",
        "how": "mean",
    },
    "timeseries.align": {
        "timestamps_a": ["2024-01-01T00:00:00", "2024-01-01T01:00:00"],
        "values_a": [1.0, 2.0],
        "timestamps_b": ["2024-01-01T00:00:00", "2024-01-01T02:00:00"],
        "values_b": [10.0, 30.0],
        "how": "inner",
    },
    "timeseries.fill_missing": {
        "timestamps": [
            "2024-01-01T00:00:00",
            "2024-01-01T01:00:00",
            "2024-01-01T02:00:00",
        ],
        "values": [1.0, None, 3.0],
        "method": "ffill",
    },
    "timeseries.power_to_energy": {
        "timestamps": ["2024-01-01T00:00:00", "2024-01-01T01:00:00"],
        "power": [1.0, 1.0],
        "power_unit": "kW",
        "energy_unit": "kWh",
    },
    # S11 quality
    "timeseries.detect_outliers": {
        "timestamps": [
            "2024-01-01T00:00:00",
            "2024-01-01T01:00:00",
            "2024-01-01T02:00:00",
            "2024-01-01T03:00:00",
            "2024-01-01T04:00:00",
        ],
        "values": [1.0, 2.0, 100.0, 2.5, 1.5],
        "method": "iqr",
        "threshold": 1.5,
    },
    "timeseries.clip": {
        "timestamps": [
            "2024-01-01T00:00:00",
            "2024-01-01T01:00:00",
            "2024-01-01T02:00:00",
        ],
        "values": [1.0, 50.0, 2.0],
        "lower": 0.0,
        "upper": 10.0,
    },
    "timeseries.normalize": {
        "timestamps": [
            "2024-01-01T00:00:00",
            "2024-01-01T01:00:00",
            "2024-01-01T02:00:00",
        ],
        "values": [0.0, 5.0, 10.0],
        "method": "minmax",
    },
    "timeseries.rolling": {
        "timestamps": [
            "2024-01-01T00:00:00",
            "2024-01-01T01:00:00",
            "2024-01-01T02:00:00",
            "2024-01-01T03:00:00",
        ],
        "values": [1.0, 2.0, 3.0, 4.0],
        "window": 2,
        "how": "mean",
    },
    # Phase E + S13
    "linear.solve_system": {"A": [[2.0, 0.0], [0.0, 2.0]], "b": [2.0, 4.0]},
    "linear.matrix_properties": {"A": [[2.0, 0.0], [0.0, 3.0]]},
    "numerical.root_system": {
        "variables": ["x", "y"],
        "equations": ["x + y - 3", "x - y - 1"],
        "x0": [0.0, 0.0],
    },
    "numerical.ode_ivp": {
        "state_names": ["y"],
        "dydt_expressions": ["-y"],
        "t_span": [0.0, 1.0],
        "y0": [1.0],
        "t_eval": [0.0, 0.5, 1.0],
    },
    "statistics.describe": {"values": [1.0, 2.0, 3.0, 4.0]},
    # S15
    "statistics.monte_carlo": {
        "expression": "x**2",
        "n_samples": 2000,
        "low": 0.0,
        "high": 1.0,
        "seed": 42,
    },
    # Phase F
    "energy.balance": {
        "energy_in": [{"value": 10.0, "unit": "Wh"}, {"value": 5.0, "unit": "Wh"}],
        "energy_out": [{"value": 12.0, "unit": "Wh"}],
        "storage_delta": {"value": 3.0, "unit": "Wh"},
    },
    "battery.soc_step": {
        "soc": 0.5,
        "power": {"value": 10.0, "unit": "W"},
        "dt_hours": {"value": 1.0, "unit": "h"},
        "capacity": {"value": 100.0, "unit": "Wh"},
    },
    "energy.load_metrics": {
        "power_values": [
            {"value": 10.0, "unit": "W"},
            {"value": 20.0, "unit": "W"},
            {"value": 15.0, "unit": "W"},
            {"value": 5.0, "unit": "W"},
        ]
    },
    # S7′
    "optimization.check_feasibility": {
        "ops": {
            "ops_version": "0.1.0",
            "problem_class": "lp",
            "sense": "min",
            "variables": [
                {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
                {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
            ],
            "constraints": [
                {
                    "name": "cover",
                    "coeffs": {"x": 1, "y": 1},
                    "sense": ">=",
                    "rhs": 1,
                }
            ],
            "objective": {"coeffs": {"x": 1, "y": 1}},
        }
    },
    "optimization.scenario_batch": {
        "ops": {
            "ops_version": "0.1.0",
            "problem_class": "lp",
            "sense": "min",
            "variables": [
                {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
                {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
            ],
            "constraints": [
                {
                    "name": "cover",
                    "coeffs": {"x": 1, "y": 1},
                    "sense": ">=",
                    "rhs": 1,
                }
            ],
            "objective": {"coeffs": {"x": 1, "y": 1}},
        },
        "path": "constraint:cover.rhs",
        "values": [0.5, 1.0, 1.5],
    },
    # S10
    "timeseries.timegrid": {
        "start": "2024-01-01T00:00:00",
        "end": "2024-01-01T03:00:00",
        "freq": "1h",
    },
    # S19
    "finance.simple_returns": {"prices": [100.0, 110.0, 105.0, 120.0]},
    "finance.max_drawdown": {"prices": [100.0, 120.0, 90.0, 110.0]},
    "finance.var_historical": {
        "returns": [-0.02, -0.01, 0.0, 0.01, 0.02, -0.05, 0.03, -0.015],
        "confidence": 0.95,
    },
    # S23–S26
    "optimization.qp": {
        "Q": [[2.0, 0.0], [0.0, 2.0]],
        "c": [-2.0, -4.0],
        "bounds": [[0.0, None], [0.0, None]],
        "x0": [0.0, 0.0],
        "sense": "min",
    },
    "optimization.nlp": {
        "expression": "(1-x)**2 + 100*(y-x**2)**2",
        "variables": ["x", "y"],
        "x0": [0.0, 0.0],
        "bounds": [[-2.0, 2.0], [-2.0, 2.0]],
        "method": "SLSQP",
    },
    "mathematics.solve_ir": {
        "ir": {
            "ir_version": "0.1.0",
            "symbols": [{"name": "x"}],
            "unknowns": ["x"],
            "initial_guess": {"x": 3.0},
            "equations": [
                {
                    "lhs": {
                        "kind": "binary",
                        "op": "**",
                        "left": {"kind": "symbol", "name": "x"},
                        "right": {"kind": "number", "value": 2},
                    },
                    "rhs": {"kind": "number", "value": 4},
                }
            ],
        }
    },
    "optimization.multiobjective": {
        "ops": {
            "ops_version": "0.1.0",
            "problem_class": "lp",
            "sense": "min",
            "variables": [
                {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
                {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
            ],
            "constraints": [
                {
                    "name": "cover",
                    "coeffs": {"x": 1, "y": 1},
                    "sense": ">=",
                    "rhs": 1,
                }
            ],
            "objective": {"coeffs": {"x": 1, "y": 1}},
        },
        "objectives": [{"x": 1, "y": 1}, {"x": 2, "y": 0}],
        "weights": [0.5, 0.5],
    },
    # v2.3 Wave A — applied math expansion (11 new skills)
    "linear.eig": {"A": [[1.0, 0.0], [0.0, 2.0]]},
    "linear.least_squares": {
        "A": [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]],
        "b": [1.0, 3.0, 5.0],
    },
    "linear.residual_norms": {"r": [3.0, 4.0]},
    "statistics.regression": {
        "x": [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0], [1.0, 3.0]],
        "y": [1.0, 3.0, 5.0, 7.0],
    },
    "statistics.intervals": {
        "samples": [1.0, 2.0, 3.0, 4.0, 5.0],
        "confidence_level": 0.95,
        # 0.2.0: Student-t default; population_standard_deviation optional
    },
    "statistics.bootstrap": {
        "samples": [1.0, 2.0, 3.0, 4.0, 5.0],
        "statistic": "mean",
        "confidence_level": 0.95,
        "n_resamples": 200,
        "seed": 0,
    },
    "timeseries.lag_features": {"values": [1.0, 2.0, 3.0, 4.0], "lags": [1]},
    "timeseries.forecast_simple": {
        "series": [1.0, 2.0, 3.0, 4.0],
        "steps_ahead": 2,
        "method": "naive",
    },
    "timeseries.backtest": {
        "series": [1.0, 2.0, 3.0, 4.0],
        "steps_ahead": 1,
        "method": "naive",
    },
    "timeseries.autocorrelation": {
        "series": [1.0, -1.0, 1.0, -1.0],
        "nlags": 3,
    },
    "timeseries.pacf": {
        "series": [1.0, -1.0, 1.0, -1.0],
        "nlags": 3,
    },
    "timeseries.ar_yule_walker": {
        "series": [1.0, -1.0, 1.0, -1.0],
        "order": 1,
    },
    "timeseries.levinson_durbin": {
        "autocorrelation": [1.0, 0.5, 0.25, 0.125],
    },
    "optimization.lp_diagnostics": {
        "ops": {
            "ops_version": "0.1.0",
            "problem_class": "lp",
            "sense": "min",
            "variables": [
                {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
                {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
            ],
            "constraints": [{"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}],
            "objective": {"coeffs": {"x": 1, "y": 1}},
        }
    },
    "optimization.infeasibility_explain": {
        "ops": {
            "ops_version": "0.1.0",
            "problem_class": "lp",
            "sense": "min",
            "variables": [{"name": "x", "kind": "continuous", "lower": 0, "upper": 1}],
            "constraints": [{"name": "use", "coeffs": {"x": 1}, "sense": ">=", "rhs": 0}],
            "objective": {"coeffs": {"x": 1}},
        }
    },
    # v2.3 Wave B
    "uncertainty.lhs": {
        "n_samples": 4,
        "bounds": [[0.0, 1.0], [0.0, 1.0]],
        "seed": 0,
    },
    "uncertainty.morris": {
        "bounds": [[0.0, 1.0], [0.0, 1.0]],
        "coeffs": [1.0, 0.0],
        "n_trajectories": 5,
        "seed": 0,
    },
    "uncertainty.propagate_linear": {
        "jacobian": [1.0, 1.0],
        "covariance": [[1.0, 0.0], [0.0, 1.0]],
    },
    "dynamics.state_space_simulate": {
        "A": [[1.0]],
        "B": [[1.0]],
        "C": [[1.0]],
        "D": [[0.0]],
        "u": [[1.0], [1.0]],
        "x0": [0.0],
        "dt": 1.0,
        "time_base": "discrete",
    },
    "dynamics.stability_margins": {"A": [[-1.0]], "time_base": "continuous"},
    "control.pid_discrete": {
        "reference": [1.0, 1.0],
        "measurement": [0.0, 0.0],
        "kp": 1.0,
        "ki": 0.0,
        "kd": 0.0,
        "dt": 0.1,
    },
    "control.kalman_filter": {
        "A": [[1.0]],
        "C": [[1.0]],
        "Q": [[0.0]],
        "R": [[1.0]],
        "z": [[1.0]],
        "x0": [0.0],
        "P0": [[1.0]],
    },
    # v2.3 Wave C
    "optimization.pareto_lp": {
        "ops": {
            "ops_version": "0.1.0",
            "problem_class": "lp",
            "sense": "min",
            "variables": [
                {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
                {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
            ],
            "constraints": [{"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}],
            "objective": {"coeffs": {"x": 1, "y": 1}},
        },
        "objective_a": {"x": 1, "y": 2},
        "objective_b": {"x": 2, "y": 1},
        "n_points": 3,
    },
    "optimization.cvar_lp": {
        "decision_vars": [{"name": "x", "lower": 0, "upper": 5}],
        "loss_scenarios": [{"x": 1.0}, {"x": 2.0}],
        "alpha": 0.5,
        "structural_constraints": [{"name": "lb", "coeffs": {"x": 1}, "sense": ">=", "rhs": 1}],
    },
    "optimization.robust_lp": {
        "ops": {
            "ops_version": "0.1.0",
            "problem_class": "lp",
            "sense": "min",
            "variables": [
                {"name": "x", "kind": "continuous", "lower": 0, "upper": 10},
                {"name": "y", "kind": "continuous", "lower": 0, "upper": 10},
            ],
            "constraints": [{"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}],
            "objective": {"coeffs": {"x": 1, "y": 1}},
        },
        "rhs_uncertainty": {"cover": 0.1},
    },
}

_REQUIRED_KEYS = frozenset(
    {
        "run_id",
        "status",
        "skill",
        "method",
        "inputs",
        "normalized_inputs",
        "result",
        "assumptions",
        "conventions",
        "diagnostics",
        "validation",
        "warnings",
        "provenance",
        "started_at",
        "completed_at",
        "duration_ms",
    }
)


def test_all_registered_skills_share_execution_result_contract() -> None:
    registry = SkillRegistry()
    report = registry.register_all(_SKILLS)
    assert not report.failures, report.failures
    manifests = registry.list_skills()
    assert len(manifests) >= 12

    try:
        import highspy  # noqa: F401
    except ImportError:
        highspy = None  # type: ignore[assignment]

    for manifest in manifests:
        skill_id = manifest.id
        if skill_id.startswith("optimization.") and highspy is None:
            continue
        assert skill_id in _FIXTURES, f"missing contract fixture for {skill_id}"
        skill = registry.get_skill(skill_id)
        iv, rv = build_validators(skill)
        service = ExecutionService(registry, input_validators=iv, result_validators=rv)
        result = service.execute(ExecutionRequest(skill_id=skill_id, inputs=_FIXTURES[skill_id]))
        dumped = result.model_dump(mode="json")
        missing = _REQUIRED_KEYS - dumped.keys()
        assert not missing, f"{skill_id} missing keys {missing}"
        assert result.status in ExecutionStatus
        assert result.skill.id == skill_id
        assert result.method.id
        assert "input_hash" in result.provenance
        assert "backends" in result.provenance
        assert isinstance(result.provenance["backends"], list)
        # Usable scientific outcome for these golden fixtures
        assert result.status not in {
            ExecutionStatus.INVALID,
            ExecutionStatus.FAILED,
        }, f"{skill_id} -> {result.status}: {result.diagnostics}"
