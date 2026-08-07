"""Golden cases for mathematics.solve_root, per plan section 12.6.

Reference roots were computed independently with mpmath's
arbitrary-precision findroot() -- a different implementation than the
SciPy solvers this skill wraps -- specifically to avoid the section 22
KILL condition ("resultados aceitos só porque o solver retornou
sucesso"). See references.md item 4.
"""

import json
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _golden_from_example(filename: str, *, tolerance: float = 1e-9) -> GoldenCase:
    data = json.loads((_SKILL_DIR / "examples" / filename).read_text(encoding="utf-8"))
    return GoldenCase(
        id=filename,
        skill_id="mathematics.solve_root",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source="mpmath.findroot (independent, arbitrary-precision), see references.md #4",
        justification=data["description"],
    )


def test_sqrt_two_from_bracket_matches_basic_example() -> None:
    golden = _golden_from_example("basic.json")
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)


def test_sqrt_two_from_initial_guess_matches_example() -> None:
    golden = _golden_from_example("from_guess.json", tolerance=1e-6)
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)


def test_cubic_root_burden_and_faires_textbook_example() -> None:
    """x^3 - x - 2 = 0, bracket [1, 2] -- the classic textbook example
    (Burden & Faires, Numerical Analysis, Ch. 2). Reference root from
    mpmath.findroot(lambda x: x**3 - x - 2, 1.5) at 50 decimal digits."""
    golden = GoldenCase(
        id="cubic-burden-faires",
        skill_id="mathematics.solve_root",
        skill_version="0.1.0",
        inputs={"expression": "x**3 - x - 2", "bracket": [1, 2]},
        expected_result={
            "root": 1.5213797068045676,
            "method": "brentq",
            "iterations": 8,
            "residual": 0.0,
        },
        tolerance=1e-9,
        source="mpmath.findroot, cross-checked against Burden & Faires Ch. 2",
        justification="classic textbook bracketed-root example, independent of this skill",
    )
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)


def test_dottie_number_cos_x_equals_x() -> None:
    """cos(x) = x has a unique real root, the 'Dottie number' — a
    well-known constant with an independently verifiable value.

    Only `root` is checked against the independent mpmath reference
    (within tolerance -- brentq and mpmath use different algorithms and
    agree to ~1e-14, not bit-for-bit). `method`/`iterations`/`residual`
    are this implementation's own observed diagnostics, recorded for
    regression tracking, not independently verified."""
    golden = GoldenCase(
        id="dottie-number",
        skill_id="mathematics.solve_root",
        skill_version="0.1.0",
        inputs={"expression": "cos(x) - x", "bracket": [0, 1]},
        expected_result={
            "root": 0.7390851332151607,
            "method": "brentq",
            "iterations": 7,
            "residual": 7.882583474838611e-15,
        },
        tolerance=1e-9,
        source="mpmath.findroot(lambda x: mpmath.cos(x) - x, 0.5), 50 decimal digits",
        justification="the Dottie number: a well-known mathematical constant",
    )
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)


def test_newton_method_matches_secant_reference() -> None:
    golden = GoldenCase(
        id="newton-sqrt-two",
        skill_id="mathematics.solve_root",
        skill_version="0.1.0",
        inputs={
            "expression": "x**2 - 2",
            "initial_guess": 1.0,
            "method": "newton",
            "derivative": "2*x",
        },
        expected_result={
            "root": 1.4142135623730951,
            "method": "newton",
            "iterations": 5,
            "residual": 4.440892098500626e-16,
        },
        tolerance=1e-9,
        source="mpmath.findroot(lambda x: x**2 - 2, 1.5), 50 decimal digits",
        justification="cross-checks Newton's method against the same independent reference",
    )
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)
