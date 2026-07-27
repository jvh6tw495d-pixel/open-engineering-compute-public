"""Unit tests for :class:`~oec.validation.dimensions.DimensionalValidator`."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest

from oec.skills.loader.frontmatter import SkillFrontMatter
from oec.skills.loader.models import LoadedSkill
from oec.skills.schemas.manifest import (
    EntrypointSpec,
    MethodRef,
    SchemaRefs,
    SkillManifest,
    SkillStatus,
)
from oec.validation.base import Severity
from oec.validation.dimensions import DimensionalValidator


def _make_skill(*, input_schema: dict[str, Any] | None = None) -> LoadedSkill:
    return LoadedSkill(
        manifest=SkillManifest(
            id="test.dimensional_skill",
            version="0.1.0",
            status=SkillStatus.EXPERIMENTAL,
            domain="test",
            title="Dimensional test skill",
            entrypoint=EntrypointSpec(module="implementation", function="execute"),
            schemas=SchemaRefs(input="input.schema.json", output="output.schema.json"),
            method=MethodRef(id="test", version="1", iterative=False),
        ),
        front_matter=SkillFrontMatter(
            id="test.dimensional_skill",
            version="0.1.0",
            status=SkillStatus.EXPERIMENTAL,
            domain="test",
            title="Dimensional test skill",
        ),
        path=Path("."),
        body="",
        input_schema=input_schema
        or {
            "type": "object",
            "properties": {
                "voltage": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "unit": {"type": "string"},
                    },
                    "x-oec-unit": "V",
                },
                "count": {"type": "integer"},
            },
        },
        output_schema={"type": "object"},
    )


def test_compatible_quantity_passes() -> None:
    skill = _make_skill()
    outcomes = DimensionalValidator().validate(
        skill, {"voltage": {"value": 0.38, "unit": "kV"}, "count": 3}
    )
    assert outcomes == []


def test_same_unit_passes() -> None:
    skill = _make_skill()
    outcomes = DimensionalValidator().validate(skill, {"voltage": {"value": 380.0, "unit": "V"}})
    assert outcomes == []


def test_incompatible_unit_is_error() -> None:
    skill = _make_skill()
    outcomes = DimensionalValidator().validate(skill, {"voltage": {"value": 10.0, "unit": "A"}})
    assert len(outcomes) == 1
    assert outcomes[0].layer == "dimensional"
    assert outcomes[0].severity == Severity.ERROR
    assert "A" in outcomes[0].messages[0]
    assert "V" in outcomes[0].messages[0]
    assert outcomes[0].details["unit"] == "A"
    assert outcomes[0].details["expected_unit"] == "V"


def test_unknown_unit_is_error() -> None:
    skill = _make_skill()
    outcomes = DimensionalValidator().validate(
        skill, {"voltage": {"value": 1.0, "unit": "notaunit"}}
    )
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.ERROR
    assert outcomes[0].details["field"] == "voltage"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_quantity_value_is_error(value: float) -> None:
    skill = _make_skill()
    outcomes = DimensionalValidator().validate(skill, {"voltage": {"value": value, "unit": "V"}})
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.ERROR


def test_plain_numbers_are_ignored() -> None:
    """Non-{value, unit} fields are not physical quantities — not an error."""
    skill = _make_skill()
    outcomes = DimensionalValidator().validate(skill, {"count": 7, "label": "ok"})
    assert outcomes == []


def test_partial_quantity_dict_is_ignored() -> None:
    """Only exact {value, unit} keys are treated as quantities."""
    skill = _make_skill()
    outcomes = DimensionalValidator().validate(
        skill, {"voltage": {"value": 1.0, "unit": "V", "extra": True}}
    )
    assert outcomes == []


def test_quantity_without_x_oec_unit_is_only_shape_checked() -> None:
    skill = _make_skill(
        input_schema={
            "type": "object",
            "properties": {
                "power": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "unit": {"type": "string"},
                    },
                }
            },
        }
    )
    outcomes = DimensionalValidator().validate(skill, {"power": {"value": 75.0, "unit": "kW"}})
    assert outcomes == []


def test_valid_quantity_shape_with_bad_unit_still_errors_without_x_oec_unit() -> None:
    skill = _make_skill(input_schema={"type": "object", "properties": {"q": {"type": "object"}}})
    outcomes = DimensionalValidator().validate(skill, {"q": {"value": 1.0, "unit": ""}})
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.ERROR


def test_missing_or_non_dict_properties_still_shape_checks_quantities() -> None:
    """No properties block (or a non-object one) means no x-oec-unit checks."""
    skill = _make_skill(input_schema={"type": "object", "properties": "not-a-map"})
    outcomes = DimensionalValidator().validate(skill, {"voltage": {"value": 1.0, "unit": "V"}})
    assert outcomes == []


def test_non_dict_field_schema_skips_unit_compatibility() -> None:
    skill = _make_skill(
        input_schema={"type": "object", "properties": {"voltage": "not-an-object-schema"}}
    )
    outcomes = DimensionalValidator().validate(skill, {"voltage": {"value": 1.0, "unit": "A"}})
    # Valid quantity shape, but no dict schema → no x-oec-unit check.
    assert outcomes == []


def test_array_quantity_reports_incompatible_item_location() -> None:
    skill = _make_skill(
        input_schema={
            "type": "object",
            "properties": {
                "power_values": {
                    "type": "array",
                    "items": {"type": "object"},
                    "x-oec-unit": "W",
                }
            },
        }
    )
    outcomes = DimensionalValidator().validate(
        skill,
        {"power_values": [{"value": 1.0, "unit": "W"}, {"value": 2.0, "unit": "A"}]},
    )
    assert len(outcomes) == 1
    assert outcomes[0].details["field"] == "power_values[1]"
    assert outcomes[0].details["expected_unit"] == "W"


def test_layer_class_attribute() -> None:
    assert DimensionalValidator.layer == "dimensional"
