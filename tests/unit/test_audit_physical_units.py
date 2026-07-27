from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "audit_physical_units", _ROOT / "scripts" / "audit_physical_units.py"
)
assert _SPEC is not None and _SPEC.loader is not None
audit = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = audit
_SPEC.loader.exec_module(audit)


def _write_skill(root: Path, field: dict[str, object]) -> None:
    skill = root / "energy" / "fixture"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "skill.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "energy.fixture",
                "validation": {"dimensional": True, "physical": True},
            }
        ),
        encoding="utf-8",
    )
    schema = {
        "type": "object",
        "properties": {"power": field},
        "additionalProperties": False,
    }
    (skill / "input.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    (skill / "output.schema.json").write_text(
        json.dumps({"type": "object", "properties": {}, "additionalProperties": False}),
        encoding="utf-8",
    )


def _quantity() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {"value": {"type": "number"}, "unit": {"type": "string"}},
        "required": ["value", "unit"],
        "additionalProperties": False,
        "x-oec-unit": "W",
    }


def test_bare_physical_number_fails(tmp_path: Path) -> None:
    _write_skill(tmp_path, {"type": "number"})
    _, findings = audit.audit_tree(tmp_path)
    assert [finding.message for finding in findings] == ["bare numeric field is unclassified"]


def test_quantity_and_dimensionless_fields_pass(tmp_path: Path) -> None:
    _write_skill(tmp_path, _quantity())
    _, findings = audit.audit_tree(tmp_path)
    assert findings == []


def test_explicit_dimensionless_field_passes(tmp_path: Path) -> None:
    _write_skill(tmp_path, {"type": "number", "x-oec-dimensionless": True})
    _, findings = audit.audit_tree(tmp_path)
    assert findings == []


def test_legacy_branch_fails_even_with_generic_exception(tmp_path: Path) -> None:
    quantity = _quantity()
    field = {"oneOf": [{"type": "number"}, quantity], "x-oec-unit": "W"}
    _write_skill(tmp_path, field)
    _, findings = audit.audit_tree(tmp_path)
    assert [finding.message for finding in findings] == ["bare numeric field is unclassified"]
    field["x-oec-unit-exception"] = {"reason": "Legacy canonical input."}
    _write_skill(tmp_path, field)
    _, findings = audit.audit_tree(tmp_path)
    assert [finding.message for finding in findings] == ["bare numeric field is unclassified"]


def test_invalid_unit_fails(tmp_path: Path) -> None:
    field = _quantity()
    field["x-oec-unit"] = "definitely_not_a_unit"
    _write_skill(tmp_path, field)
    _, findings = audit.audit_tree(tmp_path)
    assert [finding.message for finding in findings] == [
        "invalid x-oec-unit 'definitely_not_a_unit'"
    ]
