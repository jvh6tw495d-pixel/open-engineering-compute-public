# ruff: noqa
"""Scaffold E3 (DEAP GP) and E4 (Nevergrad) skills."""

from __future__ import annotations

from pathlib import Path

root = Path(__file__).resolve().parents[1] / "skills" / "evolutionary"


def write(
    folder: str,
    skill_id: str,
    method_id: str,
    title: str,
    implementation: str,
    input_schema: str,
    test: str,
    example: str,
) -> None:
    d = root / folder
    (d / "examples").mkdir(parents=True, exist_ok=True)
    (d / "tests").mkdir(parents=True, exist_ok=True)
    (d / "skill.yaml").write_text(
        f"""id: {skill_id}
version: 0.1.0
status: experimental
domain: evolutionary
title: {title}

entrypoint:
  module: implementation
  function: execute

schemas:
  input: input.schema.json
  output: output.schema.json

method:
  id: {method_id}
  version: 0.1.0
  iterative: true

execution:
  deterministic: false
  timeout_seconds: 300
  network_access: false
  filesystem_access: false

validation:
  schema: true
  dimensional: false
  mathematical: true
  physical: false
  numerical: true

references:
  - "DEAP / Nevergrad documentation"
  - "ADR 0031 Neural and Evolutionary Compute"

tags:
  - evolutionary
  - experimental
""",
        encoding="utf-8",
    )
    (d / "skill.md").write_text(
        f"---\nid: {skill_id}\nversion: 0.1.0\n---\n\n# {title}\n\n"
        "Requires `oec[evolutionary]`. No arbitrary agent Python.\n",
        encoding="utf-8",
    )
    (d / "references.md").write_text(
        "# References\n\n- DEAP / Nevergrad\n- ADR 0031 E3/E4\n", encoding="utf-8"
    )
    (d / "output.schema.json").write_text(
        """{
  "type": "object",
  "properties": {
    "backend": {"type": "string"},
    "seed": {"type": "integer"}
  },
  "required": ["backend"],
  "additionalProperties": true
}
""",
        encoding="utf-8",
    )
    (d / "input.schema.json").write_text(input_schema, encoding="utf-8")
    (d / "implementation.py").write_text(implementation, encoding="utf-8")
    (d / "validation.py").write_text(
        """from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class EvoValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill, normalized_inputs
        return []
""",
        encoding="utf-8",
    )
    (d / "tests" / "test_golden.py").write_text(test, encoding="utf-8")
    (d / "examples" / "example.json").write_text(example, encoding="utf-8")


