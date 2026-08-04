"""P5 — material property lookup and linear uniaxial constitutive law (Hooke).

This module is **not** a structural solver: it exposes (1) a small, sourced
table of engineering material properties and (2) the uniaxial linear-elastic
constitutive relation ``σ = E ε`` (Hooke's law) as an executed
:class:`~oec.physics.laws.PhysicalLaw`. The constitutive relation is
non-balance: it is not a conservation check, so it does not route through
:mod:`oec.physics.conservation` (per D5, that owner is reserved for
inflow/outflow-style residuals, which a stress-strain relation is not).
"""

from __future__ import annotations

from dataclasses import dataclass

from oec.core.types import Assumption
from oec.kernel.units.quantity import QuantityValue
from oec.physics.errors import PhysicsEvaluationError
from oec.physics.laws import MaterialProperty, PhysicalLaw
from oec.physics.types import PhysicsDomain, ValidityFrame
from oec.physics.units import as_canonical

MATERIAL_TABLE_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="Room-temperature (~20 C), isotropic, bulk engineering values", source="P5 v0"),
)

UNIAXIAL_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="Linear-elastic, uniaxial loading (Hooke's law)", source="P5 v0"),
    Assumption(text="Small-strain regime; no plasticity or necking", source="P5 v0"),
    Assumption(text="Homogeneous, isotropic material", source="P5 v0"),
)

_MATERIALS_VALIDITY = ValidityFrame(
    domains=(PhysicsDomain.MATERIALS,),
    description="Material property lookup + linear uniaxial constitutive law — PHYSICS-CATALOG P5",
)


@dataclass(frozen=True)
class MaterialRecord:
    """One row of the sourced engineering material property table."""

    id: str
    name: str
    elastic_modulus: QuantityValue
    density: QuantityValue
    reference: str


MATERIAL_TABLE: dict[str, MaterialRecord] = {
    "steel_astm_a36": MaterialRecord(
        id="steel_astm_a36",
        name="Structural steel (ASTM A36)",
        elastic_modulus=QuantityValue(value=200e9, unit="Pa"),
        density=QuantityValue(value=7850.0, unit="kg / m ** 3"),
        reference="ASTM A36 handbook nominal values",
    ),
    "aluminum_6061_t6": MaterialRecord(
        id="aluminum_6061_t6",
        name="Aluminum alloy (6061-T6)",
        elastic_modulus=QuantityValue(value=68.9e9, unit="Pa"),
        density=QuantityValue(value=2700.0, unit="kg / m ** 3"),
        reference="MatWeb 6061-T6 nominal values",
    ),
    "copper_c11000": MaterialRecord(
        id="copper_c11000",
        name="Copper (C11000, annealed)",
        elastic_modulus=QuantityValue(value=110e9, unit="Pa"),
        density=QuantityValue(value=8960.0, unit="kg / m ** 3"),
        reference="MatWeb C11000 nominal values",
    ),
}

HOOKES_LAW = PhysicalLaw(
    id="materials.hookes_law_uniaxial",
    name="Uniaxial linear-elastic constitutive law (σ = E ε)",
    hypotheses=UNIAXIAL_ASSUMPTIONS,
    validity=_MATERIALS_VALIDITY,
    references=("Hooke's law; Gere & Goodno, Mechanics of Materials",),
    evaluator=lambda state: float(state["elastic_modulus"] * state["strain"]),
)


def material_property(material_id: str, property_name: str) -> MaterialProperty:
    """Look up a sourced material property as an auditable :class:`MaterialProperty`.

    ``property_name`` is one of ``"elastic_modulus"`` or ``"density"``.
    """
    record = MATERIAL_TABLE.get(material_id)
    if record is None:
        raise PhysicsEvaluationError(
            f"unknown material {material_id!r}",
            details={"material_id": material_id, "known_materials": sorted(MATERIAL_TABLE)},
        )
    if property_name not in ("elastic_modulus", "density"):
        raise PhysicsEvaluationError(
            f"unknown material property {property_name!r}",
            details={
                "property_name": property_name,
                "known_properties": ["elastic_modulus", "density"],
            },
        )
    value: QuantityValue = getattr(record, property_name)
    return MaterialProperty(
        id=f"materials.{record.id}.{property_name}",
        name=f"{record.name} — {property_name}",
        hypotheses=MATERIAL_TABLE_ASSUMPTIONS,
        validity=_MATERIALS_VALIDITY,
        references=(record.reference,),
        value=value,
    )


def uniaxial_stress(elastic_modulus: QuantityValue, strain: float) -> QuantityValue:
    """Uniaxial stress ``σ = E ε`` via the executed :data:`HOOKES_LAW`."""
    e = as_canonical(elastic_modulus, "Pa")
    value = HOOKES_LAW.evaluate({"elastic_modulus": e.value, "strain": strain})
    return QuantityValue(value=value, unit="Pa")


def uniaxial_strain_from_deformation(
    original_length: QuantityValue, deformation: QuantityValue
) -> float:
    """Engineering strain ``ε = ΔL / L0`` from an axial deformation."""
    l0 = as_canonical(original_length, "m")
    if l0.value <= 0:
        raise ValueError("original_length must be positive")
    dl = as_canonical(deformation, "m")
    return dl.value / l0.value


__all__ = [
    "HOOKES_LAW",
    "MATERIAL_TABLE",
    "MATERIAL_TABLE_ASSUMPTIONS",
    "UNIAXIAL_ASSUMPTIONS",
    "MaterialRecord",
    "material_property",
    "uniaxial_strain_from_deformation",
    "uniaxial_stress",
]
