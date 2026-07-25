"""Unit tests for :mod:`oec.execution.normalization`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oec.execution.normalization import apply_dimensional_normalization
from oec.skills.loader.frontmatter import SkillFrontMatter
from oec.skills.loader.models import LoadedSkill
from oec.skills.schemas.manifest import (
    EntrypointSpec,
    MethodRef,
    SchemaRefs,
    SkillManifest,
    SkillStatus,
)


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
                    "properties": {"value": {"type": "number"}, "unit": {"type": "string"}},
                    "x-oec-unit": "V",
                },
                "count": {"type": "integer"},
            },
        },
        output_schema={"type": "object"},
    )


def test_converts_declared_field_to_canonical_unit() -> None:
    skill = _make_skill()
    result = apply_dimensional_normalization(skill, {"voltage": {"value": 0.38, "unit": "kV"}})
    assert result["voltage"] == {"value": 380.0, "unit": "V"}


def test_already_canonical_unit_is_unchanged_in_value() -> None:
    skill = _make_skill()
    result = apply_dimensional_normalization(skill, {"voltage": {"value": 380.0, "unit": "V"}})
    assert result["voltage"] == {"value": 380.0, "unit": "V"}


def test_does_not_mutate_the_input_dict() -> None:
    skill = _make_skill()
    original = {"voltage": {"value": 0.38, "unit": "kV"}}
    apply_dimensional_normalization(skill, original)
    assert original == {"voltage": {"value": 0.38, "unit": "kV"}}


def test_fields_without_x_oec_unit_pass_through_unchanged() -> None:
    skill = _make_skill()
    result = apply_dimensional_normalization(skill, {"count": 7})
    assert result == {"count": 7}


def test_non_quantity_values_pass_through_unchanged() -> None:
    skill = _make_skill()
    result = apply_dimensional_normalization(skill, {"voltage": "not-a-quantity"})
    assert result == {"voltage": "not-a-quantity"}


def test_missing_field_is_a_no_op() -> None:
    skill = _make_skill()
    result = apply_dimensional_normalization(skill, {"count": 1})
    assert result == {"count": 1}


def test_no_properties_block_returns_inputs_unchanged() -> None:
    skill = _make_skill(input_schema={"type": "object"})
    inputs = {"voltage": {"value": 1.0, "unit": "V"}}
    assert apply_dimensional_normalization(skill, inputs) == inputs


def test_no_declared_units_returns_inputs_unchanged() -> None:
    skill = _make_skill(
        input_schema={"type": "object", "properties": {"count": {"type": "integer"}}}
    )
    inputs = {"count": 3}
    assert apply_dimensional_normalization(skill, inputs) == inputs


def test_other_fields_are_preserved_alongside_converted_ones() -> None:
    skill = _make_skill()
    result = apply_dimensional_normalization(
        skill, {"voltage": {"value": 0.38, "unit": "kV"}, "count": 3}
    )
    assert result == {"voltage": {"value": 380.0, "unit": "V"}, "count": 3}