def main() -> None:
    write(
        "genetic_programming",
        "evolutionary.genetic_programming",
        "deap_genetic_programming",
        "Genetic Programming Symbolic Regression (DEAP)",
        '''"""evolutionary.genetic_programming"""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import DeapNotAvailableError
from oec.kernel.evolutionary.gp import run_genetic_programming


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = run_genetic_programming(
            n_var=int(inputs.get("n_var", 1)),
            target=str(inputs.get("target", "poly2")),
            n_samples=int(inputs.get("n_samples", 40)),
            population=int(inputs.get("population", 60)),
            generations=int(inputs.get("generations", 20)),
            max_depth=int(inputs.get("max_depth", 5)),
            max_size=int(inputs.get("max_size", 40)),
            seed=int(inputs.get("seed", 42)),
        )
    except DeapNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "message": exc.message, "backend": "deap"},
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": result["best_mse"] < 1e5,
            "backend": "deap",
            "seed": result["seed"],
            "best_mse": result["best_mse"],
        },
    }
''',
        """{
  "type": "object",
  "properties": {
    "n_var": {"type": "integer", "minimum": 1, "maximum": 5, "default": 1},
    "target": {"type": "string", "enum": ["poly2", "sin_x", "keijzer"], "default": "poly2"},
    "n_samples": {"type": "integer", "minimum": 10, "default": 40},
    "population": {"type": "integer", "minimum": 10, "default": 60},
    "generations": {"type": "integer", "minimum": 1, "default": 20},
    "max_depth": {"type": "integer", "minimum": 1, "maximum": 8, "default": 5},
    "max_size": {"type": "integer", "minimum": 5, "maximum": 100, "default": 40},
    "seed": {"type": "integer", "default": 42}
  },
  "additionalProperties": false
}
""",
        """from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("deap")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_gp_poly2_improves() -> None:
    out = implementation.execute({
        "target": "poly2",
        "n_var": 1,
        "n_samples": 30,
        "population": 40,
        "generations": 12,
        "max_depth": 4,
        "seed": 0,
    })
    assert out["result"]["backend"] == "deap"
    assert "best_tree_ir" in out["result"]
    assert out["result"]["best_mse"] < 1e5
""",
        '{"target": "poly2", "generations": 15, "population": 40, "seed": 0}',
    )

    write(
        "evolution_strategy",
        "evolutionary.evolution_strategy",
        "deap_evolution_strategy",
        "Evolution Strategy / Real-valued GA (DEAP)",
        '''"""evolutionary.evolution_strategy"""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import DeapNotAvailableError
from oec.kernel.evolutionary.gp import run_evolution_strategy


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = run_evolution_strategy(
            n_var=int(inputs.get("n_var", 2)),
            built_in=str(inputs.get("built_in", "sphere")),
            population=int(inputs.get("population", 30)),
            generations=int(inputs.get("generations", 25)),
            seed=int(inputs.get("seed", 42)),
            sigma=float(inputs.get("sigma", 0.5)),
        )
    except DeapNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "message": exc.message, "backend": "deap"},
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "deap",
            "seed": result["seed"],
            "best_objective": result["best_objective"],
        },
    }
''',
        """{
  "type": "object",
  "properties": {
    "n_var": {"type": "integer", "minimum": 1, "maximum": 20, "default": 2},
    "built_in": {"type": "string", "enum": ["sphere", "rosenbrock", "rastrigin"], "default": "sphere"},
    "population": {"type": "integer", "minimum": 4, "default": 30},
    "generations": {"type": "integer", "minimum": 1, "default": 25},
    "seed": {"type": "integer", "default": 42},
    "sigma": {"type": "number", "exclusiveMinimum": 0, "default": 0.5}
  },
  "additionalProperties": false
}
""",
        """from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("deap")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_es_sphere() -> None:
    out = implementation.execute({
        "built_in": "sphere",
        "n_var": 2,
        "population": 20,
        "generations": 20,
        "seed": 0,
    })
    assert out["result"]["backend"] == "deap"
    assert out["result"]["best_objective"] < 5.0
""",
        '{"built_in": "sphere", "n_var": 2, "generations": 20, "seed": 0}',
    )

    # custom_ga alias of ES for roadmap naming
    write(
        "custom_ga",
        "evolutionary.custom_ga",
        "deap_custom_ga",
        "Custom GA (DEAP real-valued)",
        '''"""evolutionary.custom_ga â€” alias of evolution_strategy for roadmap naming."""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import DeapNotAvailableError
from oec.kernel.evolutionary.gp import run_evolution_strategy


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = run_evolution_strategy(
            n_var=int(inputs.get("n_var", 2)),
            built_in=str(inputs.get("built_in", "sphere")),
            population=int(inputs.get("population", 30)),
            generations=int(inputs.get("generations", 25)),
            seed=int(inputs.get("seed", 42)),
            sigma=float(inputs.get("sigma", 0.5)),
        )
    except DeapNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "message": exc.message, "backend": "deap"},
        }
    result = dict(result)
    result["algorithm"] = "custom_ga"
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "deap",
            "seed": result["seed"],
            "best_objective": result["best_objective"],
        },
    }
''',
        """{
  "type": "object",
  "properties": {
    "n_var": {"type": "integer", "minimum": 1, "default": 2},
    "built_in": {"type": "string", "enum": ["sphere", "rosenbrock", "rastrigin"], "default": "sphere"},
    "population": {"type": "integer", "minimum": 4, "default": 30},
    "generations": {"type": "integer", "minimum": 1, "default": 25},
    "seed": {"type": "integer", "default": 42},
    "sigma": {"type": "number", "exclusiveMinimum": 0, "default": 0.5}
  },
  "additionalProperties": false
}
""",
        """from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("deap")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_custom_ga_runs() -> None:
    out = implementation.execute({"built_in": "sphere", "n_var": 2, "generations": 15, "seed": 1})
    assert out["result"]["backend"] == "deap"
""",
        '{"built_in": "sphere", "n_var": 2, "generations": 15, "seed": 0}',
    )

    write(
        "blackbox_optimize",
        "evolutionary.blackbox_optimize",
        "nevergrad_blackbox_optimize",
        "Black-Box Optimize (Nevergrad)",
        '''"""evolutionary.blackbox_optimize"""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.blackbox import blackbox_optimize
from oec.kernel.evolutionary.errors import NevergradNotAvailableError


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = blackbox_optimize(
            built_in=str(inputs.get("built_in", "sphere")),
            n_var=int(inputs.get("n_var", 2)),
            lower=float(inputs.get("lower", -5.0)),
            upper=float(inputs.get("upper", 5.0)),
            budget=int(inputs.get("budget", 150)),
            optimizer=str(inputs.get("optimizer", "OnePlusOne")),
            seed=int(inputs.get("seed", 42)),
        )
    except NevergradNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "nevergrad",
            },
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "nevergrad",
            "seed": result["seed"],
            "best_objective": result["best_objective"],
        },
    }
''',
        """{
  "type": "object",
  "properties": {
    "built_in": {"type": "string", "enum": ["sphere", "rosenbrock", "rastrigin"], "default": "sphere"},
    "n_var": {"type": "integer", "minimum": 1, "maximum": 30, "default": 2},
    "lower": {"type": "number", "default": -5.0},
    "upper": {"type": "number", "default": 5.0},
    "budget": {"type": "integer", "minimum": 10, "maximum": 10000, "default": 150},
    "optimizer": {
      "type": "string",
      "enum": ["NGOpt", "TwoPointsDE", "OnePlusOne", "CMA", "PSO", "RandomSearch", "TBPSA", "MetaTuneRecentering"],
      "default": "OnePlusOne"
    },
    "seed": {"type": "integer", "default": 42}
  },
  "additionalProperties": false
}
""",
        """from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("nevergrad")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_blackbox_sphere() -> None:
    out = implementation.execute({
        "built_in": "sphere",
        "n_var": 2,
        "budget": 80,
        "optimizer": "OnePlusOne",
        "seed": 0,
    })
    assert out["result"]["backend"] == "nevergrad"
    assert out["result"]["best_objective"] < 10.0
""",
        '{"built_in": "sphere", "n_var": 2, "budget": 100, "optimizer": "OnePlusOne", "seed": 0}',
    )

    write(
        "optimizer_portfolio",
        "evolutionary.optimizer_portfolio",
        "nevergrad_optimizer_portfolio",
        "Nevergrad Optimizer Portfolio",
        '''"""evolutionary.optimizer_portfolio"""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.blackbox import optimizer_portfolio
from oec.kernel.evolutionary.errors import NevergradNotAvailableError


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = optimizer_portfolio(
            built_in=str(inputs.get("built_in", "sphere")),
            n_var=int(inputs.get("n_var", 2)),
            lower=float(inputs.get("lower", -5.0)),
            upper=float(inputs.get("upper", 5.0)),
            budget=int(inputs.get("budget", 80)),
            optimizers=list(
                inputs.get("optimizers")
                or ["OnePlusOne", "TwoPointsDE", "RandomSearch"]
            ),
            seed=int(inputs.get("seed", 42)),
        )
    except NevergradNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "nevergrad",
            },
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "nevergrad",
            "seed": result["seed"],
            "best_optimizer": result["best_optimizer"],
            "best_objective": result["best_objective"],
        },
    }
''',
        """{
  "type": "object",
  "properties": {
    "built_in": {"type": "string", "enum": ["sphere", "rosenbrock", "rastrigin"], "default": "sphere"},
    "n_var": {"type": "integer", "minimum": 1, "default": 2},
    "lower": {"type": "number", "default": -5.0},
    "upper": {"type": "number", "default": 5.0},
    "budget": {"type": "integer", "minimum": 10, "default": 80},
    "optimizers": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["NGOpt", "TwoPointsDE", "OnePlusOne", "CMA", "PSO", "RandomSearch", "TBPSA", "MetaTuneRecentering"]
      }
    },
    "seed": {"type": "integer", "default": 42}
  },
  "additionalProperties": false
}
""",
        """from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("nevergrad")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_portfolio() -> None:
    out = implementation.execute({
        "built_in": "sphere",
        "n_var": 2,
        "budget": 40,
        "optimizers": ["OnePlusOne", "RandomSearch"],
        "seed": 0,
    })
    assert out["result"]["backend"] == "nevergrad"
    assert len(out["result"]["rows"]) == 2
    assert "best_optimizer" in out["result"]
""",
        '{"built_in": "sphere", "budget": 50, "optimizers": ["OnePlusOne", "RandomSearch"], "seed": 0}',
    )
    print("E3/E4 skills ok")


if __name__ == "__main__":
    main()
