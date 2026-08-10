"""One-shot scaffold for E2 multiobjective skills (dev helper)."""

from __future__ import annotations

from pathlib import Path

root = Path(__file__).resolve().parents[1] / "skills" / "evolutionary"

skills = [
    ("nsga2", "evolutionary.nsga2", "pymoo_nsga2", "NSGA-II (pymoo)", "nsga2"),
    ("nsga3", "evolutionary.nsga3", "pymoo_nsga3", "NSGA-III (pymoo)", "nsga3"),
    ("moead", "evolutionary.moead", "pymoo_moead", "MOEA/D (pymoo)", "moead"),
    (
        "pareto_search",
        "evolutionary.pareto_search",
        "pymoo_pareto_search",
        "Pareto Search dispatch (pymoo)",
        None,
    ),
]

output_schema = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "mo output",
  "type": "object",
  "properties": {
    "backend": { "type": "string" },
    "algorithm": { "type": "string" },
    "seed": { "type": "integer" },
    "n_objectives": { "type": "integer" },
    "decision_vectors": { "type": "array" },
    "objective_vectors": { "type": "array" },
    "nondominated_mask": { "type": "array" },
    "n_nondominated": { "type": "integer" },
    "hypervolume": { "type": ["number", "null"] },
    "problem_fingerprint": { "type": "string" }
  },
  "required": ["backend", "algorithm", "objective_vectors", "n_nondominated"],
  "additionalProperties": true
}
"""

validation = """from __future__ import annotations

from typing import Any, ClassVar

from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome


class MoValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        variables = normalized_inputs.get("variables")
        if not isinstance(variables, list) or len(variables) < 2:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["variables must have at least 2 decision variables"],
                )
            ]
        return []
"""

example = """{
  "variables": [
    {"name": "x0", "lower": 0.0, "upper": 1.0},
    {"name": "x1", "lower": 0.0, "upper": 1.0},
    {"name": "x2", "lower": 0.0, "upper": 1.0},
    {"name": "x3", "lower": 0.0, "upper": 1.0},
    {"name": "x4", "lower": 0.0, "upper": 1.0}
  ],
  "built_in": "zdt1",
  "generations": 20,
  "population": 30,
  "seed": 0
}
"""


def _input_schema(title: str, *, with_algorithm: bool) -> str:
    algo_block = ""
    if with_algorithm:
        algo_block = """    "algorithm": {
      "type": "string",
      "enum": ["nsga2", "nsga3", "moead"],
      "default": "nsga2"
    },
"""
    return f"""{{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "{title} input",
  "type": "object",
  "properties": {{
    "variables": {{
      "type": "array",
      "minItems": 2,
      "items": {{
        "type": "object",
        "properties": {{
          "name": {{ "type": "string" }},
          "lower": {{ "type": "number" }},
          "upper": {{ "type": "number" }}
        }},
        "required": ["name", "lower", "upper"],
        "additionalProperties": false
      }}
    }},
    "built_in": {{
      "type": "string",
      "enum": ["zdt1", "zdt2", "bi_sphere"],
      "default": "zdt1"
    }},
{algo_block}    "generations": {{ "type": "integer", "minimum": 1, "default": 30 }},
    "population": {{ "type": "integer", "minimum": 4, "default": 40 }},
    "seed": {{ "type": "integer", "default": 42 }},
    "n_partitions": {{ "type": "integer", "minimum": 1, "default": 12 }}
  }},
  "required": ["variables"],
  "additionalProperties": false
}}
"""


def _impl_fixed(skill_id: str, algo: str) -> str:
    return f'''"""{skill_id} — multi-objective via pymoo."""

from __future__ import annotations

from typing import Any

from oec.evolutionary.contracts import (
    BudgetSpec,
    BuiltInMultiProblemName,
    MultiObjectiveAlgorithmName,
    MultiObjectiveAlgorithmSpec,
    MultiObjectiveProblemSpec,
    VariableSpec,
)
from oec.kernel.evolutionary.errors import PymooNotAvailableError
from oec.kernel.evolutionary.multiobjective import optimize_multi


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    problem = MultiObjectiveProblemSpec(
        variables=[VariableSpec(**v) for v in inputs["variables"]],
        built_in=BuiltInMultiProblemName(inputs.get("built_in", "zdt1")),
        n_objectives=2,
    )
    algorithm = MultiObjectiveAlgorithmSpec(
        algorithm=MultiObjectiveAlgorithmName("{algo}"),
        budget=BudgetSpec(
            generations=int(inputs.get("generations", 30)),
            population=int(inputs.get("population", 40)),
        ),
        seed=int(inputs.get("seed", 42)),
        n_partitions=int(inputs.get("n_partitions", 12)),
    )
    try:
        result = optimize_multi(problem, algorithm)
    except PymooNotAvailableError as exc:
        return {{
            "result": {{"error": exc.to_dict()}},
            "diagnostics": {{
                "converged": False,
                "message": exc.message,
                "backend": "pymoo",
            }},
        }}
    payload = result.model_dump(mode="json")
    return {{
        "result": payload,
        "diagnostics": {{
            "converged": result.n_nondominated > 0,
            "message": result.message,
            "backend": "pymoo",
            "seed": result.seed,
            "n_nondominated": result.n_nondominated,
            "hypervolume": result.hypervolume,
        }},
    }}
'''


impl_dispatch = '''"""evolutionary.pareto_search — dispatch multi-objective algorithm."""

from __future__ import annotations

from typing import Any

from oec.evolutionary.contracts import (
    BudgetSpec,
    BuiltInMultiProblemName,
    MultiObjectiveAlgorithmName,
    MultiObjectiveAlgorithmSpec,
    MultiObjectiveProblemSpec,
    VariableSpec,
)
from oec.kernel.evolutionary.errors import PymooNotAvailableError
from oec.kernel.evolutionary.multiobjective import optimize_multi


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    problem = MultiObjectiveProblemSpec(
        variables=[VariableSpec(**v) for v in inputs["variables"]],
        built_in=BuiltInMultiProblemName(inputs.get("built_in", "zdt1")),
        n_objectives=2,
    )
    algorithm = MultiObjectiveAlgorithmSpec(
        algorithm=MultiObjectiveAlgorithmName(inputs.get("algorithm", "nsga2")),
        budget=BudgetSpec(
            generations=int(inputs.get("generations", 30)),
            population=int(inputs.get("population", 40)),
        ),
        seed=int(inputs.get("seed", 42)),
        n_partitions=int(inputs.get("n_partitions", 12)),
    )
    try:
        result = optimize_multi(problem, algorithm)
    except PymooNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "pymoo",
            },
        }
    payload = result.model_dump(mode="json")
    return {
        "result": payload,
        "diagnostics": {
            "converged": result.n_nondominated > 0,
            "message": result.message,
            "backend": "pymoo",
            "seed": result.seed,
            "n_nondominated": result.n_nondominated,
            "hypervolume": result.hypervolume,
        },
    }
'''

test = """from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pymoo")

