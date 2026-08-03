"""Owner of generic conservation residual checks.

Domain-specific balance terms arrive in one canonical unit. Unit conversion and
domain-specific defaults are added in later waves; the tolerance policy and its
auditable result are owned here from Wave 1 onward.
"""

from __future__ import annotations

import math

from oec.physics.errors import ConservationError
from oec.physics.result import ConservationCheck


def evaluate_residual(
    residual: float,
    *,
    atol: float,
    rtol: float,
    scale: float,
    unit: str,
) -> ConservationCheck:
    """Apply ``abs(residual) <= atol + rtol * scale`` reproducibly."""
    parameters = {"residual": residual, "atol": atol, "rtol": rtol, "scale": scale}
    if any(not math.isfinite(value) for value in parameters.values()):
        raise ConservationError(
            "conservation inputs must be finite",
            details={
                "invalid_fields": [
                    key for key, value in parameters.items() if not math.isfinite(value)
                ]
            },
        )
    if atol < 0 or rtol < 0 or scale < 0:
        raise ConservationError(
            "conservation tolerances and scale must be non-negative",
            details={"atol": atol, "rtol": rtol, "scale": scale},
        )
    if not unit:
        raise ConservationError("conservation residual unit must not be empty")

    return ConservationCheck(
        residual=residual,
        balanced=abs(residual) <= atol + rtol * scale,
        atol=atol,
        rtol=rtol,
        scale=scale,
        unit=unit,
    )


__all__ = ["evaluate_residual"]
