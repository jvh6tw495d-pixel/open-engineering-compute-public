"""JSON Schema for OPS v0.1 (Phase C)."""

from __future__ import annotations

from typing import Any

OPS_SCHEMA_VERSION = "0.1.0"

OPS_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "OEC Problem Specification",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "ops_version",
        "problem_class",
        "sense",
        "variables",
        "constraints",
        "objective",
    ],
    "properties": {
        "ops_version": {"type": "string", "const": OPS_SCHEMA_VERSION},
        "problem_class": {"type": "string", "enum": ["lp", "milp"]},
        "sense": {"type": "string", "enum": ["min", "max"]},
        "name": {"type": "string"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
        "variables": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name"],
                "properties": {
                    "name": {
                        "type": "string",
                        "minLength": 1,
                        "pattern": "^[A-Za-z_][A-Za-z0-9_]*$",
                    },
                    "kind": {
                        "type": "string",
                        "enum": ["continuous", "integer", "binary"],
                        "default": "continuous",
                    },
                    "lower": {"type": ["number", "null"]},
                    "upper": {"type": ["number", "null"]},
                    "objective_coeff": {"type": "number", "default": 0},
                },
            },
        },
        "constraints": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "coeffs", "sense", "rhs"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "coeffs": {
                        "type": "object",
                        "additionalProperties": {"type": "number"},
                        "minProperties": 1,
                    },
                    "sense": {"type": "string", "enum": ["<=", ">=", "="]},
                    "rhs": {"type": "number"},
                },
            },
        },
        "objective": {
            "type": "object",
            "additionalProperties": False,
            "required": ["coeffs"],
            "properties": {
                "coeffs": {
                    "type": "object",
                    "additionalProperties": {"type": "number"},
                },
                "offset": {"type": "number", "default": 0},
            },
        },
        "execution_limits": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "time_limit_seconds": {"type": "number", "exclusiveMinimum": 0},
            },
        },
    },
}
