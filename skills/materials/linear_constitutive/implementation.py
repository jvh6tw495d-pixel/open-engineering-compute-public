"""materials.linear_constitutive entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Thin adapter (skill-first,
per plan section 8): validates/adapts inputs into ``QuantityValue``s (or a
sourced material lookup) and calls ``oec.physics.materials``. This module
performs no physics arithmetic of its own.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.materials import (
    material_property,
    uniaxial_strain_from_deformation,
    uniaxial_stress,
)


def _qv(field: dict[str, Any]) -> QuantityValue:
    return QuantityValue(value=float(field["value"]), unit=field["unit"])


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    material_meta: dict[str, Any] | None = None
    if "material_id" in inputs:
        prop = material_property(str(inputs["material_id"]), "elastic_modulus")
        elastic_modulus = prop.value
        material_meta = {
            "material_id": str(inputs["material_id"]),
            "property_id": prop.id,
            "property_name": prop.name,
            "references": list(prop.references),
        }
    else:
        elastic_modulus = _qv(inputs["elastic_modulus"])

    if "strain" in inputs:
        strain = float(inputs["strain"])
    else:
        strain = uniaxial_strain_from_deformation(
            _qv(inputs["original_length"]),
            _qv(inputs["deformation"]),
        )

    stress = uniaxial_stress(elastic_modulus, strain)

    result: dict[str, Any] = {
        "elastic_modulus": elastic_modulus.model_dump(mode="json"),
        "strain": strain,
        "stress": stress.model_dump(mode="json"),
    }
    if material_meta is not None:
        result["material"] = material_meta

    return {"result": result, "diagnostics": {}}
