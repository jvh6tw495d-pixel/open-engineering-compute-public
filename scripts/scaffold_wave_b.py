"""One-shot scaffold for v2.3 Wave B skill packages. Idempotent."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills"


def w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.lstrip("\n"), encoding="utf-8", newline="\n")


def yaml(skill_id: str, title: str, method: str, iterative: bool = False) -> str:
    domain = skill_id.split(".")[0]
    return f"""id: {skill_id}
version: 0.1.0
status: experimental
domain: {domain}
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
  iterative: {str(iterative).lower()}

execution:
  deterministic: true
  timeout_seconds: 30
  network_access: false
  filesystem_access: false

validation:
  schema: true
  dimensional: false
  mathematical: true
  physical: false
  numerical: true

references:
  - "See references.md"

tags:
  - v2.3
  - wave-b
  - {domain}
"""


def jdump(obj: object) -> str:
    return json.dumps(obj, indent=2) + "\n"


def main() -> None:
    # uncertainty.lhs
    b = ROOT / "uncertainty" / "lhs"
    w(b / "skill.yaml", yaml("uncertainty.lhs", "Latin Hypercube Sample", "latin_hypercube"))
    w(
        b / "skill.md",
        """---
id: uncertainty.lhs
version: 0.1.0
---

# Purpose

Latin Hypercube sample design over rectangular bounds (McKay et al.).

# Official methodology

Method id: `latin_hypercube`. Stratified unit hypercube + affine map to bounds.
Deterministic when `seed` is set (ADR 0004).

# Applicability limits

- `n_samples >= 1`, each bound `low < high`.
- Design only — does not evaluate a model.

# Known limitations

- No correlation control (Iman–Conover) in Wave B.
""",
    )
    w(
        b / "references.md",
        """# References

1. McKay, Beckman, Conover (1979), Technometrics — LHS.
2. Seeded NumPy Generator makes strata permutation deterministic.
""",
    )
    w(
        b / "input.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "n_samples": {"type": "integer", "exclusiveMinimum": 0},
                    "bounds": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "items": {"type": "number"},
                        },
                    },
                    "seed": {"type": ["integer", "null"]},
                },
                "required": ["n_samples", "bounds"],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "output.schema.json",
        jdump(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "samples": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                    },
                    "n_samples": {"type": "integer"},
                    "n_dim": {"type": "integer"},
                    "bounds": {"type": "array"},
                    "seed": {"type": ["integer", "null"]},
                    "backend": {"type": "string"},
                    "converged": {"type": ["null", "boolean"]},
                    "method": {"type": "string"},
                },
                "required": [
                    "samples",
                    "n_samples",
                    "n_dim",
                    "bounds",
                    "backend",
                    "converged",
                    "method",
                ],
                "additionalProperties": False,
            }
        ),
    )
    w(
        b / "implementation.py",
        '''"""uncertainty.lhs entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.uncertainty.sampling import latin_hypercube


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = latin_hypercube(
        int(inputs["n_samples"]),
        inputs["bounds"],
        seed=inputs.get("seed"),
    )
    return {
        "result": out,
        "diagnostics": {
            "n_samples": out["n_samples"],
            "n_dim": out["n_dim"],
            "converged": None,
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


class LhsValidator:
    layer: ClassVar[str] = "mathematical"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        del skill
        bounds = normalized_inputs.get("bounds")
        if not isinstance(bounds, list) or not bounds:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["bounds must be non-empty"],
                )
            ]
        for pair in bounds:
            if not isinstance(pair, list) or len(pair) != 2 or not (pair[0] < pair[1]):
                return [
                    ValidationOutcome(
                        layer=self.layer,
                        severity=Severity.ERROR,
                        messages=["each bound must satisfy low < high"],
                    )
                ]
        n = normalized_inputs.get("n_samples")
        if not isinstance(n, int) or n < 1:
            return [
                ValidationOutcome(
                    layer=self.layer,
                    severity=Severity.ERROR,
                    messages=["n_samples must be a positive integer"],
                )
            ]
        return []
''',
    )
    w(
        b / "examples" / "unit_square.json",
        jdump(
            {
                "description": "2 samples in [0,1]^2 with seed=0",
                "input": {
                    "n_samples": 2,
                    "bounds": [[0.0, 1.0], [0.0, 1.0]],
                    "seed": 0,
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
validation = load_skill_module(_SKILL_DIR, "validation")
V = validation.LhsValidator()


def test_bad_bounds() -> None:
    assert V.validate(None, {"n_samples": 2, "bounds": [[1.0, 0.0]]})  # type: ignore[arg-type]


def test_ok() -> None:
    assert not V.validate(None, {"n_samples": 2, "bounds": [[0.0, 1.0]]})  # type: ignore[arg-type]
''',
    )
    w(
        b / "tests" / "test_golden.py",
        '''from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_lhs_seeded_shape_and_bounds() -> None:
    out = implementation.execute(
        {"n_samples": 5, "bounds": [[0.0, 2.0], [-1.0, 1.0]], "seed": 1}
    )
    samples = out["result"]["samples"]
    assert len(samples) == 5
    assert out["result"]["n_dim"] == 2
    for row in samples:
        assert 0.0 <= row[0] <= 2.0
        assert -1.0 <= row[1] <= 1.0


def test_lhs_deterministic_with_seed() -> None:
    a = implementation.execute(
        {"n_samples": 4, "bounds": [[0.0, 1.0]], "seed": 7}
    )["result"]["samples"]
    b = implementation.execute(
        {"n_samples": 4, "bounds": [[0.0, 1.0]], "seed": 7}
    )["result"]["samples"]
    assert a == b
''',
    )

    print("lhs ok")
    import importlib.util

    rest_path = Path(__file__).resolve().parent / "_wave_b_rest.py"
    spec = importlib.util.spec_from_file_location("_wave_b_rest", rest_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.scaffold_rest(ROOT, w, yaml, jdump)
    print("wave B scaffold complete")


if __name__ == "__main__":
    main()
