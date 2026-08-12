"""Geometrical optics foundations (W3) — Snell and thin lens.

Merit: classical ray optics. Not wave optics / diffraction / gradient-index.
"""

from __future__ import annotations

import math

from oec.core.types import Assumption
from oec.kernel.units.quantity import QuantityValue
from oec.physics.errors import PhysicsEvaluationError
from oec.physics.laws import PhysicalLaw
from oec.physics.types import PhysicsDomain, ValidityFrame

OPTICS_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="Geometrical (ray) optics; wavelength << aperture", source="W3 optics v0"),
    Assumption(text="Homogeneous isotropic media; planar interface", source="W3 optics v0"),
)

_OPTICS_VALIDITY = ValidityFrame(
    domains=(PhysicsDomain.MATERIALS,),
    description="Geometrical optics: Snell's law and paraxial thin lens",
    constraints=("angles in radians for kernel API",),
)

SNELL_LAW = PhysicalLaw(
    id="optics.snell",
    name="Snell's law n1 sin θ1 = n2 sin θ2",
    hypotheses=OPTICS_ASSUMPTIONS,
    validity=_OPTICS_VALIDITY,
    references=("Hecht, Optics",),
    evaluator=lambda state: float(
        math.asin((state["n1"] * math.sin(state["theta1"])) / state["n2"])
    ),
)

THIN_LENS_LAW = PhysicalLaw(
    id="optics.thin_lens",
    name="Thin-lens equation 1/f = 1/u + 1/v (Cartesian sign convention)",
    hypotheses=(
        *OPTICS_ASSUMPTIONS,
        Assumption(text="Paraxial thin lens; single surface power", source="W3 optics v0"),
    ),
    validity=_OPTICS_VALIDITY,
    references=("Hecht, Optics",),
    evaluator=lambda state: float(1.0 / (1.0 / state["f"] - 1.0 / state["u"])),
)


def snell_refracted_angle(
    n1: float,
    n2: float,
    theta1_rad: float,
) -> dict[str, float | bool | None]:
    """Solve for transmitted angle; report TIR when |n1/n2 sin θ1| > 1."""
    if n1 <= 0 or n2 <= 0:
        raise PhysicsEvaluationError(
            "refractive indices must be positive", details={"n1": n1, "n2": n2}
        )
    if theta1_rad < 0 or theta1_rad > math.pi / 2:
        raise PhysicsEvaluationError(
            "theta1_rad must be in [0, π/2]", details={"theta1_rad": theta1_rad}
        )
    arg = (n1 / n2) * math.sin(theta1_rad)
    critical: float | None = math.asin(min(1.0, n2 / n1)) if n1 > n2 else None
    if abs(arg) > 1.0 + 1e-15:
        return {
            "theta2_rad": None,
            "total_internal_reflection": True,
            "critical_angle_rad": critical,
        }
    theta2 = float(math.asin(max(-1.0, min(1.0, arg))))
    return {
        "theta2_rad": theta2,
        "total_internal_reflection": False,
        "critical_angle_rad": critical,
    }


def thin_lens_image_distance(focal_length_m: float, object_distance_m: float) -> float:
    """Return image distance v from 1/f = 1/u + 1/v (object distance u > 0 convention)."""
    f = float(focal_length_m)
    u = float(object_distance_m)
    if abs(f) < 1e-30:
        raise PhysicsEvaluationError("focal_length must be non-zero", details={"f": f})
    if abs(u) < 1e-30:
        raise PhysicsEvaluationError("object_distance must be non-zero", details={"u": u})
    if abs(u - f) < 1e-15:
        raise PhysicsEvaluationError(
            "object at focal plane → image at infinity", details={"u": u, "f": f}
        )
    return THIN_LENS_LAW.evaluate({"f": f, "u": u})


def thin_lens_magnification(object_distance_m: float, image_distance_m: float) -> float:
    u = float(object_distance_m)
    v = float(image_distance_m)
    if abs(u) < 1e-30:
        raise PhysicsEvaluationError("object_distance must be non-zero")
    return float(-v / u)


def wavelength_in_medium(wavelength_vacuum_m: float, n: float) -> QuantityValue:
    if wavelength_vacuum_m <= 0 or n <= 0:
        raise PhysicsEvaluationError(
            "wavelength and n must be positive",
            details={"lambda0": wavelength_vacuum_m, "n": n},
        )
    return QuantityValue(value=wavelength_vacuum_m / n, unit="m")
