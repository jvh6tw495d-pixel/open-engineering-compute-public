"""Unit tests for :class:`~oec.validation.schema.SchemaValidator`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
from oec.validation.schema import SchemaValidator


def _make_skill(
    *,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
) -> LoadedSkill:
    return LoadedSkill(
        manifest=SkillManifest(
            id="test.schema_skill",
            version="0.1.0",
            status=SkillStatus.EXPERIMENTAL,
            domain="test",
            title="Schema test skill",
            entrypoint=EntrypointSpec(module="implementation", function="execute"),
            schemas=SchemaRefs(input="input.schema.json", output="output.schema.json"),
            method=MethodRef(id="test", version="1", iterative=False),
        ),
        front_matter=SkillFrontMatter(
            id="test.schema_skill",
            version="0.1.0",
            status=SkillStatus.EXPERIMENTAL,
            domain="test",
            title="Schema test skill",
        ),
        path=Path("."),
        body="",
        input_schema={
            "type": "object",
            "properties": {"value": {"type": "number"}},
            "required": ["value"],
            "additionalProperties": False,
        }
        if input_schema is None
        else input_schema,
        output_schema={"type": "object"} if output_schema is None else output_schema,
    )


def test_valid_inputs_yield_no_outcomes() -> None:
    """Happy path: conforming inputs produce an empty list (implicit OK)."""
    skill = _make_skill()
    outcomes = SchemaValidator().validate(skill, {"value": 42.0})
    assert outcomes == []


def test_missing_required_property_is_error() -> None:
    skill = _make_skill()
    outcomes = SchemaValidator().validate(skill, {})
    assert len(outcomes) == 1
    assert outcomes[0].layer == "schema"
    assert outcomes[0].severity == Severity.ERROR
    assert "value" in outcomes[0].messages[0]
    assert "json_path" in outcomes[0].details


def test_wrong_type_is_error() -> None:
    skill = _make_skill()
    outcomes = SchemaValidator().validate(skill, {"value": "not-a-number"})
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.ERROR
    assert outcomes[0].layer == "schema"


def test_additional_property_is_error() -> None:
    skill = _make_skill()
    outcomes = SchemaValidator().validate(skill, {"value": 1.0, "extra": True})
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.ERROR


def test_multiple_errors_are_all_reported() -> None:
    """A single validate() call surfaces every schema violation, not just the first."""
    skill = _make_skill(
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "string"},
            },
            "required": ["a", "b"],
            "additionalProperties": False,
        }
    )
    outcomes = SchemaValidator().validate(skill, {"a": "wrong", "c": 1})
    assert len(outcomes) >= 2
    assert all(o.severity == Severity.ERROR for o in outcomes)
    assert all(o.layer == "schema" for o in outcomes)


def test_empty_schema_accepts_anything() -> None:
    skill = _make_skill(input_schema={})
    outcomes = SchemaValidator().validate(skill, {"anything": [1, 2, 3]})
    assert outcomes == []


def test_layer_class_attribute() -> None:
    assert SchemaValidator.layer == "schema"
