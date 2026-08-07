"""Thin dimensional-check façade for physics expressions.

The Math IR implementation remains owned by :mod:`oec.modeling.dimensions`.
Physics consumers import the two supported entry points here so this package
does not grow a second dimension parser or algebra.
"""

from oec.kernel.units.normalize import dimension_of
from oec.modeling.dimensions import infer_dimension

__all__ = ["dimension_of", "infer_dimension"]
