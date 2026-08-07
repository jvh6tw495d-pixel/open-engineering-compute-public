"""Unit tests for :mod:`oec.kernel.units.schema`."""

from __future__ import annotations

from oec.kernel.units.schema import declared_units, is_quantity_dict


def test_declared_units_collects_x_oec_unit_fields() -> None:
    properties = {
        "voltage": {"type": "object", "x-oec-unit": "V"},
        "current": {"type": "object", "x-oec-unit": "A"},
        "count": {"type": "integer"},
    }
    assert declared_units(properties) == {"voltage": "V", "current": "A"}


def test_declared_units_ignores_non_string_x_oec_unit() -> None:
    properties = {"voltage": {"x-oec-unit": 123}}
    assert declared_units(properties) == {}


def test_declared_units_ignores_non_dict_field_schemas() -> None:
    properties = {"voltage": "not-an-object-schema"}
    assert declared_units(properties) == {}


def test_declared_units_empty_properties() -> None:
    assert declared_units({}) == {}


def test_is_quantity_dict_accepts_exact_value_unit_keys() -> None:
    assert is_quantity_dict({"value": 1.0, "unit": "V"}) is True


def test_is_quantity_dict_rejects_extra_keys() -> None:
    assert is_quantity_dict({"value": 1.0, "unit": "V", "extra": True}) is False


def test_is_quantity_dict_rejects_missing_keys() -> None:
    assert is_quantity_dict({"value": 1.0}) is False


def test_is_quantity_dict_rejects_non_dict() -> None:
    assert is_quantity_dict(5) is False
    assert is_quantity_dict("V") is False
    assert is_quantity_dict(None) is False
