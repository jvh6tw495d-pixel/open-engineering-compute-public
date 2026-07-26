# ADR 0017: Provenance includes input_hash and backend versions

- **Status:** accepted
- **Date:** 2026-07-26
- **Phase:** A1 (core consolidation)

## Context

Phase A requires every execution to be auditable enough to answer: *what
inputs were used* and *which scientific engines were in the environment*.
`ProvenanceRecord` already carried `oec_version`, `git_commit`, `trace_id`,
sandbox honesty flags, and optional unit originals — but not a stable input
fingerprint or library versions.

## Decision

Extend `build_provenance` / `ProvenanceRecord` **additively**:

1. **`input_hash`**: SHA-256 hex digest of canonical JSON serialization of the
   caller’s original `inputs` (`sort_keys=True`, compact separators, UTF-8).
2. **`backends`**: list of `{name, version}` for the core scientific packages
   importable in the runtime: `numpy`, `scipy`, `sympy`, `pint` (skip any
   missing). This records **environment engines**, not a per-call dynamic
   import trace.

Do **not** change `ExecutionStatus` or collapse results to boolean success.

## Consequences

- All executions gain stronger reproducibility metadata without breaking
  existing consumers (new keys only).
- Skills that never import SciPy still list SciPy in `backends` if installed;
  skill.md remains the source of *which* routine a method uses.
- Future HiGHS/other engines can append to the same list when added as deps.
