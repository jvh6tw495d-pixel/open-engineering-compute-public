"""Dynamics helpers (LTI simulation and stability). Merit: NumPy/SciPy."""

from oec.kernel.dynamics.stability import stability_margins
from oec.kernel.dynamics.state_space import simulate_state_space

__all__ = ["simulate_state_space", "stability_margins"]
