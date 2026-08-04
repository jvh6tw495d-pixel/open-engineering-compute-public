"""P5 material property lookup + uniaxial Hooke's law — Wave 3 slice 3.7."""

from __future__ import annotations

import pytest

from oec.kernel.units.quantity import QuantityValue
from oec.physics.errors import PhysicsEvaluationError
from oec.physics.laws import MaterialProperty
from oec.physics.materials import (
    material_property,
    uniaxial_strain_from_deformation,
    uniaxial_stress,
)


def test_material_property_lookup_returns_auditable_material_property() -> None:
    prop = material_property("steel_astm_a36", "elastic_modulus")
    assert isinstance(prop, MaterialProperty)
    assert prop.value.unit == "Pa"
    assert prop.value.value == pytest.approx(200e9)
    assert prop.references


def test_material_property_lookup_rejects_unknown_material() -> None:
    with pytest.raises(PhysicsEvaluationError, match="unknown material"):
        material_property("unobtainium", "elastic_modulus")


def test_material_property_lookup_rejects_unknown_property() -> None:
    with pytest.raises(PhysicsEvaluationError, match="unknown material property"):
        material_property("steel_astm_a36", "yield_strength")


def test_uniaxial_stress_matches_hand_solved_hookes_law() -> None:
    # sigma = E * epsilon = 200e9 * 0.001 = 2e8 Pa
    stress = uniaxial_stress(elastic_modulus=QuantityValue(value=200e9, unit="Pa"), strain=0.001)
    assert stress.unit == "Pa"
    assert stress.value == pytest.approx(2e8)


def test_uniaxial_strain_from_deformation_matches_hand_solved_value() -> None:
    strain = uniaxial_strain_from_deformation(
        original_length=QuantityValue(value=2.0, unit="m"),
        deformation=QuantityValue(value=0.002, unit="m"),
    )
    assert strain == pytest.approx(0.001)


def test_uniaxial_stress_composes_with_material_lookup_and_strain() -> None:
    steel_modulus = material_property("steel_astm_a36", "elastic_modulus").value
    strain = uniaxial_strain_from_deformation(
        original_length=QuantityValue(value=1.0, unit="m"),
        deformation=QuantityValue(value=1e-3, unit="m"),
    )
    stress = uniaxial_stress(steel_modulus, strain)
    assert stress.value == pytest.approx(200e9 * 1e-3)
