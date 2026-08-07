"""Deterministic Math IR problem classification (roadmap Step B item 5).

Method/class selection is never silent, per the ethos already established
in :mod:`oec.kernel.optimization.scalar` and
:mod:`oec.kernel.computational.roots` (``select_default_method``): a
:class:`~oec.modeling.ir.MathProblem` document is classified from its own
declared structure, and a mismatched explicit ``problem_class`` is a hard
error, not silently overridden.
"""

from __future__ import annotations

from typing import Literal

from oec.core.errors import (
    OverdeterminedProblemError,
    ScientificDomainError,
    UnderdeterminedProblemError,
)
from oec.modeling.ir import MathProblem

ProblemClass = Literal["linear_program", "scalar_root"]


def classify(problem: MathProblem) -> ProblemClass:
    """Classify ``problem`` as ``linear_program`` or ``scalar_root``.

    Raises :class:`ScientificDomainError` if both or neither an objective
    and equations are declared, or if ``problem.problem_class`` disagrees
    with the inferred class. Raises
    :class:`UnderdeterminedProblemError`/:class:`OverdeterminedProblemError`
    if the equation/unknown counts don't match for a ``scalar_root`` problem.
    """
    has_objective = problem.objective is not None
    has_equations = bool(problem.equations)

    if has_objective and has_equations:
        raise ScientificDomainError(
            "a MathProblem cannot declare both an objective (linear_program) "
            "and equations (scalar_root)"
        )

    if has_objective:
        inferred: ProblemClass = "linear_program"
    elif has_equations:
        n_equations = len(problem.equations)
        n_unknowns = len(problem.unknowns)
        if n_equations < n_unknowns:
            raise UnderdeterminedProblemError(
                f"{n_equations} equation(s) for {n_unknowns} unknown(s)",
                details={"equations": n_equations, "unknowns": n_unknowns},
            )
        if n_equations > n_unknowns:
            raise OverdeterminedProblemError(
                f"{n_equations} equation(s) for {n_unknowns} unknown(s)",
                details={"equations": n_equations, "unknowns": n_unknowns},
            )
        inferred = "scalar_root"
    else:
        raise ScientificDomainError("MathProblem declares neither an objective nor equations")

    if problem.problem_class is not None and problem.problem_class != inferred:
        raise ScientificDomainError(
            f"declared problem_class {problem.problem_class!r} does not match "
            f"inferred class {inferred!r}",
            details={"declared": problem.problem_class, "inferred": inferred},
        )

    return inferred
