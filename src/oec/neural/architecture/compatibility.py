"""Connection compatibility — explicit adapters only (ADR 0047)."""

from __future__ import annotations

from oec.neural.architecture.registry import BlockRegistry
from oec.neural.architecture.specs import BlockSpec, CompatibilityResult
from oec.neural.architecture.types import BlockCategory, TensorKind


def _adapter_candidates(
    registry: BlockRegistry,
    source_kind: TensorKind,
    target: BlockSpec,
) -> tuple[str, ...]:
    direct: list[str] = []
    for spec in registry.list():
        if spec.category != BlockCategory.ADAPTER:
            continue
        if spec.accepts(source_kind) and target.accepts(spec.output_kind):
            direct.append(spec.id)
    return tuple(sorted(direct))


def check_connection(
    source: BlockSpec,
    target: BlockSpec,
    registry: BlockRegistry,
) -> CompatibilityResult:
    if len(target.input_ports) != 1:
        return CompatibilityResult(
            compatible=False,
            reason=(
                f"{target.id} requires named ports {list(target.input_ports)}; "
                "unary sequential edges are not representable"
            ),
        )
    if target.accepts(source.output_kind):
        return CompatibilityResult(
            compatible=True,
            reason=(f"{source.id} outputs {source.output_kind.value}; {target.id} accepts it"),
        )
    adapters = _adapter_candidates(registry, source.output_kind, target)
    accepted = sorted(kind.value for kind in target.input_kinds)
    return CompatibilityResult(
        compatible=False,
        reason=(
            f"{source.id} outputs {source.output_kind.value}, but {target.id} accepts {accepted}"
        ),
        suggested_adapters=adapters,
    )
