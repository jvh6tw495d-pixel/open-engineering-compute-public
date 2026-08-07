"""Safe public arithmetic for :class:`QuantityValue`.

The functions in this module keep Pint inside the kernel and turn invalid
dimensional operations into a typed OEC exception.  Offset temperatures are
intentionally excluded from arithmetic: a caller must use an explicit delta
temperature unit (for example ``delta_degC``) when modelling a temperature
difference.
"""

from typing import Never

import pint
from pydantic import ValidationError

from oec.errors import UnitError
from oec.kernel.units.quantity import QuantityValue
from oec.kernel.units.registry import ureg
from oec.kernel.units.serialization import from_pint, to_pint


class QuantityOperationError(UnitError):
    """Raised when physical arithmetic cannot be performed safely."""

    default_code = "quantity_operation_invalid"


def is_offset_unit(unit: str) -> bool:
    """Whether a unit has an affine offset rather than a pure scale."""
    try:
        # Pint rejects multiplicative arithmetic on affine units through its
        # public Quantity API.  Use that contract instead of inspecting the
        # registry's private ``_units``/converter implementation.
        ureg.Quantity(1.0, unit) * 1.0
    except pint.OffsetUnitCalculusError:
        return True
    return False


def _raise_operation_error(
    operation: str,
    left: QuantityValue,
    right: QuantityValue,
    exc: Exception | None = None,
) -> Never:
    message = f"cannot {operation} quantities with units {left.unit!r} and {right.unit!r}"
    if exc is not None:
        message = f"{message}: {exc}"
    raise QuantityOperationError(
        message,
        details={"operation": operation, "left_unit": left.unit, "right_unit": right.unit},
    ) from exc


def _reject_offset_units(operation: str, left: QuantityValue, right: QuantityValue) -> None:
    if is_offset_unit(left.unit) or is_offset_unit(right.unit):
        _raise_operation_error(operation, left, right)


def add(left: QuantityValue, right: QuantityValue) -> QuantityValue:
    """Add compatible quantities and express the result in ``left.unit``."""
    _reject_offset_units("add", left, right)
    try:
        right_in_left_unit = to_pint(right).to(left.unit)
        return QuantityValue(value=left.value + float(right_in_left_unit.magnitude), unit=left.unit)
    except (pint.errors.PintError, ValidationError) as exc:
        _raise_operation_error("add", left, right, exc)


def subtract(left: QuantityValue, right: QuantityValue) -> QuantityValue:
    """Subtract compatible quantities and express the result in ``left.unit``."""
    _reject_offset_units("subtract", left, right)
    try:
        right_in_left_unit = to_pint(right).to(left.unit)
        return QuantityValue(value=left.value - float(right_in_left_unit.magnitude), unit=left.unit)
    except (pint.errors.PintError, ValidationError) as exc:
        _raise_operation_error("subtract", left, right, exc)


def multiply(left: QuantityValue, right: QuantityValue) -> QuantityValue:
    """Multiply two non-offset quantities."""
    _reject_offset_units("multiply", left, right)
    try:
        return from_pint(to_pint(left) * to_pint(right))
    except (pint.errors.PintError, ValidationError) as exc:
        _raise_operation_error("multiply", left, right, exc)


def divide(left: QuantityValue, right: QuantityValue) -> QuantityValue:
    """Divide two non-offset quantities."""
    _reject_offset_units("divide", left, right)
    try:
        return from_pint(to_pint(left) / to_pint(right))
    except (pint.errors.PintError, ValidationError, ZeroDivisionError) as exc:
        _raise_operation_error("divide", left, right, exc)
