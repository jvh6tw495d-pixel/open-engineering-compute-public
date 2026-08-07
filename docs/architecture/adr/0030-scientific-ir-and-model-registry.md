# ADR 0030 — Scientific IR v0 and Model Registry (v2.9)

- Status: **Accepted**
- Date: 2026-08-06
- Release: content ships in `oec==3.1.0` (closes deferred V3 §13 / v2.9 scope)

## Context

V3 §13 (v2.9) requires:

- **Scientific IR** — Math IR + laws + species + properties
- **Model Registry** with fidelity tags (reduced / mid / high)
- Deprecation path and catalog export

Math IR already exists (`oec.modeling.ir`, ADR 0020) and stays domain-agnostic.
Skill folder resolution lives in `oec.skills.registry` and is **not** replaced.

## Decision

1. **Scientific IR** lives in `oec.modeling.scientific_ir` as
   `ScientificDocument` — declarative, JSON round-trip, schema version
   `0.1.0`. Embeds optional Math IR problem payload as a dict; declares
   species, reactions, `LawRef`, `PropertyRef`, and `ConservationGoal`.
2. **Model Registry** lives in `oec.registry` (new package) — in-memory
   `ModelRegistry` + `ModelRecord` with `FidelityLevel` enum
   (`reduced` | `mid` | `high`). Supports list/filter, deprecate,
   JSON catalog load/save.
3. **Seed catalog** includes multiphysics (2.7), chemistry (2.8), and
   Scientific IR (2.9) entrypoints via `default_registry()`.
4. **Out of scope v0:** full V3 §20 governance UI, remote catalog service,
   automatic fidelity promotion, SemVer-complete version ordering beyond
   lexicographic string sort.

## Consequences

- Callers can discover models without scanning the filesystem skill tree.
- Scientific IR does not execute — domain owners still run physics/chemistry.
- Deprecations are first-class (`deprecated`, `replaced_by`).

## Related

- ADR 0020 Math IR · ADR 0019 Scientific Kernel · ADR 0029 Chemistry
- V3 §13 · V3 §20 fidelity
