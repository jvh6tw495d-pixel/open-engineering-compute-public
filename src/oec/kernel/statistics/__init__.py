"""Statistics helpers (NumPy/SciPy). Merit: NumPy/SciPy; OEC governs contracts."""

from oec.kernel.statistics.bootstrap import bootstrap_ci
from oec.kernel.statistics.describe import describe
from oec.kernel.statistics.intervals import confidence_interval_of_mean
from oec.kernel.statistics.monte_carlo import monte_carlo_mean
from oec.kernel.statistics.regression import linear_regression

__all__ = [
    "bootstrap_ci",
    "confidence_interval_of_mean",
    "describe",
    "linear_regression",
    "monte_carlo_mean",
]
