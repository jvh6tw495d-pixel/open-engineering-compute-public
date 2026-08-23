"""Block and compatibility contracts (ADR 0047). Importable without torch."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.types import BlockCategory, NeuralFamily, TensorKind

KNOWN_PARAMETER_KINDS = frozenset({"int", "float", "bool", "enum", "str"})


class BlockParameterSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    kind: str
    required: bool = False
    default: Any = None
    minimum: float | int | None = None
    maximum: float | int | None = None
    choices: tuple[Any, ...] = ()


class BlockSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    display_name: str
    family: NeuralFamily
    category: BlockCategory
    input_kinds: frozenset[TensorKind]
    output_kind: TensorKind
    parameters: tuple[BlockParameterSpec, ...] = ()
    capabilities: frozenset[str] = frozenset()
    backend_requirements: tuple[str, ...] = ()
    input_ports: tuple[str, ...] = ("in",)
    output_ports: tuple[str, ...] = ("out",)
    experimental: bool = True
    notes: str = ""

    @model_validator(mode="after")
    def _single_output_port(self) -> BlockSpec:
        if self.output_ports != ("out",):
            raise ValueError(
                f"block {self.id!r} output_ports={self.output_ports!r}; "
                "only ('out',) is supported until a multi-output protocol exists"
            )
        return self

    def accepts(self, kind: TensorKind) -> bool:
        return TensorKind.ANY in self.input_kinds or kind in self.input_kinds

    def validate_config(self, config: Mapping[str, Any] | None) -> dict[str, Any]:
        """Fail-closed against ``parameters``; materialize declared defaults."""
        raw = dict(config or {})
        declared = {item.name: item for item in self.parameters}
        unknown = sorted(name for name in raw if name not in declared)
        if unknown:
            raise ArchitectureValidationError(
                f"unknown config keys for block {self.id!r}: {unknown}",
                details={"block_id": self.id, "unknown_keys": unknown},
            )
        normalized: dict[str, Any] = {}
        for spec in self.parameters:
            if spec.name in raw:
                normalized[spec.name] = _coerce_parameter(self.id, spec, raw[spec.name])
                continue
            if spec.required and spec.default is None:
                raise ArchitectureValidationError(
                    f"missing required parameter {spec.name!r} for block {self.id!r}",
                    details={"block_id": self.id, "parameter": spec.name},
                )
            if spec.default is not None:
                normalized[spec.name] = _coerce_parameter(self.id, spec, spec.default)
        _validate_attention_head_split(self.id, normalized)
        return normalized


def _validate_attention_head_split(block_id: str, normalized: dict[str, Any]) -> None:
    """d_model must split evenly across nhead — Torch's own constraint, but we
    fail closed in the IR instead of surfacing a raw PyTorch exception."""
    if "d_model" not in normalized or "nhead" not in normalized:
        return
    d_model = normalized["d_model"]
    nhead = normalized["nhead"]
    if nhead > d_model or d_model % nhead != 0:
        raise ArchitectureValidationError(
            f"block {block_id!r} requires d_model % nhead == 0 and nhead <= d_model "
            f"(d_model={d_model}, nhead={nhead})",
            details={"block_id": block_id, "d_model": d_model, "nhead": nhead},
        )


def _coerce_parameter(block_id: str, spec: BlockParameterSpec, value: Any) -> Any:
    kind = spec.kind
    details = {"block_id": block_id, "parameter": spec.name, "kind": kind, "value": value}
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ArchitectureValidationError(
                f"parameter {spec.name!r} for block {block_id!r} must be int",
                details=details,
            )
        return _check_bounds(block_id, spec, value, details)
    if kind == "float":
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ArchitectureValidationError(
                f"parameter {spec.name!r} for block {block_id!r} must be float",
                details=details,
            )
        return _check_bounds(block_id, spec, float(value), details)
    if kind == "bool":
        if not isinstance(value, bool):
            raise ArchitectureValidationError(
                f"parameter {spec.name!r} for block {block_id!r} must be bool",
                details=details,
            )
        return value
    if kind in {"enum", "str"}:
        if not isinstance(value, str):
            raise ArchitectureValidationError(
                f"parameter {spec.name!r} for block {block_id!r} must be str",
                details=details,
            )
        if spec.choices and value not in spec.choices:
            raise ArchitectureValidationError(
                f"parameter {spec.name!r} for block {block_id!r} is not in choices",
                details={**details, "choices": list(spec.choices)},
            )
        return value
    raise ArchitectureValidationError(
        f"unsupported parameter kind {kind!r} for block {block_id!r}",
        details=details,
    )


def _check_bounds(
    block_id: str,
    spec: BlockParameterSpec,
    number: int | float,
    details: dict[str, Any],
) -> int | float:
    if spec.minimum is not None and number < spec.minimum:
        raise ArchitectureValidationError(
            f"parameter {spec.name!r} for block {block_id!r} is below minimum {spec.minimum}",
            details={**details, "minimum": spec.minimum},
        )
    if spec.maximum is not None and number > spec.maximum:
        raise ArchitectureValidationError(
            f"parameter {spec.name!r} for block {block_id!r} is above maximum {spec.maximum}",
            details={**details, "maximum": spec.maximum},
        )
    return number


class CompatibilityResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    compatible: bool
    reason: str
    suggested_adapters: tuple[str, ...] = ()


class RegistrySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    blocks: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
