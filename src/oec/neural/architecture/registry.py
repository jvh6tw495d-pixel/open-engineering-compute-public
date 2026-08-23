"""Governed block registry (ADR 0047). Fail-closed on unknown / duplicate ids."""

from __future__ import annotations

from collections.abc import Iterable

from oec.neural.architecture.errors import (
    DuplicateBlockError,
    UnknownBlockError,
    UnknownFamilyError,
)
from oec.neural.architecture.specs import BlockSpec, RegistrySnapshot
from oec.neural.architecture.types import NeuralFamily, TensorKind


class BlockRegistry:
    def __init__(self, version: str = "0.1.0") -> None:
        self.version = version
        self._blocks: dict[str, BlockSpec] = {}

    def register(self, spec: BlockSpec) -> None:
        if spec.id in self._blocks:
            raise DuplicateBlockError(f"duplicate block id: {spec.id}")
        self._blocks[spec.id] = spec

    def register_many(self, specs: Iterable[BlockSpec]) -> None:
        for spec in specs:
            self.register(spec)

    def get(self, block_id: str) -> BlockSpec:
        try:
            return self._blocks[block_id]
        except KeyError as exc:
            raise UnknownBlockError(f"unknown block id: {block_id}") from exc

    def list(self) -> tuple[BlockSpec, ...]:
        return tuple(self._blocks[key] for key in sorted(self._blocks))

    def by_family(self, family: object) -> tuple[BlockSpec, ...]:
        resolved = _require_family(family)
        return tuple(spec for spec in self.list() if spec.family == resolved)

    def compatible_blocks(
        self,
        *,
        input_kind: TensorKind,
        output_kind: TensorKind | None = None,
    ) -> tuple[BlockSpec, ...]:
        out: list[BlockSpec] = []
        for spec in self.list():
            if not spec.accepts(input_kind):
                continue
            if output_kind is not None and spec.output_kind != output_kind:
                continue
            out.append(spec)
        return tuple(out)

    def snapshot(self) -> RegistrySnapshot:
        blocks: list[dict[str, object]] = []
        for spec in self.list():
            payload = spec.model_dump(mode="json")
            payload["input_kinds"] = sorted(payload["input_kinds"])
            payload["capabilities"] = sorted(payload["capabilities"])
            blocks.append(payload)
        return RegistrySnapshot(version=self.version, blocks=tuple(blocks))


def _require_family(family: object) -> NeuralFamily:
    if isinstance(family, NeuralFamily):
        return family
    if isinstance(family, str):
        try:
            return NeuralFamily(family)
        except ValueError as exc:
            raise UnknownFamilyError(
                f"unknown neural family: {family!r}",
                details={"family": family},
            ) from exc
    raise UnknownFamilyError(
        f"unknown neural family: {family!r}",
        details={"family": repr(family), "type": type(family).__name__},
    )
