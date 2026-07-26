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
