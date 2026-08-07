"""Small, versioned catalogue of universally defined scientific constants.

The catalogue deliberately starts small.  Each item embeds its source and
source version so an execution can preserve provenance without accepting a
memory-derived numerical constant.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict

from oec.kernel.units.quantity import QuantityValue

CATALOG_VERSION = "SI-2019"
SI_BROCHURE_9TH_EDITION = "BIPM SI Brochure, 9th edition (2019)"


class ScientificConstant(BaseModel):
    """A versioned constant with JSON-safe value and provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    symbol: str
    quantity: QuantityValue
    source: str
    source_version: str
    exact: bool


_CONSTANTS = MappingProxyType(
    {
        "speed_of_light_in_vacuum": ScientificConstant(
            name="speed of light in vacuum",
            symbol="c",
            quantity=QuantityValue(value=299_792_458.0, unit="m/s"),
            source=SI_BROCHURE_9TH_EDITION,
            source_version=CATALOG_VERSION,
            exact=True,
        ),
        "planck_constant": ScientificConstant(
            name="Planck constant",
            symbol="h",
            quantity=QuantityValue(value=6.626_070_15e-34, unit="J*s"),
            source=SI_BROCHURE_9TH_EDITION,
            source_version=CATALOG_VERSION,
            exact=True,
        ),
        "elementary_charge": ScientificConstant(
            name="elementary charge",
            symbol="e",
            quantity=QuantityValue(value=1.602_176_634e-19, unit="C"),
            source=SI_BROCHURE_9TH_EDITION,
            source_version=CATALOG_VERSION,
            exact=True,
        ),
    }
)


def constants() -> Mapping[str, ScientificConstant]:
    """Return the immutable catalogue of constants for ``CATALOG_VERSION``."""
    return _CONSTANTS


def get_constant(key: str) -> ScientificConstant:
    """Return a named constant or raise a clear ``KeyError`` for unknown keys."""
    try:
        return _CONSTANTS[key]
    except KeyError as exc:
        raise KeyError(f"unknown scientific constant {key!r}") from exc
