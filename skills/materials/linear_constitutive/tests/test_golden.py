"""Golden cases for materials.linear_constitutive.

Expected values are hand-derived closed form (sigma = E * epsilon) --
never by trusting the implementation under test.
"""

import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_steel_uniaxial_lookup_matches_hookes_law() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "steel_uniaxial.json").read_text(encoding="utf-8"))
    inputs = data["input"]
    # Hand oracle: E_A36 = 200e9 Pa; sigma = 200e9 * 0.001 = 2e8 Pa.
    golden = GoldenCase(
        id="steel_uniaxial.json",
        skill_id="materials.linear_constitutive",
        skill_version="0.1.0",
        inputs=inputs,
        expected_result={
            "elastic_modulus": {"value": 200e9, "unit": "Pa"},
            "strain": 0.001,
            "stress": {"value": 2e8, "unit": "Pa"},
            "material": {
                "material_id": "steel_astm_a36",
                "property_id": "materials.steel_astm_a36.elastic_modulus",
                "property_name": "Structural steel (ASTM A36) — elastic_modulus",
                "references": ["ASTM A36 handbook nominal values"],
            },
        },
        tolerance=1e-9,
        source="closed form: sigma = E * epsilon = 200e9 * 0.001 = 2e8 Pa",
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_explicit_modulus_and_strain_from_deformation() -> None:
    # L0 = 2 m, dL = 0.002 m → epsilon = 0.001; E = 68.9e9 → sigma = 6.89e7
    out = implementation.execute(
        {
            "elastic_modulus": {"value": 68.9e9, "unit": "Pa"},
            "original_length": {"value": 2.0, "unit": "m"},
            "deformation": {"value": 0.002, "unit": "m"},
        }
    )["result"]
    assert out["strain"] == pytest.approx(0.001)
    assert out["stress"]["value"] == pytest.approx(68.9e6)
    assert "material" not in out


def test_unknown_material_id_raises() -> None:
    with pytest.raises(Exception, match="unknown material"):
        implementation.execute({"material_id": "unobtainium", "strain": 0.001})
