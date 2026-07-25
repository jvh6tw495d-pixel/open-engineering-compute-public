"""Unit tests for :class:`~oec.validation.invariants.InvariantValidator`."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest

from oec.common import VersionedRef
from oec.skills.loader.frontmatter import SkillFrontMatter
from oec.skills.loader.models import LoadedSkill
from oec.skills.schemas.manifest import (
    EntrypointSpec,
    SchemaRefs,
    SkillManifest,
    SkillStatus,
)
from oec.validation.base import Severity
from oec.validation.invariants import InvariantValidator


def _make_skill(*, output_schema: dict[str, Any] | None = None) -> LoadedSkill:
    return LoadedSkill(
        manifest=SkillManifest(
            id="test.invariant_skill",
            version="0.1.0",
            status=SkillStatus.EXPERIMENTAL,
            domain="test",
            title="Invariant test skill",
            entrypoint=EntrypointSpec(module="implementation", function="execute"),
            schemas=SchemaRefs(input="input.schema.json", output="output.schema.json"),
            method=VersionedRef(id="test", version="1"),
        ),
        front_matter=SkillFrontMatter(
            id="test.invariant_skill",
            version="0.1.0",
            status=SkillStatus.EXPERIMENTAL,
            domain="test",
            title="Invariant test skill",
        ),
        path=Path("."),
        body="",
        input_schema={"type": "object"},
        output_schema=output_schema
        if output_schema is not None
        else {
            "type": "object",
            "properties": {"voltage_drop": {"type": "number"}},
            "required": ["voltage_drop"],
            "additionalProperties": False,
        },
    )


def _validate(
    result: dict[str, Any],
    *,
    output_schema: dict[str, Any] | None = None,
) -> list:
    return InvariantValidator().validate(_make_skill(output_schema=output_schema), {}, result, {})


def test_finite_conforming_result_is_ok() -> None:
    assert _validate({"voltage_drop": 12.5}) == []


def test_nan_is_error_with_path() -> None:
    outcomes = _validate({"voltage_drop": math.nan}, output_schema={})
    assert len(outcomes) == 1
    assert outcomes[0].layer == "invariants"
    assert outcomes[0].severity == Severity.ERROR
    assert outcomes[0].details["path"] == "result.voltage_drop"
    assert "non-finite" in outcomes[0].messages[0]


@pytest.mark.parametrize("value", [math.inf, -math.inf])
def test_infinity_is_error(value: float) -> None:
    outcomes = _validate({"voltage_drop": value}, output_schema={})
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.ERROR
    assert outcomes[0].details["path"] == "result.voltage_drop"


def test_nested_non_finite_path() -> None:
    outcomes = _validate(
        {"inner": {"values": [1.0, math.nan, 3.0]}},
        output_schema={},
    )
    assert len(outcomes) == 1
    assert outcomes[0].details["path"] == "result.inner.values[1]"


def test_multiple_non_finite_values() -> None:
    outcomes = _validate(
        {"a": math.nan, "b": math.inf},
        output_schema={},
    )
    assert len(outcomes) == 2
    paths = {o.details["path"] for o in outcomes}
    assert paths == {"result.a", "result.b"}


def test_output_schema_violation_is_error() -> None:
    outcomes = _validate({})  # missing required voltage_drop
    assert len(outcomes) >= 1
    assert all(o.severity == Severity.ERROR for o in outcomes)
    assert all(o.layer == "invariants" for o in outcomes)


def test_output_schema_wrong_type() -> None:
    outcomes = _validate({"voltage_drop": "nope"})
    assert len(outcomes) == 1
    assert outcomes[0].severity == Severity.ERROR


def test_empty_output_schema_skips_shape_check() -> None:
    """Empty output_schema means no shape invariant — only finiteness applies."""
    outcomes = _validate({"anything": {"nested": [1, 2, 3]}}, output_schema={})
    assert outcomes == []


def test_non_finite_and_schema_errors_combine() -> None:
    outcomes = _validate({"extra": math.nan})  # missing voltage_drop + nan
    assert len(outcomes) >= 2
    assert any("non-finite" in o.messages[0] for o in outcomes)
    assert any("json_path" in o.details or "required" in o.messages[0].lower() for o in outcomes)


def test_layer_class_attribute() -> None:
    assert InvariantValidator.layer == "invariants"
