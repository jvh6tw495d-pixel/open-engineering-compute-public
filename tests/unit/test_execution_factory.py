"""Unit tests for :func:`oec.execution.factory.build_validators` (ADR 0014)."""

from __future__ import annotations

from pathlib import Path

import pytest

from oec.errors import SkillEntrypointError
from oec.execution.factory import build_validators
from oec.skills.loader.loader import load_skill
from oec.testing import write_skill_dir
from oec.validation.dimensions import DimensionalValidator, ResultDimensionalValidator
from oec.validation.invariants import InvariantValidator
from oec.validation.numerical import NumericalDiagnosticsValidator
from oec.validation.schema import SchemaValidator

_NO_EXTRA_VALIDATION = {
    "validation": {
        "schema": True,
        "dimensional": False,
        "mathematical": False,
        "physical": False,
        "numerical": False,
    }
}

_SINGLE_VALIDATOR_SOURCE = """
class FooValidator:
    layer = "mathematical"

    def validate(self, skill, normalized_inputs):
        return []
"""

_NO_MATCHING_CLASS_SOURCE = """
def not_a_validator():
    pass
"""

_TWO_MATCHING_CLASSES_SOURCE = """
class FirstValidator:
    layer = "mathematical"

    def validate(self, skill, normalized_inputs):
        return []


class SecondValidator:
    layer = "mathematical"

    def validate(self, skill, normalized_inputs):
        return []
"""


def _build(tmp_path: Path, *, overrides: dict, validation_py: str | None = None) -> Path:
    skill_dir = write_skill_dir(tmp_path, manifest_overrides=overrides)
    if validation_py is not None:
        (skill_dir / "validation.py").write_text(validation_py, encoding="utf-8")
    return skill_dir


def _with(*flags: str) -> dict:
    """``_NO_EXTRA_VALIDATION`` with the given policy flags flipped to True."""
    validation = {**_NO_EXTRA_VALIDATION["validation"]}
    for flag in flags:
        validation[flag] = True
    return {**_NO_EXTRA_VALIDATION, "validation": validation}


def test_schema_only_wires_schema_and_invariant(tmp_path: Path) -> None:
    skill_dir = _build(tmp_path, overrides=_NO_EXTRA_VALIDATION)
    skill = load_skill(skill_dir)

    input_validators, result_validators = build_validators(skill)

    assert [type(v) for v in input_validators] == [SchemaValidator]
    assert [type(v) for v in result_validators] == [InvariantValidator]


def test_dimensional_true_wires_dimensional_validator(tmp_path: Path) -> None:
    skill_dir = _build(tmp_path, overrides=_with("dimensional"))
    skill = load_skill(skill_dir)

    input_validators, _ = build_validators(skill)

    assert any(isinstance(v, DimensionalValidator) for v in input_validators)


def test_dimensional_true_wires_result_dimensional_validator(tmp_path: Path) -> None:
    skill_dir = _build(tmp_path, overrides=_with("dimensional"))
    skill = load_skill(skill_dir)

    _, result_validators = build_validators(skill)

    assert [type(v) for v in result_validators] == [
        InvariantValidator,
        ResultDimensionalValidator,
    ]


def test_physical_true_wires_nothing_extra(tmp_path: Path) -> None:
    skill_dir = _build(tmp_path, overrides=_with("physical"))
    skill = load_skill(skill_dir)

    input_validators, _ = build_validators(skill)

    assert [type(v) for v in input_validators] == [SchemaValidator]


def test_numerical_true_adds_numerical_diagnostics_validator(tmp_path: Path) -> None:
    skill_dir = _build(tmp_path, overrides=_with("numerical"))
    skill = load_skill(skill_dir)

    _, result_validators = build_validators(skill)

    assert [type(v) for v in result_validators] == [
        InvariantValidator,
        NumericalDiagnosticsValidator,
    ]


def test_invariant_validator_always_included_even_when_numerical_false(tmp_path: Path) -> None:
    skill_dir = _build(tmp_path, overrides=_NO_EXTRA_VALIDATION)
    skill = load_skill(skill_dir)

    _, result_validators = build_validators(skill)

    assert any(isinstance(v, InvariantValidator) for v in result_validators)


def test_mathematical_true_discovers_skill_validator(tmp_path: Path) -> None:
    skill_dir = _build(
        tmp_path, overrides=_with("mathematical"), validation_py=_SINGLE_VALIDATOR_SOURCE
    )
    skill = load_skill(skill_dir)

    input_validators, _ = build_validators(skill)

    assert [type(v).__name__ for v in input_validators] == ["SchemaValidator", "FooValidator"]


def test_mathematical_true_without_validation_file_raises(tmp_path: Path) -> None:
    skill_dir = _build(tmp_path, overrides=_with("mathematical"))
    skill = load_skill(skill_dir)

    with pytest.raises(SkillEntrypointError):
        build_validators(skill)


def test_mathematical_true_with_no_matching_class_raises(tmp_path: Path) -> None:
    skill_dir = _build(
        tmp_path, overrides=_with("mathematical"), validation_py=_NO_MATCHING_CLASS_SOURCE
    )
    skill = load_skill(skill_dir)

    with pytest.raises(SkillEntrypointError):
        build_validators(skill)


def test_mathematical_true_with_ambiguous_classes_raises(tmp_path: Path) -> None:
    skill_dir = _build(
        tmp_path, overrides=_with("mathematical"), validation_py=_TWO_MATCHING_CLASSES_SOURCE
    )
    skill = load_skill(skill_dir)

    with pytest.raises(SkillEntrypointError):
        build_validators(skill)