from oec.testing import load_skill_module  # noqa: E402

implementation = load_skill_module(Path(__file__).resolve().parent.parent, "implementation")
pytestmark = pytest.mark.evolutionary


def test_runs_zdt1() -> None:
    vars_ = [{"name": f"x{i}", "lower": 0.0, "upper": 1.0} for i in range(5)]
    payload = {
        "variables": vars_,
        "built_in": "zdt1",
        "generations": 12,
        "population": 24,
        "seed": 0,
    }
    out = implementation.execute(payload)
    assert out["result"]["backend"] == "pymoo"
    assert out["result"]["n_nondominated"] >= 1
    assert len(out["result"]["objective_vectors"]) >= 1
"""


def main() -> None:
    for folder, sid, method, title, fixed in skills:
        d = root / folder
        (d / "examples").mkdir(parents=True, exist_ok=True)
        (d / "tests").mkdir(parents=True, exist_ok=True)
        yaml = f"""id: {sid}
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
  id: {method}
  version: 0.1.0
  iterative: true

execution:
  deterministic: false
  timeout_seconds: 180
  network_access: false
  filesystem_access: false

validation:
  schema: true
  dimensional: false
  mathematical: true
  physical: false
  numerical: true

references:
  - "pymoo — https://pymoo.org/"
  - "Deb et al. — NSGA-II / NSGA-III"
  - "ADR 0031 Neural and Evolutionary Compute"

tags:
  - evolutionary
  - multiobjective
  - experimental
"""
        (d / "skill.yaml").write_text(yaml, encoding="utf-8")
        (d / "skill.md").write_text(
            f"---\nid: {sid}\nversion: 0.1.0\n---\n\n# {title}\n\n"
            "Multi-objective box-constrained search on built-in problems "
            "(`zdt1`, `zdt2`, `bi_sphere`). Requires `oec[evolutionary]`.\n",
            encoding="utf-8",
        )
        (d / "references.md").write_text(
            "# References\n\n- pymoo docs\n- ADR 0031 / E2 multiobjective\n",
            encoding="utf-8",
        )
        (d / "output.schema.json").write_text(output_schema, encoding="utf-8")
        (d / "input.schema.json").write_text(
            _input_schema(sid, with_algorithm=fixed is None), encoding="utf-8"
        )
        if fixed is None:
            (d / "implementation.py").write_text(impl_dispatch, encoding="utf-8")
        else:
            (d / "implementation.py").write_text(_impl_fixed(sid, fixed), encoding="utf-8")
        (d / "validation.py").write_text(validation, encoding="utf-8")
        (d / "tests" / "test_golden.py").write_text(test, encoding="utf-8")
        (d / "examples" / "zdt1.json").write_text(example, encoding="utf-8")
    print("mo skills ok")


if __name__ == "__main__":
    main()
