"""Statistics helpers (NumPy). Merit: NumPy; OEC governs contracts."""

from oec.kernel.statistics.describe import describe
from oec.kernel.statistics.monte_carlo import monte_carlo_mean

__all__ = ["describe", "monte_carlo_mean"]
