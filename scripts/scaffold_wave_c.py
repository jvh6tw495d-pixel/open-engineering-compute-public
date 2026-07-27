"""Scaffold v2.3 Wave C optimization skills."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "optimization"


def w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.lstrip("\n"), encoding="utf-8", newline="\n")


def j(obj: object) -> str:
    return json.dumps(obj, indent=2) + "\n"


def yaml_block(skill_id: str, title: str, method: str) -> str:
    return f"""id: {skill_id}
version: 0.1.0
status: experimental
domain: optimization
title: {title}

entrypoint:
  module: implementation
  function: execute

schemas:
  input: input.schema.json
  output: output.schema.json

method:
  id: {method}
  version: 0.1.0
  iterative: true

execution:
  deterministic: true
  timeout_seconds: 60
  network_access: false
  filesystem_access: false

validation:
  schema: true
  dimensional: false
  mathematical: true
  physical: false
  numerical: true

references:
  - See references.md

tags:
  - v2.3
  - wave-c
  - optimization
"""


def fm(skill_id: str, title: str) -> str:
    return f"""---
id: {skill_id}
version: 0.1.0
status: experimental
domain: optimization
title: {title}
---
"""


def main() -> None:
    # pareto_lp
    b = ROOT / "pareto_lp"
    w(b / "skill.yaml", yaml_block("optimization.pareto_lp", "Bi-objective LP Pareto (weighted sum)", "pareto_weighted_sum"))
    w(
        b / "skill.md",
        fm("optimization.pareto_lp", "Bi-objective LP Pareto (weighted sum)")
        + """
# Purpose

Approximate a bi-objective Pareto set for a linear program by sweeping
convex combination weights of two linear objectives (Wave C v0).

# Official methodology

Method id: `pareto_weighted_sum`. For weights w on a uniform grid,
solve LP with combined objective `w c_a + (1-w) c_b`, then filter
non-dominated points under the base OPS sense.

# Applicability limits

- Continuous LP only (`problem_class=lp`).
- Two objectives; n_points >= 2.
- Requires HiGHS (`oec[optimization]`).

# Known limitations

- Weighted-sum only finds supported efficient points.
""",
    )
    w(b / "references.md", "# References\n\n1. Miettinen — multiobjective weighted sum.\n2. HiGHS LP.\n")
    w(
        b / "input.schema.json",
        j(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "ops": {"type": "object"},
                    "objective_a": {"type": "object", "additionalProperties": {"type": "number"}},
                    "objective_b": {"type": "object", "additionalProperties": {"type": "number"}},
                    "n_points": {"type": "integer", "minimum": 2},
                },
                "required": ["ops", "objective_a", "objective_b"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "output.schema.json",
        j(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "n_points_requested": {"type": "integer"},
                    "n_solved_optimal": {"type": "integer"},
                    "n_nondominated": {"type": "integer"},
                    "points": {"type": "array"},
                    "nondominated": {"type": "array"},
                    "sense": {"type": "string"},
                    "method": {"type": "string"},
                    "backend": {"type": "string"},
                    "converged": {"type": ["null", "boolean"]},
                },
                "required": [
                    "n_points_requested",
                    "n_solved_optimal",
                    "n_nondominated",
                    "points",
                    "nondominated",
                    "method",
                    "backend",
                ],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "implementation.py",
        '''"""optimization.pareto_lp entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.optimization.pareto import pareto_weighted_sum
from oec.ops.models import validate_ops


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    problem = validate_ops(inputs["ops"])
    if problem.problem_class != "lp":
        raise ValueError("optimization.pareto_lp requires ops.problem_class='lp'")
    out = pareto_weighted_sum(
        inputs["ops"],
        objective_a=dict(inputs["objective_a"]),
        objective_b=dict(inputs["objective_b"]),
        n_points=int(inputs.get("n_points", 11)),
    )
    return {
        "result": out,
        "diagnostics": {
            "n_nondominated": out["n_nondominated"],
            "n_solved_optimal": out["n_solved_optimal"],
            "converged": out["n_solved_optimal"] > 0,
            "backend": out["backend"],
        },
    }
