"""Minimal, provenance-safe uncertainty representation.

This package represents uncertainty only.  General propagation is explicitly
outside v2.1's scope and is not inferred by these models.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from oec.kernel.units.normalize import same_dimension
from oec.kernel.units.operations import is_offset_unit
from oec.kernel.units.quantity import QuantityValue


class Uncertainty(BaseModel):
    """An absolute or relative uncertainty with optional measurement context.

    Relative values are fractions: ``0.02`` means two percent. Values above
    one remain valid because uncertainty can legitimately exceed 100%.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["absolute", "relative"]
    value: float
    unit: str | None = None
    confidence_level: float | None = None
    source: str | None = None

    @model_validator(mode="after")
    def _validate_representation(self) -> Uncertainty:
        if not math.isfinite(self.value) or self.value < 0:
            raise ValueError("uncertainty value must be finite and non-negative")
        if self.kind == "absolute":
            if self.unit is None:
                raise ValueError("absolute uncertainty requires a unit")
            QuantityValue(value=self.value, unit=self.unit)
            if is_offset_unit(self.unit):
                raise ValueError(
                    "absolute uncertainty requires a multiplicative interval unit "
                    "(for example K or delta_degC), not an affine temperature unit"
                )
        elif self.unit is not None:
            raise ValueError("relative uncertainty must not declare a unit")
        if self.confidence_level is not None and not 0 < self.confidence_level <= 1:
            raise ValueError("confidence_level must be in (0, 1]")
        return self


class UncertainQuantity(BaseModel):
    """A quantity paired with uncertainty metadata; no propagation is implied."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    quantity: QuantityValue
    uncertainty: Uncertainty

    @model_validator(mode="after")
    def _validate_absolute_dimension(self) -> UncertainQuantity:
        if (
            self.uncertainty.kind == "absolute"
            and self.uncertainty.unit is not None
            and not same_dimension(self.quantity.unit, self.uncertainty.unit)
        ):
            raise ValueError("absolute uncertainty unit must match the quantity dimension")
        return self


__all__ = ["Uncertainty", "UncertainQuantity"]
