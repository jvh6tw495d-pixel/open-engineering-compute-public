#!/usr/bin/env python3
"""Audit physical skill schemas for explicit unit classifications."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from oec.kernel.units.quantity import QuantityValue

_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _ROOT / "skills"

# Existing dimensionless electrical contract names. New schemas should prefer
# the machine-readable ``x-oec-dimensionless`` annotation.
_KNOWN_DIMENSIONLESS = frozenset(
    {
        "desired_power_factor",
        "efficiency",
        "existing_power_factor",
        "load_factor",
        "loading_percent",
        "overload_threshold_percent",
        "phase_count",
        "power_factor",
        "soc",
        "soc_next",
        "value_pu",
        "voltage_drop_percent",
    }
)
_DYNAMIC_UNIT_EXCEPTIONS = {
    (
        "electrical.per_unit_conversion",
        "input.schema.json",
        "value",
    ): "Unit depends on quantity_kind and is validated by the skill.",
    (
        "electrical.per_unit_conversion",
        "output.schema.json",
        "value_actual",
    ): "Unit depends on quantity_kind.",
}


@dataclass(frozen=True)
class Finding:
    skill: str
    schema: str
    field: str
    message: str

    def format(self) -> str:
        return f"ERROR: {self.skill}: {self.schema}:{self.field}: {self.message}"


def _is_numeric(schema: object) -> bool:
    if not isinstance(schema, dict):
        return False
    schema_type = schema.get("type")
    if isinstance(schema_type, str) and schema_type in {"number", "integer"}:
        return True
    if schema.get("type") == "array":
        return _is_numeric(schema.get("items"))
    return any(_is_numeric(option) for option in schema.get("oneOf", []))


def _is_quantity(schema: object) -> bool:
    if not isinstance(schema, dict):
        return False
    required = schema.get("required")
    properties = schema.get("properties")
    if (
        schema.get("type") == "object"
        and isinstance(required, list)
        and set(required) == {"value", "unit"}
        and isinstance(properties, dict)
        and properties.get("value", {}).get("type") == "number"
        and properties.get("unit", {}).get("type") == "string"
        and schema.get("additionalProperties") is False
    ):
        return True
    if schema.get("type") == "array":
        return _is_quantity(schema.get("items"))
    return any(_is_quantity(option) for option in schema.get("oneOf", []))


def audit_schema(skill: str, name: str, schema: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return [Finding(skill, name, "$", "object schema must declare properties")]

    for field, field_schema in properties.items():
        if not isinstance(field_schema, dict) or not (
            _is_numeric(field_schema) or _is_quantity(field_schema)
        ):
            continue
        dimensionless = field_schema.get("x-oec-dimensionless") is True
        if field in _KNOWN_DIMENSIONLESS:
            dimensionless = True
        quantity = _is_quantity(field_schema)
        unit = field_schema.get("x-oec-unit")
        if unit is None and quantity:
            unit_schema = field_schema.get("properties", {}).get("unit", {})
            if isinstance(unit_schema, dict):
                unit = unit_schema.get("const")
        registry_exception = _DYNAMIC_UNIT_EXCEPTIONS.get((skill, name, field))

        if dimensionless:
            continue
        if quantity and _is_numeric(field_schema):
            findings.append(Finding(skill, name, field, "bare numeric field is unclassified"))
            continue
        # Bare numeric / numeric arrays may carry an explicit x-oec-unit (e.g.
        # energy series in Wh) without using the {value, unit} quantity object.
        if not quantity:
            if isinstance(unit, str) and unit.strip():
                try:
                    QuantityValue(value=0.0, unit=unit)
                except ValidationError:
                    findings.append(Finding(skill, name, field, f"invalid x-oec-unit {unit!r}"))
                continue
            findings.append(Finding(skill, name, field, "bare numeric field is unclassified"))
            continue
        if (not isinstance(unit, str) or not unit.strip()) and not registry_exception:
            findings.append(Finding(skill, name, field, "quantity field lacks x-oec-unit"))
        elif not registry_exception:
            try:
                QuantityValue(value=0.0, unit=unit)
            except ValidationError:
                findings.append(Finding(skill, name, field, f"invalid x-oec-unit {unit!r}"))
    return findings


def audit_tree(skills_root: Path) -> tuple[int, list[Finding]]:
    scanned = 0
    findings: list[Finding] = []
    for manifest_path in sorted(skills_root.rglob("skill.yaml")):
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            continue
        validation = manifest.get("validation", {})
        if not isinstance(validation, dict) or not (
            validation.get("dimensional") or validation.get("physical")
        ):
            continue
        scanned += 1
        skill_id = str(manifest.get("id", manifest_path.parent.as_posix()))
        for schema_name in ("input.schema.json", "output.schema.json"):
            path = manifest_path.parent / schema_name
            schema = json.loads(path.read_text(encoding="utf-8"))
            findings.extend(audit_schema(skill_id, schema_name, schema))
    return scanned, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", type=Path, default=_SKILLS)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    root = args.skills_root if args.skills_root.is_absolute() else _ROOT / args.skills_root
    scanned, findings = audit_tree(root)
    if args.json_output:
        print(
            json.dumps(
                {
                    "skills_scanned": scanned,
                    "errors": [finding.__dict__ for finding in findings],
                },
                indent=2,
            )
        )
    else:
        print(f"OEC physical unit audit: {scanned} physical skill(s), {len(findings)} error(s)")
        for finding in findings:
            print(finding.format())
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
