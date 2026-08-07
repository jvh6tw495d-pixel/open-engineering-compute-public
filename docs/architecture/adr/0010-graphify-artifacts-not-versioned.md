# ADR 0010: Graphify's generated artifacts are not versioned

- **Status:** accepted
- **Date:** 2026-07-25

## Context

`graphify update .` writes a code graph and supporting files into
`graphify-out/` (`graph.json`, `graph.html`, `GRAPH_REPORT.md`,
`manifest.json`, `.graphify_labels.json`, `.graphify_root`, and a
`cache/` directory), as required by master plan section 31. Section 31.5
is explicit that these generated artifacts must not be committed "sem
decisão explícita em ADR" — evaluating size, stability, absolute paths,
and sensitive data first. This ADR is that explicit decision, formalizing
what had previously only been documented informally in
`docs/development/graphify.md`.

## Evaluation (as of Sprint 01, 376 nodes / 634 edges)

- **Size:** under 1 MB total — not a storage concern.
- **Absolute paths:** none found in `graph.json` (checked via
  `grep -c "OneDrive" graph.json` → `0`).
- **Sensitive data:** none — the corpus indexed is source code, docs,
  and ADRs already meant for the repository; nothing private is
  extracted into the graph.
- **Stability:** the graph is rebuilt at the end of every sprint (and
  after any structural refactor, per section 31.4's update policy), so
  it changes on nearly every commit that touches `src/oec` or `docs/`.
  `graph.html` alone is ~350 KB and would dominate diffs. `cache/` is
  pure extraction cache with no standalone value.

## Decision

`graphify-out/` stays listed in `.gitignore` and is never committed. It
is fully and cheaply regenerable from source via
`uv tool run --from graphifyy graphify update .` (no LLM cost for
structural extraction), so there is nothing lost by not versioning it —
same treatment as `.pytest_cache/`, `.mypy_cache/`, and `.ruff_cache/`.

## Consequences

- Every contributor (and every future sprint) regenerates the graph
  locally rather than pulling a possibly-stale committed copy.
- No noisy, low-signal diffs from `graph.json`/`graph.html` churn on
  every commit.
- If the graph is ever needed as a stable, shareable artifact — e.g. for
  onboarding documentation shipped in the eventual public repository —
  that is a new decision superseding this ADR, not a silent change to
  `.gitignore`.
- `docs/development/graphify.md` documents the tool, its invocation, and
  the update policy; it defers to this ADR for the versioning rationale
  instead of duplicating it.
