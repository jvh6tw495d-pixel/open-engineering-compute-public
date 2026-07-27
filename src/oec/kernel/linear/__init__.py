"""Linear algebra wrappers (NumPy/SciPy)."""

from oec.kernel.linear.analysis import (
    eigendecomposition,
    least_squares,
    matrix_properties,
    residual_norms,
)
from oec.kernel.linear.solve import solve_dense

__all__ = [
    "eigendecomposition",
    "least_squares",
    "matrix_properties",
    "residual_norms",
    "solve_dense",
]
