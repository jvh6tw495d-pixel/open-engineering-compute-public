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
    """Tensor-kind compatibility for a single edge.

    Arity (how many named ports a multi-port target needs wired, and by
    whom) is a graph-level concern checked by
    ``ArchitectureGraph.validate_graph``, not here — a single edge into a
    multi-port block (e.g. cross_attention's ``query``) is compatible as
    long as the tensor kind matches.
    """
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
