"""Phase A3: every registered skill returns the same ExecutionResult top-level keys."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oec.execution.factory import build_validators
from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry

_SKILLS = Path("skills")

# Committed examples shared by the OEC 3.6 neural training/search skills.
_NEURAL_TRAINING_EXAMPLE: dict[str, Any] = {
    "x": [[float(value)] for value in range(12)],
    "y": [float(2 * value + 1) for value in range(12)],
    "seed": 0,
    "max_evaluations": 6,
    "inner_epochs": 10,
    "epochs": 20,
}
_NEURAL_GRADIENT_EXAMPLE: dict[str, Any] = {
    "x": [[float(value)] for value in range(12)],
    "y": [float(2 * value + 1) for value in range(12)],
    "seed": 0,
    "epochs": 20,
    "device": "cpu",
}
_NEURAL_NEUROEVOLUTION_EXAMPLE: dict[str, Any] = {
    "x": [[float(value)] for value in range(12)],
    "y": [float(2 * value + 1) for value in range(12)],
    "seed": 0,
    "max_evaluations": 6,
    "device": "cpu",
}

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
    "battery.soc_trajectory": {
        "initial_soc": 0.5,
        "powers": [
            {"value": 10.0, "unit": "W"},
            {"value": -20.0, "unit": "W"},
        ],
        "dt_hours": {"value": 1.0, "unit": "h"},
        "capacity": {"value": 100.0, "unit": "Wh"},
        "eta_charge": 1.0,
        "eta_discharge": 1.0,
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
    "chemistry.arrhenius": {
        "pre_exponential": 42.0,
        "activation_energy_j_per_mol": 0.0,
        "temperature_k": 300.0,
    },
    "chemistry.batch_kinetics": {
        "a_mol": 1.0,
        "b_mol": 0.0,
        "k": 0.1,
        "volume_m3": 1.0,
        "dt_s": 1.0,
    },
    "chemistry.equilibrium": {"a_mol": 1.0, "b_mol": 1.0, "kc": 1.0, "volume_m3": 1.0},
    "chemistry.fick_flux": {
        "concentration_a_mol_m3": 10.0,
        "concentration_b_mol_m3": 0.0,
        "distance_m": 0.1,
        "diffusivity_m2_s": 1e-05,
    },
    "chemistry.nernst": {
        "e0_v": 1.23,
        "n_electrons": 2,
        "reaction_quotient": 1.0,
        "temperature_k": 298.15,
    },
    "chemistry.reaction_extent": {
        "h2_mol": 4.0,
        "o2_mol": 1.0,
        "h2o_mol": 0.0,
        "extent_mol": 1.0,
    },
    "electrical.dc_power_flow": {
        "lines": [
            {"from_bus": "A", "to_bus": "B", "susceptance": 10.0},
            {"from_bus": "B", "to_bus": "C", "susceptance": 10.0},
            {"from_bus": "A", "to_bus": "C", "susceptance": 10.0},
        ],
        "injections": {"A": -1.0, "B": 0.4, "C": 0.6},
        "slack_bus": "A",
    },
    "electrical.harmonics_thd": {
        "fundamental": {"value": 100.0, "unit": "V"},
        "harmonics": [{"value": 3.0, "unit": "V"}, {"value": 4.0, "unit": "V"}],
    },
    "energy.grid_zero_feasibility": {
        "load": [{"value": 2.0, "unit": "W"}, {"value": 1.0, "unit": "W"}],
        "pv": [{"value": 0.5, "unit": "W"}, {"value": 1.5, "unit": "W"}],
        "storage_charge": [{"value": 0.0, "unit": "W"}, {"value": 0.5, "unit": "W"}],
        "storage_discharge": [{"value": 1.5, "unit": "W"}, {"value": 0.0, "unit": "W"}],
        "grid_import": [{"value": 0.0, "unit": "W"}, {"value": 0.0, "unit": "W"}],
        "dt_hours": {"value": 1.0, "unit": "h"},
    },
    "energy.hybrid_balance": {
        "load": [{"value": 3.0, "unit": "W"}, {"value": 2.0, "unit": "W"}],
        "pv": [{"value": 0.0, "unit": "W"}, {"value": 3.0, "unit": "W"}],
        "grid_import": [{"value": 3.0, "unit": "W"}, {"value": -0.5, "unit": "W"}],
        "storage_charge": [{"value": 0.0, "unit": "W"}, {"value": 0.5, "unit": "W"}],
        "storage_discharge": [{"value": 0.0, "unit": "W"}, {"value": 0.0, "unit": "W"}],
        "dt_hours": {"value": 1.0, "unit": "h"},
    },
    "energy.min_storage_capacity": {
        "load": [{"value": 2.0, "unit": "Wh"}, {"value": 1.0, "unit": "Wh"}],
        "pv": [{"value": 0.0, "unit": "Wh"}, {"value": 0.0, "unit": "Wh"}],
        "eta_charge": 1.0,
        "eta_discharge": 1.0,
        "soc_min": 0.0,
        "soc_max": 1.0,
        "initial_soc": 1.0,
        "horizon_hours": {"value": 2.0, "unit": "h"},
        "curtailment_allowed": False,
    },
    "energy.pv_power": {
        "irradiance": {"value": 1000.0, "unit": "W / m ** 2"},
        "area": {"value": 10.0, "unit": "m ** 2"},
        "efficiency": 0.2,
    },
    "energy.service_metrics": {
        "load": [{"value": 10.0, "unit": "W"}, {"value": 20.0, "unit": "W"}],
        "pv": [{"value": 0.0, "unit": "W"}, {"value": 0.0, "unit": "W"}],
        "storage_discharge": [{"value": 10.0, "unit": "W"}, {"value": 20.0, "unit": "W"}],
        "grid_import": [{"value": 0.0, "unit": "W"}, {"value": 0.0, "unit": "W"}],
        "dt_hours": {"value": 1.0, "unit": "h"},
        "capacity": {"value": 50.0, "unit": "Wh"},
        "initial_soc": 1.0,
    },
    "fluids.bernoulli": {
        "pressure_upstream": {"value": 300000.0, "unit": "Pa"},
        "pressure_downstream": {"value": 280000.0, "unit": "Pa"},
        "velocity_upstream": {"value": 2.0, "unit": "m / s"},
        "velocity_downstream": {"value": 2.0, "unit": "m / s"},
        "elevation_upstream": {"value": 10.0, "unit": "m"},
        "elevation_downstream": {"value": 10.0, "unit": "m"},
        "density": {"value": 1000.0, "unit": "kg / m ** 3"},
        "friction_factor": 0.02,
        "length": {"value": 50.0, "unit": "m"},
        "diameter": {"value": 0.1, "unit": "m"},
    },
    "materials.linear_constitutive": {"material_id": "steel_astm_a36", "strain": 0.001},
    "mechanics.energy_1d": {
        "mass": {"value": 2.0, "unit": "kg"},
        "height_initial": {"value": 8.0, "unit": "m"},
        "height_final": {"value": 0.0, "unit": "m"},
        "velocity_initial": {"value": 0.0, "unit": "m / s"},
        "velocity_final": {"value": 12.526228482667877, "unit": "m / s"},
    },
    "multiphysics.solar_thermal_electrical": {
        "irradiance_w_m2": 1000.0,
        "area_m2": 1.0,
        "eta0": 0.2,
        "t_amb_c": 25.0,
        "ua_w_per_k": 50.0,
        "gamma_per_c": -0.004,
        "t_ref_c": 25.0,
    },
    "multiphysics.wire_i2r": {
        "current_a": 10.0,
        "r0_ohm": 0.1,
        "t_amb_k": 293.15,
        "ua_w_per_k": 1.0,
        "alpha_per_k": 0.0,
        "t0_k": 293.15,
    },
    "thermal.conduction_1d": {
        "conductivity": {"value": 1.5, "unit": "W / (m * K)"},
        "area": {"value": 0.5, "unit": "m ** 2"},
        "length": {"value": 0.02, "unit": "m"},
        "hot_temperature": {"value": 80.0, "unit": "degC"},
        "cold_temperature": {"value": 20.0, "unit": "degC"},
    },
    # --- OEC 3.4 neural/evolutionary/hybrid/scientific fixtures ---
    "evolutionary.benchmark": {
        "algorithms": ["differential_evolution", "genetic_algorithm"],
        "built_in": "sphere",
        "generations": 12,
        "mode": "single",
        "population": 16,
        "seeds": [0, 1],
        "variables": [
            {"lower": -2.0, "name": "x1", "upper": 2.0},
            {"lower": -2.0, "name": "x2", "upper": 2.0},
        ],
    },
    "evolutionary.blackbox_optimize": {
        "budget": 100,
        "built_in": "sphere",
        "n_var": 2,
        "optimizer": "OnePlusOne",
        "seed": 0,
    },
    "evolutionary.cma_es": {
        "built_in": "sphere",
        "generations": 30,
        "population": 20,
        "seed": 0,
        "variables": [
            {"lower": -5.0, "name": "x1", "upper": 5.0},
            {"lower": -5.0, "name": "x2", "upper": 5.0},
        ],
    },
    "evolutionary.custom_ga": {"built_in": "sphere", "generations": 15, "n_var": 2, "seed": 0},
    "evolutionary.differential_evolution": {
        "built_in": "sphere",
        "generations": 30,
        "population": 20,
        "seed": 0,
        "variables": [
            {"lower": -5.0, "name": "x1", "upper": 5.0},
            {"lower": -5.0, "name": "x2", "upper": 5.0},
        ],
    },
    "evolutionary.evolution_strategy": {
        "built_in": "sphere",
        "generations": 20,
        "n_var": 2,
        "seed": 0,
    },
    "evolutionary.genetic_algorithm": {
        "built_in": "sphere",
        "generations": 30,
        "population": 20,
        "seed": 0,
        "variables": [
            {"lower": -5.0, "name": "x1", "upper": 5.0},
            {"lower": -5.0, "name": "x2", "upper": 5.0},
        ],
    },
    "evolutionary.genetic_programming": {
        "generations": 15,
        "population": 40,
        "seed": 0,
        "target": "poly2",
    },
    "evolutionary.moead": {
        "built_in": "zdt1",
        "generations": 20,
        "population": 30,
        "seed": 0,
        "variables": [
            {"lower": 0.0, "name": "x0", "upper": 1.0},
            {"lower": 0.0, "name": "x1", "upper": 1.0},
            {"lower": 0.0, "name": "x2", "upper": 1.0},
            {"lower": 0.0, "name": "x3", "upper": 1.0},
            {"lower": 0.0, "name": "x4", "upper": 1.0},
        ],
    },
    "evolutionary.nsga2": {
        "built_in": "zdt1",
        "generations": 20,
        "population": 30,
        "seed": 0,
        "variables": [
            {"lower": 0.0, "name": "x0", "upper": 1.0},
            {"lower": 0.0, "name": "x1", "upper": 1.0},
            {"lower": 0.0, "name": "x2", "upper": 1.0},
            {"lower": 0.0, "name": "x3", "upper": 1.0},
            {"lower": 0.0, "name": "x4", "upper": 1.0},
        ],
    },
    "evolutionary.nsga3": {
        "built_in": "zdt1",
        "generations": 20,
        "population": 30,
        "seed": 0,
        "variables": [
            {"lower": 0.0, "name": "x0", "upper": 1.0},
            {"lower": 0.0, "name": "x1", "upper": 1.0},
            {"lower": 0.0, "name": "x2", "upper": 1.0},
            {"lower": 0.0, "name": "x3", "upper": 1.0},
            {"lower": 0.0, "name": "x4", "upper": 1.0},
        ],
    },
    "evolutionary.optimize_single": {
        "algorithm": "differential_evolution",
        "built_in": "sphere",
        "generations": 30,
        "population": 20,
        "seed": 0,
        "variables": [
            {"lower": -5.0, "name": "x1", "upper": 5.0},
            {"lower": -5.0, "name": "x2", "upper": 5.0},
        ],
    },
    "evolutionary.optimizer_portfolio": {
        "budget": 50,
        "built_in": "sphere",
        "optimizers": ["OnePlusOne", "RandomSearch"],
        "seed": 0,
    },
    "evolutionary.pareto_search": {
        "built_in": "zdt1",
        "generations": 20,
        "population": 30,
        "seed": 0,
        "variables": [
            {"lower": 0.0, "name": "x0", "upper": 1.0},
            {"lower": 0.0, "name": "x1", "upper": 1.0},
            {"lower": 0.0, "name": "x2", "upper": 1.0},
            {"lower": 0.0, "name": "x3", "upper": 1.0},
            {"lower": 0.0, "name": "x4", "upper": 1.0},
        ],
    },
    "evolutionary.pso": {
        "built_in": "sphere",
        "generations": 30,
        "population": 20,
        "seed": 0,
        "variables": [
            {"lower": -5.0, "name": "x1", "upper": 5.0},
            {"lower": -5.0, "name": "x2", "upper": 5.0},
        ],
    },
    "hybrid.evo_hyperparams": {
        "budget": 4,
        "epochs": 15,
        "seed": 0,
        "x": [[0], [1], [2], [3], [4], [5], [6], [7]],
        "y": [1, 3, 5, 7, 9, 11, 13, 15],
    },
    "hybrid.surrogate_optimize": {
        "built_in": "sphere",
        "device": "cpu",
        "evo_budget": 60,
        "n_train": 50,
        "n_var": 2,
        "seed": 0,
        "surrogate_epochs": 30,
    },
    "neural.autoencoder.basic": {
        "epochs": 20,
        "latent_dim": 2,
        "seed": 0,
        "x": [[0, 1, 0], [1, 0, 1], [0.5, 0.5, 0.5], [1, 1, 0], [0, 0, 1]],
    },
    "neural.autoencoder.denoising": {
        "epochs": 20,
        "noise_std": 0.1,
        "seed": 0,
        "x": [[0, 1, 0], [1, 0, 1], [0.5, 0.5, 0.5], [1, 1, 0], [0, 0, 1]],
    },
    "neural.cnn1d": {
        "epochs": 15,
        "seed": 0,
        "x": [
            [[0, 1], [1, 1], [2, 1]],
            [[1, 1], [2, 1], [3, 1]],
            [[2, 1], [3, 1], [4, 1]],
            [[3, 1], [4, 1], [5, 1]],
        ],
        "y": [1, 2, 3, 4],
    },
    "neural.distill": {
        "x": [[0.0], [1.0], [2.0]],
        "y": [0.0, 1.0, 2.0],
        "teacher_checkpoint": {
            "storage": "json_inline",
            "checkpoint_format_version": 1,
            "model_spec": {
                "architecture": "mlp",
                "input_dim": 1,
                "output_dim": 1,
                "hidden_dims": [1],
                "activation": "relu",
                "dropout": 0.0,
            },
            "state_dict": {
                "0.weight": [[1.0]],
                "0.bias": [0.0],
                "2.weight": [[1.0]],
                "2.bias": [0.0],
            },
            "sha256": "f1d0446468d5e77719bf50ed71d748c6291190450d918b9115640d176ca563a4",
        },
        "student_hidden_dims": [1],
        "epochs": 2,
        "batch_size": 3,
        "max_epochs": 2,
        "max_batch_size": 3,
        "seed": 0,
    },
    "neural.evaluate": {
        "checkpoint": {
            "architecture": "mlp",
            "model_spec": {
                "activation": "relu",
                "architecture": "mlp",
                "dropout": 0.0,
                "hidden_dims": [8],
                "input_dim": 1,
                "output_dim": 1,
            },
            "state_dict": {
                "0.bias": [
                    -0.08874404430389404,
                    2.5312869548797607,
                    -0.7727540135383606,
                    1.1047155857086182,
                    -0.9553484916687012,
                    -0.6622821092605591,
                    -0.41222310066223145,
                    2.2125442028045654,
                ],
                "0.weight": [
                    [-0.007486820220947266],
                    [1.7387737035751343],
                    [-0.38597673177719116],
                    [-0.5884883403778076],
                    [-0.3851543664932251],
                    [0.26815736293792725],
                    [-0.019813179969787598],
                    [2.1322555541992188],
                ],
                "2.bias": [1.64408540725708],
                "2.weight": [
                    [
                        0.13977208733558655,
                        2.016160726547241,
                        0.33456242084503174,
                        0.7555960416793823,
                        0.12841662764549255,
                        0.29358646273612976,
                        -0.07276135683059692,
                        1.9790631532669067,
                    ]
                ],
            },
            "task": "regression",
        },
        "device": "cpu",
        "normalize": {"mean": [5.5], "std": [3.452052529534663]},
        "task": "regression",
        "x": [[0.0], [1.0], [2.0], [3.0], [4.0], [5.0], [6.0], [7.0], [8.0], [9.0], [10.0], [11.0]],
        "y": [1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0, 17.0, 19.0, 21.0, 23.0],
    },
    "neural.gat": {
        "edge_index": [[0, 1, 2], [1, 2, 3]],
        "epochs": 20,
        "node_features": [[0, 1], [1, 1], [2, 1], [3, 1]],
        "seed": 0,
        "y": [0, 1, 2, 3],
    },
    "neural.gcn": {
        "edge_index": [[0, 1, 2], [1, 2, 3]],
        "epochs": 20,
        "node_features": [[0, 1], [1, 1], [2, 1], [3, 1]],
        "seed": 0,
        "y": [0, 1, 2, 3],
    },
    "neural.graphsage": {
        "edge_index": [[0, 1, 2], [1, 2, 3]],
        "epochs": 20,
        "node_features": [[0, 1], [1, 1], [2, 1], [3, 1]],
        "seed": 0,
        "y": [0, 1, 2, 3],
    },
    "neural.gru": {
        "epochs": 15,
        "seed": 0,
        "x": [
            [[0, 1], [1, 1], [2, 1]],
            [[1, 1], [2, 1], [3, 1]],
            [[2, 1], [3, 1], [4, 1]],
            [[3, 1], [4, 1], [5, 1]],
        ],
        "y": [1, 2, 3, 4],
    },
    "neural.lstm": {
        "epochs": 15,
        "seed": 0,
        "x": [
            [[0, 1], [1, 1], [2, 1]],
            [[1, 1], [2, 1], [3, 1]],
            [[2, 1], [3, 1], [4, 1]],
            [[3, 1], [4, 1], [5, 1]],
        ],
        "y": [1, 2, 3, 4],
    },
    "neural.mlp.classifier": {
        "device": "cpu",
        "epochs": 100,
        "hidden_dims": [16, 8],
        "n_classes": 2,
        "seed": 0,
        "x": [[0, 0], [0, 1], [1, 0], [1, 1], [0.1, 0.1], [0.9, 0.1], [0.1, 0.9], [0.9, 0.9]],
        "y": [0, 1, 1, 0, 0, 1, 1, 0],
    },
    "neural.mlp.regressor": {
        "device": "cpu",
        "epochs": 120,
        "hidden_dims": [16],
        "lr": 0.05,
        "seed": 0,
        "val_fraction": 0.25,
        "x": [[0.0], [1.0], [2.0], [3.0], [4.0], [5.0], [6.0], [7.0]],
        "y": [1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0],
    },
    "neural.predict": {
        "checkpoint": {
            "architecture": "mlp",
            "model_spec": {
                "activation": "relu",
                "architecture": "mlp",
                "dropout": 0.0,
                "hidden_dims": [8],
                "input_dim": 1,
                "output_dim": 1,
            },
            "state_dict": {
                "0.bias": [
                    -0.08874404430389404,
                    2.5312869548797607,
                    -0.7727540135383606,
                    1.1047155857086182,
                    -0.9553484916687012,
                    -0.6622821092605591,
                    -0.41222310066223145,
                    2.2125442028045654,
                ],
                "0.weight": [
                    [-0.007486820220947266],
                    [1.7387737035751343],
                    [-0.38597673177719116],
                    [-0.5884883403778076],
                    [-0.3851543664932251],
                    [0.26815736293792725],
                    [-0.019813179969787598],
                    [2.1322555541992188],
                ],
                "2.bias": [1.64408540725708],
                "2.weight": [
                    [
                        0.13977208733558655,
                        2.016160726547241,
                        0.33456242084503174,
                        0.7555960416793823,
                        0.12841662764549255,
                        0.29358646273612976,
                        -0.07276135683059692,
                        1.9790631532669067,
                    ]
                ],
            },
            "task": "regression",
        },
        "device": "cpu",
        "normalize": {"mean": [5.5], "std": [3.452052529534663]},
        "x": [[0.0], [1.0], [2.0]],
    },
    "neural.tcn": {
        "epochs": 15,
        "seed": 0,
        "x": [
            [[0, 1], [1, 1], [2, 1]],
            [[1, 1], [2, 1], [3, 1]],
            [[2, 1], [3, 1], [4, 1]],
            [[3, 1], [4, 1], [5, 1]],
        ],
        "y": [1, 2, 3, 4],
    },
    "neural.transformer.encoder": {
        "d_model": 16,
        "epochs": 12,
        "n_heads": 2,
        "seed": 0,
        "x": [[[0], [1], [2]], [[1], [2], [3]], [[2], [3], [4]], [[3], [4], [5]]],
        "y": [1, 2, 3, 4],
    },
    "neural.transformer.sequence_classifier": {
        "d_model": 16,
        "epochs": 20,
        "n_classes": 2,
        "n_heads": 2,
        "seed": 0,
        "task": "classification",
        "x": [[[0], [0], [0]], [[1], [1], [1]], [[0], [0], [1]], [[1], [1], [0]]],
        "y": [0, 1, 0, 1],
    },
    "neural.transformer.sequence_regressor": {
        "d_model": 16,
        "epochs": 12,
        "n_heads": 2,
        "seed": 0,
        "task": "regression",
        "x": [[[0], [1], [2]], [[1], [2], [3]], [[2], [3], [4]], [[3], [4], [5]]],
        "y": [1, 2, 3, 4],
    },
    # OEC 3.6 core/no-AI-extra additions; inputs mirror committed skill examples.
    "chemistry.hess_enthalpy": {
        "steps": [
            {"delta_h_j_per_mol": -285800.0, "coefficient": 1.0},
            {"delta_h_j_per_mol": -393500.0, "coefficient": -1.0},
        ]
    },
    "chemistry.vanthoff": {
        "k1": 1.0,
        "t1_k": 298.15,
        "t2_k": 310.15,
        "delta_h_j_per_mol": 50000.0,
    },
    "em.coulomb": {
        "charge1": {"value": 1e-06, "unit": "C"},
        "charge2": {"value": 1e-06, "unit": "C"},
        "separation": {"value": 0.1, "unit": "m"},
    },
    "em.parallel_plate_capacitor": {
        "area": {"value": 0.01, "unit": "m**2"},
        "gap": {"value": 0.001, "unit": "m"},
        "relative_permittivity": 1.0,
        "voltage": {"value": 10.0, "unit": "V"},
    },
    "foundation.capabilities": {},
    "foundation.embed": {
        "texts": ["hello engineering", "hello science"],
        "backend": "builtin_hash",
        "dim": 16,
        "seed": 0,
        "normalize": True,
    },
    "foundation.generate": {
        "prompt": "Hello",
        "model_id": "sshleifer/tiny-gpt2",
        "revision": "5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be",
        "max_new_tokens": 8,
        "temperature": 0,
        "seed": 0,
    },
    "foundation.peft_train": {
        "model_id": "sshleifer/tiny-gpt2",
        "revision": "5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be",
        "mode": "peft_lora",
        "texts": ["open engineering compute", "scientific skills for agents"],
        "r": 4,
        "lora_alpha": 8,
        "target_modules": ["c_attn"],
        "max_steps": 2,
        "max_seq_len": 32,
        "batch_size": 2,
        "seed": 0,
    },
    "foundation.vision_embed": {
        "images": [
            {
                "image_base64": (
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/"
                    "AAX+Av4N70a4AAAAAElFTkSuQmCC"
                )
            }
        ],
        "model_id": "openai/clip-vit-base-patch32",
        "revision": "5812e510083bb2d23fa43778a39ac065d205ed4d",
        "dim": 512,
        "normalize": True,
        "seed": 0,
    },
    "foundation.vlm_generate": {
        "prompt": "describe this image",
        "image": {
            "image_base64": (
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/"
                "AAX+Av4N70a4AAAAAElFTkSuQmCC"
            )
        },
        "model_id": "Salesforce/blip-image-captioning-base",
        "revision": "82a37760796d32b1411fe092ab5d4e227313294b",
        "max_new_tokens": 8,
        "temperature": 0,
        "seed": 0,
    },
    "mathematics.jacobian": {
        "expressions": ["x**2 + y", "x*y"],
        "variables": ["x", "y"],
        "at": [1.0, 2.0],
        "method": "central",
    },
    "mechanics.kinematics_1d": {
        "v0": {"value": 0.0, "unit": "m/s"},
        "a": {"value": 9.81, "unit": "m/s**2"},
        "t": {"value": 2.0, "unit": "s"},
        "x0": {"value": 0.0, "unit": "m"},
    },
    "neural.benchmark.training_strategy": dict(_NEURAL_TRAINING_EXAMPLE),
    "neural.search.architecture": dict(_NEURAL_TRAINING_EXAMPLE),
    "neural.search.features": dict(_NEURAL_TRAINING_EXAMPLE),
    "neural.search.hyperparameters": dict(_NEURAL_TRAINING_EXAMPLE),
    "neural.search.loss_weights": dict(_NEURAL_TRAINING_EXAMPLE),
    "neural.search.policy": dict(_NEURAL_TRAINING_EXAMPLE),
    "neural.training.gradient": dict(_NEURAL_GRADIENT_EXAMPLE),
    "neural.training.hybrid": dict(_NEURAL_TRAINING_EXAMPLE),
    "neural.training.neuroevolution": dict(_NEURAL_NEUROEVOLUTION_EXAMPLE),
    "neural.training.supervised": dict(_NEURAL_GRADIENT_EXAMPLE),
    "numerical.pde_1d_heat": {
        "mode": "steady",
        "length": 1.0,
        "n_intervals": 10,
        "left_value": 0.0,
        "right_value": 1.0,
        "source": 0.0,
    },
    "optics.snell": {"n1": 1.0, "n2": 1.5, "theta1_rad": 0.5},
    "optics.thin_lens": {"focal_length_m": 0.1, "object_distance_m": 0.2},
    "statistical_physics.ideal_gas": {
        "amount_mol": 1.0,
        "temperature": {"value": 273.15, "unit": "K"},
        "volume": {"value": 0.0224, "unit": "m**3"},
        "molar_mass_kg_per_mol": 0.028,
    },
    "statistics.distribution_eval": {
        "distribution": "norm",
        "operation": "pdf",
        "params": {"loc": 0.0, "scale": 1.0},
        "x": 0.0,
    },
    "statistics.hypothesis_test": {
        "test": "t_one_sample",
        "sample": [0.1, -0.2, 0.05, 0.0, -0.1, 0.15, -0.05, 0.02],
        "popmean": 0.0,
        "alternative": "two-sided",
    },
    "waves.phase_speed": {
        "frequency": {"value": 50.0, "unit": "Hz"},
        "wavelength": {"value": 6.0, "unit": "m"},
    },
    "scientific.method_select": {
        "budget_seconds": 30,
        "problem_class": "soo_box",
        "run_probe_benchmark": False,
        "seed": 0,
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
    try:
        import torch  # noqa: F401
    except ImportError:
        torch = None  # type: ignore[assignment]
    try:
        import pymoo  # noqa: F401
    except ImportError:
        pymoo = None  # type: ignore[assignment]
    try:
        import deap  # noqa: F401
    except ImportError:
        deap = None  # type: ignore[assignment]
    try:
        import nevergrad  # noqa: F401
    except ImportError:
        nevergrad = None  # type: ignore[assignment]

    for manifest in manifests:
        skill_id = manifest.id
        if skill_id.startswith("optimization.") and highspy is None:
            continue
        # OEC 3.4 optional extras — skip execute when backend not installed
        if skill_id.startswith(("neural.", "hybrid.")) and torch is None:
            continue
        if skill_id.startswith("hybrid.") and nevergrad is None:
            continue
        if skill_id.startswith("evolutionary."):
            # route by family
            if (
                skill_id
                in {
                    "evolutionary.genetic_programming",
                    "evolutionary.evolution_strategy",
                    "evolutionary.custom_ga",
                }
                and deap is None
            ):
                continue
            if (
                skill_id
                in {
                    "evolutionary.blackbox_optimize",
                    "evolutionary.optimizer_portfolio",
                }
                and nevergrad is None
            ):
                continue
            # remaining evolutionary default to pymoo (incl. benchmark multi/single)
            if (
                skill_id
                not in {
                    "evolutionary.genetic_programming",
                    "evolutionary.evolution_strategy",
                    "evolutionary.custom_ga",
                    "evolutionary.blackbox_optimize",
                    "evolutionary.optimizer_portfolio",
                }
                and pymoo is None
            ):
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
