"""Compile a Math IR ``scalar_root`` document to a residual callable and
solve via SciPy root-finding.

v0 scope, stated explicitly rather than attempted silently: exactly one
equation in one unknown, which must be the only symbol referenced in that
equation (ADR 0020 non-goals). Method selection reuses
:func:`oec.kernel.numerics.root_finding.select_default_method` — a bracket
takes precedence, an initial guess alone selects the secant method — the
same explicit, non-silent rule ``mathematics.solve_root`` already uses.
"""

from __future__ import annotations

from oec.core.errors import ScientificDomainError
from oec.kernel.numerics.root_finding import (
    RootFindingResult,
    find_root_bracketed,
    find_root_from_guess,
    select_default_method,
)
from oec.modeling.dimensions import check_equation_dimensions, referenced_symbols
from oec.modeling.evaluate import evaluate_expr
from oec.modeling.ir import MathProblem


def compile_scalar_root(problem: MathProblem) -> RootFindingResult:
    """Compile and solve the scalar_root variant of ``problem``."""
    if len(problem.equations) != 1 or len(problem.unknowns) != 1:
        raise ScientificDomainError(
            "the v0 scalar_root compiler supports exactly one equation and one unknown",
            details={"equations": len(problem.equations), "unknowns": len(problem.unknowns)},
        )

    unknown = problem.unknowns[0]
    equation = problem.equations[0]

    extra_symbols = referenced_symbols(equation.lhs) | referenced_symbols(equation.rhs)
    extra_symbols.discard(unknown)
    if extra_symbols:
        raise ScientificDomainError(
            "the v0 scalar_root compiler only supports the equation's unknown as a free "
            f"symbol; found additional free symbol(s): {sorted(extra_symbols)}",
            details={"unknown": unknown, "extra_symbols": sorted(extra_symbols)},
        )

    symbol_units = {symbol.name: symbol.unit for symbol in problem.symbols}
    check_equation_dimensions(equation, symbol_units)

    def residual(x: float) -> float:
        bindings = {unknown: x}
        return evaluate_expr(equation.lhs, bindings) - evaluate_expr(equation.rhs, bindings)

    bracket = problem.bracket.get(unknown)
    guess = problem.initial_guess.get(unknown)
    method = select_default_method(
        has_bracket=bracket is not None, has_initial_guess=guess is not None
    )

    if method == "brentq":
        if bracket is None:
            # Unreachable given select_default_method's has_bracket check; guarded
            # explicitly (not via `assert`, which is stripped under -O).
            raise ScientificDomainError(
                "brentq selected without a bracket", details={"unknown": unknown}
            )
        return find_root_bracketed(residual, bracket[0], bracket[1])

    if guess is None:
        raise ScientificDomainError(
            "secant selected without an initial guess", details={"unknown": unknown}
        )
    return find_root_from_guess(residual, guess)
