"""Owner of generic conservation residual checks.

Domain-specific balance terms arrive in one canonical unit chosen by the
caller to match the *actual* balance being closed (a KCL power residual is
W; a mechanical energy balance is J; a mass-flow continuity balance is
kg/s — never a blindly-applied domain default). This module owns the single
``abs(residual) <= atol + rtol * scale`` formula (D5); every other module in
:mod:`oec.physics` routes through :func:`evaluate_residual`,
:func:`evaluate_vector_residual`, or :func:`aggregate_balance` instead of
reimplementing the tolerance check inline.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

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


def evaluate_vector_residual(
    residuals: Mapping[str, float],
    *,
    atol: float,
    rtol: float,
    scale: float,
    unit: str,
) -> dict[str, ConservationCheck]:
    """Apply the conservation tolerance policy independently to each named residual.

    This is the multi-node/vectorial entry point (for example one KCL residual
    per bus in a meshed power-flow network): every component is checked by
    :func:`evaluate_residual`, so the tolerance formula is never duplicated.
    """
    if not residuals:
        raise ConservationError("vector residual requires at least one named component")
    return {
        key: evaluate_residual(value, atol=atol, rtol=rtol, scale=scale, unit=unit)
        for key, value in residuals.items()
    }


def aggregate_balance(checks: Mapping[str, ConservationCheck]) -> ConservationCheck:
    """Combine per-component conservation checks into one network-level check.

    The aggregate residual is the arithmetic sum of the component residuals
    (for a lossless network this is exactly ``sum(injections)``, since the
    internal flow terms cancel pairwise), re-checked against the shared
    tolerance policy via :func:`evaluate_residual`. The aggregate is
    ``balanced`` only when the summed residual itself is within tolerance
    *and* every individual component is balanced.
    """
    if not checks:
        raise ConservationError("cannot aggregate an empty set of conservation checks")

    units = {check.unit for check in checks.values()}
    if len(units) > 1:
        raise ConservationError(
            "cannot aggregate conservation checks reported in different units",
            details={"units": sorted(units)},
        )
    atols = {check.atol for check in checks.values()}
    rtols = {check.rtol for check in checks.values()}
    scales = {check.scale for check in checks.values()}
    if len(atols) > 1 or len(rtols) > 1 or len(scales) > 1:
        raise ConservationError(
            "cannot aggregate conservation checks with differing tolerance policy",
            details={"atol": sorted(atols), "rtol": sorted(rtols), "scale": sorted(scales)},
        )

    unit = units.pop()
    total_residual = math.fsum(check.residual for check in checks.values())
    aggregate = evaluate_residual(
        total_residual, atol=atols.pop(), rtol=rtols.pop(), scale=scales.pop(), unit=unit
    )
    all_balanced = aggregate.balanced and all(check.balanced for check in checks.values())
    if all_balanced == aggregate.balanced:
        return aggregate
    return aggregate.model_copy(update={"balanced": all_balanced})


__all__ = ["aggregate_balance", "evaluate_residual", "evaluate_vector_residual"]
