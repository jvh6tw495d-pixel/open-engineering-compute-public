"""Golden cases for mathematics.curve_fit, per plan section 12.6.

Reference parameters come from an independent source: noiseless data
generated FROM known true parameters. The ground truth is known by
construction (the true parameters were chosen first, then the data
computed from them), not fit by any solver -- curve_fit recovering
those exact values is the verification, avoiding the section 22 KILL
condition of validating a solver against its own output.
"""

import json
import math
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _golden_from_example(filename: str, *, tolerance: float = 1e-6) -> GoldenCase:
    data = json.loads((_SKILL_DIR / "examples" / filename).read_text(encoding="utf-8"))
    return GoldenCase(
        id=filename,
        skill_id="mathematics.curve_fit",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source=(
            "noiseless data generated from known true parameters, see skill.md 'Worked examples'"
        ),
        justification=data["description"],
    )


def test_linear_exact_recovery_matches_example() -> None:
    golden = _golden_from_example("linear_exact_recovery.json", tolerance=1e-6)
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)
    assert out["diagnostics"]["converged"] is True
    assert all(abs(r) < 1e-6 for r in out["diagnostics"]["residuals"])


def test_sinusoid_exact_recovery_matches_example() -> None:
    golden = _golden_from_example("sinusoid_exact_recovery.json", tolerance=1e-4)
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)
    assert out["diagnostics"]["converged"] is True
    assert all(abs(r) < 1e-4 for r in out["diagnostics"]["residuals"])


def test_initial_guess_sensitivity_finds_a_different_local_optimum() -> None:
    """Same noiseless sinusoid data as sinusoid_exact_recovery.json, but
    a bad initial guess on the frequency parameter (b=0.3 instead of
    close to the true b=1.7) converges to a DIFFERENT local optimum of
    the least-squares surface -- diagnostics.converged is still True
    (SciPy found *a* minimum, just not the one matching the true
    generating parameters). Demonstrates explicitly (skill.md
    'Assumptions') that curve_fit is a local method and the caller is
    responsible for a reasonable initial_guess, especially for periodic
    parameters."""
    example = json.loads(
        (_SKILL_DIR / "examples" / "sinusoid_exact_recovery.json").read_text(encoding="utf-8")
    )
    good_guess_inputs = example["input"]
    bad_guess_inputs = {**good_guess_inputs, "initial_guess": [2.5, 0.3, 0.0]}

    good_out = implementation.execute(good_guess_inputs)
    bad_out = implementation.execute(bad_guess_inputs)

    assert good_out["diagnostics"]["converged"] is True
    assert bad_out["diagnostics"]["converged"] is True
    # both "converged" in SciPy's sense, but to visibly different points
    assert not math.isclose(bad_out["result"]["params"][1], 1.7, abs_tol=0.2)
    assert not math.isclose(
        bad_out["result"]["params"][0], good_out["result"]["params"][0], abs_tol=0.5
    )


def test_low_max_iterations_yields_unconverged_not_an_exception() -> None:
    """max_iterations=1 on the sinusoid fit must not silently report
    success -- diagnostics.converged is False, and params/residuals
    reflect the initial_guess (SciPy's RuntimeError path exposes no
    partial progress; skill.md 'Numerical diagnostics')."""
    example = json.loads(
        (_SKILL_DIR / "examples" / "sinusoid_exact_recovery.json").read_text(encoding="utf-8")
    )
    inputs = {**example["input"], "max_iterations": 1}
    out = implementation.execute(inputs)
    assert out["diagnostics"]["converged"] is False
    assert out["result"]["params"] == example["input"]["initial_guess"]
