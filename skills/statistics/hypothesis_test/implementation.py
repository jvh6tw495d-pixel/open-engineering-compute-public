"""statistics.hypothesis_test — SciPy closed-catalog tests."""

from __future__ import annotations

from typing import Any

from oec.kernel.statistics.hypothesis import run_hypothesis_test


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = run_hypothesis_test(
        test=str(inputs["test"]),
        sample=inputs.get("sample"),
        sample_a=inputs.get("sample_a"),
        sample_b=inputs.get("sample_b"),
        popmean=float(inputs.get("popmean", 0.0)),
        equal_var=bool(inputs.get("equal_var", True)),
        alternative=str(inputs.get("alternative", "two-sided")),
        reference_distribution=str(inputs.get("reference_distribution", "norm")),
        reference_params=inputs.get("reference_params"),
    )
    return {
        "result": out,
        "diagnostics": {
            "test": out["test"],
            "backend": out["backend"],
            "statistic": out["statistic"],
            "pvalue": out["pvalue"],
        },
    }
