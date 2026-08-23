"""Block and compatibility contracts (ADR 0047). Importable without torch."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from oec.neural.architecture.types import BlockCategory, NeuralFamily, TensorKind


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
    experimental: bool = True
    notes: str = ""

    def accepts(self, kind: TensorKind) -> bool:
        return TensorKind.ANY in self.input_kinds or kind in self.input_kinds


class CompatibilityResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    compatible: bool
    reason: str
    suggested_adapters: tuple[str, ...] = ()


class RegistrySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    blocks: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
