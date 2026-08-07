"""Finance & Uncertainty Specialist for governed public OEC skills."""

from __future__ import annotations

from agents.common import SkillSpecialist


class FinanceUncertaintySpecialist(SkillSpecialist):
    name = "finance_uncertainty_specialist"
    demos = {
        "returns": ("finance.simple_returns", {"prices": [100.0, 110.0, 105.0, 120.0]}),
        "var": (
            "finance.var_historical",
            {"returns": [-0.02, -0.01, 0.0, 0.01, 0.02, -0.05, 0.03, -0.015], "confidence": 0.95},
        ),
        "propagate": (
            "uncertainty.propagate_linear",
            {"jacobian": [1.0, 1.0], "covariance": [[1.0, 0.0], [0.0, 1.0]]},
        ),
    }
