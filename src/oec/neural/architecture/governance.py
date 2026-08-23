"""Architecture IR governance (ADR 0047 wave A8). Core-safe, no torch.

Manifests bind a graph to the catalog it was validated against so a
consumer can tell, offline, whether "the same architecture" still means
the same thing. ``audit_catalog`` is a read-only catalog health check —
it never mutates the registry.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from oec.neural.architecture.backends import (
    JAX_BUILDABLE_BLOCK_IDS,
    KNOWN_MANIFEST_BACKENDS,
    TORCH_BUILDABLE_BLOCK_IDS,
)
from oec.neural.architecture.errors import (
    ArchitectureValidationError,
    RegistrySealedError,
    UnknownBlockError,
)
from oec.neural.architecture.graph import (
    ARCHITECTURE_COMPATIBILITY_VERSION,
    ArchitectureGraph,
    ArchitectureValidationReport,
)
from oec.neural.architecture.registry import BlockRegistry
from oec.neural.architecture.shapes import graph_dim_errors
from oec.neural.architecture.specs import KNOWN_PARAMETER_KINDS, BlockSpec

COMPATIBILITY_VERSION = ARCHITECTURE_COMPATIBILITY_VERSION


class ArchitectureProvenance(BaseModel):
    """Closed provenance keys — no arbitrary free-form extras."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str | None = None
    author: str | None = None
    tool: str | None = None
    notes: str | None = None


class ArchitectureManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    graph_fingerprint: str
    registry_version: str
    catalog_hash: str
    compatibility_version: str
    backend: str
    experimental_flags_used: tuple[str, ...] = ()
    created_at: str | None = None
    provenance: ArchitectureProvenance = ArchitectureProvenance()


def manifest_for_graph(
    graph: ArchitectureGraph,
    registry: BlockRegistry,
    *,
    backend: str = "torch",
    created_at: str | None = None,
    provenance: ArchitectureProvenance | None = None,
) -> ArchitectureManifest:
    """Bind a graph's fingerprint to the catalog/compatibility state used to validate it.

    Fails closed: the registry must be sealed (immutable catalog state), the
    graph must validate against it, and ``backend`` must be a known backend.
    A manifest for an invalid graph or a mutable/unknown-backend catalog
    would certify nothing.
    """
    if not registry.sealed:
        raise RegistrySealedError(
            "manifest_for_graph requires a sealed registry; the catalog it "
            "certifies against must not be able to change after the fact",
            details={"registry_version": registry.version},
        )
    if backend not in KNOWN_MANIFEST_BACKENDS:
        raise ArchitectureValidationError(
            f"unknown architecture manifest backend {backend!r}",
            details={"backend": backend, "known": sorted(KNOWN_MANIFEST_BACKENDS)},
        )
    report = validate_for_backend(graph, backend, registry)
    if not report.valid:
        raise ArchitectureValidationError(
            "cannot manifest an architecture graph the backend cannot execute: "
            + "; ".join(report.errors),
            details={"errors": list(report.errors)},
        )
    specs_by_id = {node.block_id: registry.get(node.block_id) for node in graph.nodes}
    experimental_ids = sorted(spec_id for spec_id, spec in specs_by_id.items() if spec.experimental)
    return ArchitectureManifest(
        graph_fingerprint=graph.fingerprint(registry),
        registry_version=registry.version,
        catalog_hash=registry.catalog_hash(),
        compatibility_version=COMPATIBILITY_VERSION,
        backend=backend,
        experimental_flags_used=tuple(experimental_ids),
        created_at=created_at,
        provenance=provenance or ArchitectureProvenance(),
    )


def validate_for_backend(
    graph: ArchitectureGraph,
    backend: str,
    registry: BlockRegistry,
) -> ArchitectureValidationReport:
    """Graph + A7 topology + port dims + builder coverage. Core-safe (no torch)."""
    if backend not in KNOWN_MANIFEST_BACKENDS:
        return ArchitectureValidationReport(
            valid=False,
            errors=(f"unknown architecture backend {backend!r}",),
        )
    report = graph.validate_graph(registry)
    errors = list(report.errors)
    warnings = list(report.warnings)
    errors.extend(graph.a7_chain_errors(registry))
    errors.extend(graph_dim_errors(graph, registry))
    try:
        specs_by_id = {node.block_id: registry.get(node.block_id) for node in graph.nodes}
        _assert_backend_can_build(backend, specs_by_id)
    except (ArchitectureValidationError, UnknownBlockError) as exc:
        message = exc.message if isinstance(exc, ArchitectureValidationError) else str(exc)
        errors.append(message)
    # de-dupe while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for item in errors:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return ArchitectureValidationReport(
        valid=not unique,
        errors=tuple(unique),
        warnings=tuple(sorted(set(warnings))),
    )


def _assert_backend_can_build(backend: str, specs_by_id: dict[str, BlockSpec]) -> None:
    for spec_id, spec in specs_by_id.items():
        required = spec.backend_requirements
        if required and backend not in required:
            raise ArchitectureValidationError(
                f"block {spec_id!r} requires backends {list(required)}, not {backend!r}",
                details={
                    "block_id": spec_id,
                    "backend": backend,
                    "backend_requirements": list(required),
                },
            )
        if backend == "torch" and spec_id not in TORCH_BUILDABLE_BLOCK_IDS:
            raise ArchitectureValidationError(
                f"block {spec_id!r} has no torch builder; cannot manifest backend='torch'",
                details={"block_id": spec_id, "backend": backend},
            )
        if backend == "jax" and spec_id not in JAX_BUILDABLE_BLOCK_IDS:
            raise ArchitectureValidationError(
                f"block {spec_id!r} has no jax builder; cannot manifest backend='jax'",
                details={"block_id": spec_id, "backend": backend},
            )


class CatalogAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    experimental_ids: tuple[str, ...] = ()
    stable_ids: tuple[str, ...] = ()


def audit_catalog(registry: BlockRegistry) -> CatalogAuditReport:
    """Fail-closed health check over a catalog: duplicate ids, experimental
    blocks missing ``backend_requirements``, blocks declaring unknown
    parameter kinds, an unsealed registry, and missing ``input_ports``."""
    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    experimental_ids: list[str] = []
    stable_ids: list[str] = []

    for spec in registry.list():
        if spec.id in seen_ids:
            errors.append(f"duplicate block id: {spec.id}")
        seen_ids.add(spec.id)

        if spec.experimental:
            experimental_ids.append(spec.id)
            if not spec.backend_requirements:
                errors.append(f"experimental block missing backend_requirements: {spec.id}")
        else:
            stable_ids.append(spec.id)

        for param in spec.parameters:
            if param.kind not in KNOWN_PARAMETER_KINDS:
                errors.append(
                    f"block {spec.id} parameter {param.name!r} has unknown kind {param.kind!r}"
                )

        if not spec.input_ports:
            errors.append(f"block {spec.id} has no input_ports")
        if spec.output_ports != ("out",):
            errors.append(
                f"block {spec.id} output_ports={list(spec.output_ports)}; "
                "only ['out'] is supported until a multi-output protocol exists"
            )

    if not registry.sealed:
        errors.append("registry is not sealed")

    return CatalogAuditReport(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(sorted(set(warnings))),
        experimental_ids=tuple(sorted(experimental_ids)),
        stable_ids=tuple(sorted(stable_ids)),
    )
