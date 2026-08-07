# Governance — Open Engineering Compute

This document is the public-facing governance stub required by the V3
layout (implementation plan §14). It applies to the **public** project
tree; incubation may hold additional private process docs that never ship.

## Principles

1. **Science first.** OEC ships generalisable engineering computation —
   skills, kernels, units, IR — not commercial scoring, client pricing, or
   proprietary decision engines (ADR 0008 / plan §19).
2. **Skill contract.** Every public skill has schemas, method declaration,
   references, and tests. Thin adapters over domain libraries are preferred.
3. **Units and conservation.** Quantities carry units (ADR 0003/0016);
   balance residuals use a single conservation owner where applicable.
4. **Reproducibility.** Deterministic defaults; provenance on execution
   results (ADR 0017).
5. **Public/private separation.** Incubation history is never force-published;
   public releases use a clean tree (ADR 0008).

## Roles

| Role | Responsibility |
|------|----------------|
| Maintainers | Releases, ADR acceptance, public tag authority |
| Contributors | PRs against public contract; no private brand leakage |
| Reviewers | Contract, units, forbidden-names, tests |

## Decision records

Architectural decisions live under `docs/architecture/adr/`. Accepted ADRs
are the source of truth for package layout and interfaces.

## Versioning

- Package versions follow SemVer on the incubation and public trees.
- **Product milestone v3.0** (original plan) = first **official public**
  GitHub release after 2.8–2.9 RC gates (Option A).
- See `docs/implementation/OPTION-A-REALIGNMENT.md` for the map between
  historical incubation tags and product milestones.

## Security

- Report vulnerabilities per `SECURITY.md`.
- No secrets in the repository; CI runs lint/type/test and forbidden-name gates.

## License

Apache-2.0 — see `LICENSE`.