''',
    )
    w(
        b / "validation.py",
        '''from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class ParetoLpValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        a = normalized_inputs.get("objective_a")
        b = normalized_inputs.get("objective_b")
        if not isinstance(a, dict) or not a or not isinstance(b, dict) or not b:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["objective_a and objective_b must be non-empty coeff maps"],
                )
            ]
        n = normalized_inputs.get("n_points", 11)
        if not isinstance(n, int) or n < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["n_points must be an integer >= 2"],
                )
            ]
        return []
''',
    )
    w(
        b / "examples" / "diet_biobj.json",
        j(
            {
                "description": "Bi-objective cover LP",
                "input": {
                    "ops": {
                        "ops_version": "0.1.0",
                        "problem_class": "lp",
                        "sense": "min",
                        "variables": [
                            {"name": "x", "kind": "continuous", "lower": 0, "upper": 10},
                            {"name": "y", "kind": "continuous", "lower": 0, "upper": 10},
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
                    "objective_a": {"x": 1, "y": 2},
                    "objective_b": {"x": 2, "y": 1},
                    "n_points": 5,
                },
            }
        ),
    )
    w(
        b / "tests" / "test_validation.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
V = load_skill_module(_SKILL_DIR, "validation").ParetoLpValidator()


def test_empty_obj() -> None:
    assert V.validate(
        None, {"objective_a": {}, "objective_b": {"x": 1}, "n_points": 5}
    )  # type: ignore[arg-type]
''',
    )
    w(
        b / "tests" / "test_golden.py",
        '''from __future__ import annotations

from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_OPS = {
    "ops_version": "0.1.0",
    "problem_class": "lp",
    "sense": "min",
    "variables": [
        {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
        {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
    ],
    "constraints": [
        {"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}
    ],
    "objective": {"coeffs": {"x": 1, "y": 1}},
}


def test_pareto_sweep_finds_optimal_points() -> None:
    out = implementation.execute(
        {
            "ops": _OPS,
            "objective_a": {"x": 1, "y": 2},
            "objective_b": {"x": 2, "y": 1},
            "n_points": 5,
        }
    )["result"]
    if out["points"] and "not installed" in str(out["points"][0].get("feasibility_issues", [])):
        pytest.skip("highspy not installed")
    assert out["n_points_requested"] == 5
    assert out["n_solved_optimal"] >= 1
    assert out["n_nondominated"] >= 1
''',
    )

    # cvar_lp
    b = ROOT / "cvar_lp"
    w(b / "skill.yaml", yaml_block("optimization.cvar_lp", "Linear CVaR (Rockafellar-Uryasev)", "rockafellar_uryasev_cvar"))
    w(
        b / "skill.md",
        fm("optimization.cvar_lp", "Linear CVaR (Rockafellar-Uryasev)")
        + """
# Purpose

Minimize Conditional Value-at-Risk (CVaR) of a linear loss over finite scenarios.

# Official methodology

Method id: `rockafellar_uryasev_cvar`. Auxiliary VaR level t and excesses
u_s >= loss_s(x) - t; objective t + 1/((1-α)S) Σ u_s.

# Applicability limits

- Finite discrete scenarios; continuous decisions.
- sense=min only in v0.
- Requires HiGHS.
""",
    )
    w(b / "references.md", "# References\n\n1. Rockafellar & Uryasev (2000).\n2. HiGHS LP.\n")
    w(
        b / "input.schema.json",
        j(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "decision_vars": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "lower": {"type": ["number", "null"]},
                                "upper": {"type": ["number", "null"]},
                            },
                            "required": ["name"],
                            "additionalProperties": False,
                        },
                    },
                    "loss_scenarios": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                        },
                    },
                    "alpha": {
                        "type": "number",
                        "exclusiveMinimum": 0,
                        "exclusiveMaximum": 1,
                    },
                    "structural_constraints": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "coeffs": {
                                    "type": "object",
                                    "additionalProperties": {"type": "number"},
                                },
                                "sense": {"type": "string", "enum": ["<=", ">=", "="]},
                                "rhs": {"type": "number"},
                            },
                            "required": ["coeffs", "sense", "rhs"],
                        },
                    },
                },
                "required": ["decision_vars", "loss_scenarios", "alpha"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "output.schema.json",
        j(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "solver_status": {"type": "string"},
                    "cvar": {"type": ["number", "null"]},
                    "var_level": {"type": ["number", "null"]},
                    "primal": {"type": "object"},
                    "decision": {"type": "object"},
                    "tail_excesses": {"type": "array", "items": {"type": "number"}},
                    "alpha": {"type": "number"},
                    "n_scenarios": {"type": "integer"},
                    "feasibility_issues": {"type": "array"},
                    "backend": {"type": "string"},
                    "method": {"type": "string"},
                    "converged": {"type": "boolean"},
                },
                "required": [
                    "solver_status",
                    "cvar",
                    "var_level",
                    "decision",
                    "alpha",
                    "n_scenarios",
                    "backend",
                    "method",
                    "converged",
                ],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "implementation.py",
        '''"""optimization.cvar_lp entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.optimization.cvar import cvar_lp


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = cvar_lp(
        decision_vars=list(inputs["decision_vars"]),
        loss_scenarios=list(inputs["loss_scenarios"]),
        alpha=float(inputs["alpha"]),
        structural_constraints=inputs.get("structural_constraints"),
    )
    return {
        "result": out,
        "diagnostics": {
            "converged": out["converged"],
            "alpha": out["alpha"],
            "backend": out["backend"],
            "message": out["solver_status"],
        },
    }
''',
    )
    w(
        b / "validation.py",
        '''from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class CvarLpValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        alpha = normalized_inputs.get("alpha")
        if not isinstance(alpha, (int, float)) or not (0 < float(alpha) < 1):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["alpha must be in (0,1)"],
                )
            ]
        scenarios = normalized_inputs.get("loss_scenarios")
        if not isinstance(scenarios, list) or not scenarios:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["loss_scenarios must be non-empty"],
                )
            ]
        return []
''',
    )
    w(
        b / "examples" / "two_scenario.json",
        j(
            {
                "description": "CVaR of loss=x under two scenarios",
                "input": {
                    "decision_vars": [{"name": "x", "lower": 0, "upper": 10}],
                    "loss_scenarios": [{"x": 1.0}, {"x": 2.0}],
                    "alpha": 0.5,
                    "structural_constraints": [
                        {"name": "floor", "coeffs": {"x": 1}, "sense": ">=", "rhs": 1}
                    ],
                },
            }
        ),
    )
    w(
        b / "tests" / "test_validation.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
V = load_skill_module(_SKILL_DIR, "validation").CvarLpValidator()


def test_bad_alpha() -> None:
    assert V.validate(
        None, {"alpha": 1.5, "loss_scenarios": [{"x": 1}]}
    )  # type: ignore[arg-type]
''',
    )
    w(
        b / "tests" / "test_golden.py",
        '''from __future__ import annotations

from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_cvar_runs_or_skips() -> None:
    out = implementation.execute(
        {
            "decision_vars": [{"name": "x", "lower": 0.0, "upper": 5.0}],
            "loss_scenarios": [{"x": 1.0}, {"x": 3.0}],
            "alpha": 0.5,
            "structural_constraints": [
                {"name": "lb", "coeffs": {"x": 1}, "sense": ">=", "rhs": 1.0}
            ],
        }
    )["result"]
    if out["solver_status"] == "other" and "not installed" in str(out["feasibility_issues"]):
        pytest.skip("highspy not installed")
    assert out["method"] == "rockafellar_uryasev"
    if out["converged"]:
        assert out["cvar"] is not None
        assert out["decision"]["x"] >= 1.0 - 1e-8
''',
    )

    # robust_lp
    b = ROOT / "robust_lp"
    w(b / "skill.yaml", yaml_block("optimization.robust_lp", "Robust LP (box RHS)", "box_rhs_worst_case"))
    w(
        b / "skill.md",
        fm("optimization.robust_lp", "Robust LP (box RHS)")
        + """
# Purpose

Solve a robust linear program under independent box uncertainty on selected
constraint right-hand sides (Wave C v0).

# Official methodology

Method id: `box_rhs_worst_case`. For radius δ on a constraint:
`<=` uses rhs−δ; `>=` uses rhs+δ. Equalities unsupported in v0.

# Applicability limits

- Continuous LP OPS document.
- Non-negative uncertainty radii.
- Requires HiGHS.
""",
    )
    w(b / "references.md", "# References\n\n1. Ben-Tal et al. — Robust Optimization.\n2. HiGHS LP.\n")
    w(
        b / "input.schema.json",
        j(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "ops": {"type": "object"},
                    "rhs_uncertainty": {
                        "type": "object",
                        "additionalProperties": {"type": "number", "minimum": 0},
                    },
                },
                "required": ["ops", "rhs_uncertainty"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "output.schema.json",
        j(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "solver_status": {"type": "string"},
                    "objective_value": {"type": ["number", "null"]},
                    "primal": {"type": "object"},
                    "dual": {"type": "object"},
                    "rhs_adjusted": {"type": "object"},
                    "feasibility_issues": {"type": "array"},
                    "backend": {"type": "string"},
                    "method": {"type": "string"},
                    "converged": {"type": "boolean"},
                },
                "required": [
                    "solver_status",
                    "objective_value",
                    "primal",
                    "rhs_adjusted",
                    "backend",
                    "method",
                    "converged",
                ],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "implementation.py",
        '''"""optimization.robust_lp entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.optimization.robust import robust_lp_box_rhs


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = robust_lp_box_rhs(
        inputs["ops"],
        rhs_uncertainty={
            str(k): float(v) for k, v in dict(inputs["rhs_uncertainty"]).items()
        },
    )
    return {
        "result": out,
        "diagnostics": {
            "converged": out["converged"],
            "backend": out["backend"],
            "message": out["solver_status"],
        },
    }
''',
    )
    w(
        b / "validation.py",
        '''from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class RobustLpValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        unc = normalized_inputs.get("rhs_uncertainty")
        if not isinstance(unc, dict) or not unc:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["rhs_uncertainty must be a non-empty map"],
                )
            ]
        if any(not isinstance(v, (int, float)) or float(v) < 0 for v in unc.values()):
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["radii must be non-negative numbers"],
                )
            ]
        return []
''',
    )
    w(
        b / "examples" / "cover_robust.json",
        j(
            {
                "description": "Min x+y s.t. robust cover",
                "input": {
                    "ops": {
                        "ops_version": "0.1.0",
                        "problem_class": "lp",
                        "sense": "min",
                        "variables": [
                            {"name": "x", "kind": "continuous", "lower": 0, "upper": 10},
                            {"name": "y", "kind": "continuous", "lower": 0, "upper": 10},
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
                    "rhs_uncertainty": {"cover": 0.2},
                },
            }
        ),
    )
    w(
        b / "tests" / "test_validation.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
V = load_skill_module(_SKILL_DIR, "validation").RobustLpValidator()


def test_empty_unc() -> None:
    assert V.validate(None, {"rhs_uncertainty": {}})  # type: ignore[arg-type]
''',
    )
    w(
        b / "tests" / "test_golden.py",
        '''from __future__ import annotations

from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_robust_rhs_tightens_and_solves() -> None:
    out = implementation.execute(
        {
            "ops": {
                "ops_version": "0.1.0",
                "problem_class": "lp",
                "sense": "min",
                "variables": [
                    {"name": "x", "kind": "continuous", "lower": 0, "upper": 10},
                    {"name": "y", "kind": "continuous", "lower": 0, "upper": 10},
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
            "rhs_uncertainty": {"cover": 0.2},
        }
    )["result"]
    if out["solver_status"] == "other" and "not installed" in str(
        out["feasibility_issues"]
    ):
        pytest.skip("highspy not installed")
    assert out["rhs_adjusted"]["cover"]["rhs_robust"] == pytest.approx(1.2)
    if out["converged"]:
        assert out["objective_value"] == pytest.approx(1.2)
''',
    )
    print("wave C skills written")


if __name__ == "__main__":
    main()
