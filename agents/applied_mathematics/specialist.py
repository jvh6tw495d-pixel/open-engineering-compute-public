"""Applied Mathematics Specialist v0.1 — formulate skill inputs, run OEC, narrate.

Harness only: LLMs use ``prompts/``; numerical answers always come from
:class:`oec.sdk.Engine`.
"""

from __future__ import annotations

from agents.common import SkillSpecialist


class AppliedMathematicsSpecialist(SkillSpecialist):
    """Maps math demos → mathematics/linear/statistics/numerical skills."""

    name = "applied_mathematics_specialist"
    demos = {
        "sqrt2": (
            "mathematics.solve_root",
            {"expression": "x**2 - 2", "bracket": [0, 2]},
        ),
        "solve_root": (
            "mathematics.solve_root",
            {"expression": "x**2 - 2", "bracket": [0, 2]},
        ),
        "integrate_x2": (
            "mathematics.integrate",
            {"expression": "x**2", "bounds": [0.0, 1.0]},
        ),
        "linear_identity": (
            "linear.solve_system",
            {"A": [[2.0, 0.0], [0.0, 2.0]], "b": [2.0, 4.0]},
        ),
        "matrix_properties": (
            "linear.matrix_properties",
            {"A": [[2.0, 0.0], [0.0, 3.0]]},
        ),
        "describe": (
            "statistics.describe",
            {"values": [1.0, 2.0, 3.0, 4.0]},
        ),
        "monte_carlo": (
            "statistics.monte_carlo",
            {
                "expression": "x**2",
                "n_samples": 5000,
                "low": 0.0,
                "high": 1.0,
                "seed": 42,
            },
        ),
        "ode_decay": (
            "numerical.ode_ivp",
            {
                "state_names": ["y"],
                "dydt_expressions": ["-y"],
                "t_span": [0.0, 1.0],
                "y0": [1.0],
                "t_eval": [0.0, 0.5, 1.0],
            },
        ),
    }
