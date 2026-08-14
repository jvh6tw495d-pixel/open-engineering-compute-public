"""Unit tests for post-execution dimensional output enforcement."""

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
from oec.validation.dimensions import ResultDimensionalValidator


def _make_skill(*, output_schema: dict[str, Any]) -> LoadedSkill:
    return LoadedSkill(
        manifest=SkillManifest(
            id="test.output_dimensions",
            version="0.1.0",
            status=SkillStatus.EXPERIMENTAL,
            domain="test",
            title="Output dimensions test skill",
            entrypoint=EntrypointSpec(module="implementation", function="execute"),
            schemas=SchemaRefs(input="input.schema.json", output="output.schema.json"),
            method=MethodRef(id="test", version="1", iterative=False),
        ),
        front_matter=SkillFrontMatter(
            id="test.output_dimensions",
            version="0.1.0",
            status=SkillStatus.EXPERIMENTAL,
            domain="test",
            title="Output dimensions test skill",
        ),
        path=Path("."),
        body="",
        input_schema={"type": "object"},
        output_schema=output_schema,
    )


def _declared_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "power": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string"},
                },
                "x-oec-unit": "W",
            },
            "label": {"type": "string"},
        },
    }


def _validate(result: dict[str, Any], *, output_schema: dict[str, Any] | None = None) -> list:
    return ResultDimensionalValidator().validate(
        _make_skill(output_schema=output_schema or _declared_output_schema()), {}, result, {}
    )


def test_declared_canonical_quantity_output_passes() -> None:
    assert _validate({"power": {"value": 75.0, "unit": "W"}, "label": "ok"}) == []


def test_declared_compatible_but_noncanonical_output_unit_is_error() -> None:
    outcomes = _validate({"power": {"value": 0.075, "unit": "kW"}})

    assert len(outcomes) == 1
    assert outcomes[0].layer == "dimensional"
    assert outcomes[0].severity is Severity.ERROR
    assert outcomes[0].details == {
        "field": "power",
        "unit": "kW",
        "expected_unit": "W",
        "reason": "noncanonical_output_unit",
    }


def test_unit_const_is_enforced_without_x_oec_unit_extension() -> None:
    schema = {
        "type": "object",
        "properties": {
            "power": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string", "const": "W"},
                },
            }
        },
    }
    outcomes = _validate(
        {"power": {"value": 0.075, "unit": "kW"}},
        output_schema=schema,
    )
    assert len(outcomes) == 1
    assert outcomes[0].details["reason"] == "noncanonical_output_unit"
    assert outcomes[0].details["expected_unit"] == "W"


@pytest.mark.parametrize(
    "raw",
    [
        75.0,
        {"value": 75.0},
        {"unit": "W"},
        {"value": 75.0, "unit": "W", "extra": True},
    ],
)
def test_declared_quantity_output_fails_closed_for_malformed_objects(raw: Any) -> None:
    outcomes = _validate({"power": raw})

    assert len(outcomes) == 1
    assert outcomes[0].severity is Severity.ERROR
    assert outcomes[0].details["field"] == "power"
    assert outcomes[0].details["reason"] == "malformed_quantity_output"


@pytest.mark.parametrize("unit", ["", "not-a-unit"])
def test_invalid_quantity_dto_output_is_error(unit: str) -> None:
    outcomes = _validate({"power": {"value": 75.0, "unit": unit}})

    assert len(outcomes) == 1
    assert outcomes[0].severity is Severity.ERROR
    assert outcomes[0].details == {"field": "power", "reason": "invalid_quantity_output"}


def test_non_finite_quantity_output_is_error() -> None:
    outcomes = _validate({"power": {"value": math.nan, "unit": "W"}})

    assert len(outcomes) == 1
    assert outcomes[0].severity is Severity.ERROR


def test_exact_quantity_output_without_unit_declaration_is_still_validated() -> None:
    schema = {"type": "object", "properties": {"measured": {"type": "object"}}}
    outcomes = _validate({"measured": {"value": 1.0, "unit": "not-a-unit"}}, output_schema=schema)

    assert len(outcomes) == 1
    assert outcomes[0].details == {"field": "measured", "reason": "invalid_quantity_output"}


def test_nonphysical_outputs_are_unchanged() -> None:
    assert _validate({"label": "ok", "metadata": {"value": "display value"}}) == []


def test_missing_optional_declared_quantity_is_left_to_schema_validator() -> None:
    assert _validate({"label": "ok"}) == []


def test_layer_class_attribute() -> None:
    assert ResultDimensionalValidator.layer == "dimensional"


def _array_unit_schema() -> dict[str, Any]:
    """Schema shape used by battery.soc_trajectory.energy_delta (array + x-oec-unit)."""
    return {
        "type": "object",
        "properties": {
            "energy_delta": {
                "type": "array",
                "items": {"type": "number", "x-oec-unit": "Wh"},
                "x-oec-unit": "Wh",
            },
            "label": {"type": "string"},
        },
    }


def test_declared_physical_series_array_of_numbers_passes() -> None:
    assert (
        _validate(
            {"energy_delta": [10.0, 5.0, -2.5], "label": "ok"},
            output_schema=_array_unit_schema(),
        )
        == []
    )


def test_declared_physical_series_empty_array_passes() -> None:
    assert _validate({"energy_delta": []}, output_schema=_array_unit_schema()) == []


@pytest.mark.parametrize(
    "raw",
    [
        10.0,
        {"value": 10.0, "unit": "Wh"},
        [10.0, True],
        [10.0, "1"],
        [None],
        [{"value": 10.0, "unit": "Wh"}],
    ],
)
def test_declared_physical_series_rejects_non_numeric_items(raw: Any) -> None:
    outcomes = _validate({"energy_delta": raw}, output_schema=_array_unit_schema())

    assert len(outcomes) == 1
    assert outcomes[0].severity is Severity.ERROR
    assert outcomes[0].details == {
        "field": "energy_delta",
        "reason": "malformed_quantity_series_output",
    }
