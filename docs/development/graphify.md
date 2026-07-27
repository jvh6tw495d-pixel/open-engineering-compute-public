# Graphify — structural memory of this repository

OEC uses [Graphify](https://github.com) to build and maintain a navigable
graph of the codebase, as required by section 31 of the master plan. It is a
complement to Git, tests, docs, ADRs, and type checking — not a replacement
for any of them.

## Installation found

Graphify was already installed in the user's environment as a `uv` tool:

```text
package: graphifyy
version: 0.8.39
commands exposed: graphify, graphify-mcp
```

It is **not** on `PATH` directly (no `graphify` binary outside the uv tool
shim), so every invocation in this repository goes through:

```bash
uv tool run --from graphifyy graphify <command> [args]
```

Verified with:

```bash
uv tool list                                    # showed graphifyy v0.8.39
uv tool run --from graphifyy graphify --version # -> graphify 0.8.39
uv tool run --from graphifyy graphify --help    # full command list
```

No alternative installation was created; the pre-existing one is used as-is
per the plan's instruction not to install another variant without cause.

## Backend

Local backend available and preferred, per section 31.3:

```text
Ollama
└── llama3.1:8b   (present locally — `ollama list` confirmed)
```

The initial indexing command used for this sprint (`graphify update .`) does
**not** require an LLM backend — it performs structural extraction only. The
Ollama backend becomes relevant only for `graphify label` (semantic community
naming) or `graphify query`, which are not required for Sprint 00 and are
deferred to when the graph grows large enough to need it.

## Procedure used in Sprint 00

```bash
uv tool run --from graphifyy graphify update .
```

Output:

```text
Re-extracting code files in . (no LLM needed)...
[graphify watch] Rebuilt: 143 nodes, 166 edges, 31 communities
[graphify watch] graph.json, graph.html and GRAPH_REPORT.md updated in graphify-out
```

Artifacts generated in `graphify-out/`:

| File | Purpose |
|---|---|
| `graph.json` | machine-readable graph (nodes/edges/communities) |
| `graph.html` | interactive visual graph |
| `GRAPH_REPORT.md` | human-readable summary: hubs, god nodes, communities, gaps |
| `manifest.json` | extraction manifest |
| `.graphify_labels.json`, `.graphify_root` | internal bookkeeping |
| `cache/` | extraction cache |

## Versioning decision

`graphify-out/` is **not committed** to Git (see `.gitignore`). This is now
a formal decision — see
[ADR 0010](../architecture/adr/0010-graphify-artifacts-not-versioned.md)
for the full evaluation (size, stability, absolute paths, sensitive data)
required by master plan section 31.5 before generated artifacts can be
excluded from or included in version control.

## Update policy

Per section 31.4, the graph is updated:

- at the end of each sprint;
- after any relevant structural refactor;
- after new core modules are created;
- before multi-file architectural tasks;
- before the sprint's final report.

### Last full rebuild (v2.0 handoff)

**2026-07-27** after Scientific Kernel cut + GPT construction handoff:

```bash
uv tool run --from graphifyy graphify update .
```

**Rebuild result (2026-07-27):** ~**5058 nodes**, ~**7783 edges**, ~**435 communities**
(`graph.html` skipped — over viz node limit; use `graph.json` + `GRAPH_REPORT.md`)

Indexed highlights for construction agents:

- `src/oec/core/**` (v2.0 Scientific Kernel)
- `docs/implementation/GPT_CONSTRUCTION_HANDOFF.md` (GPT builds; Grok validates)
- `docs/implementation/OEC_V3_IMPLEMENTATION_PLAN.md` (state: v2.0 done → v2.1 next)
- `docs/concepts/scientific-kernel.md`, ADR 0019

`graphify-out/` remains **gitignored** (ADR 0010). Rebuild locally before multi-agent construction sessions.

### Pre-v2.1 stabilization rebuild

Rebuilt again on **2026-07-27** before stabilization and Q0 planning.
`GRAPH_REPORT.md` records baseline commit `6e271496` with approximately
**5063 nodes**, **7787 edges** and **428 communities**. Generated artifacts
remain local and gitignored; rebuild after the stabilization/documentation
changes before handing off implementation.

**Post-stabilization/Q0 rebuild:** **5086 nodes**, **7819 edges** and
**466 communities**. The report still names committed baseline `6e271496`;
the new stabilization and Q0 files are present in the local graph but remain
uncommitted at this handoff.

### v2.1 implementation report

The report
[`v2.1-delivery-status-and-v2.5-next-steps.md`](../implementation/v2.1-delivery-status-and-v2.5-next-steps.md)
is the indexed handoff after commits `f7cbf0a` and `abb31c7`. It records:

- the complete v2.1 implementation and independent gate evidence;
- corrections made after Terra, Grok, Opus and OpenCode review;
- blockers that still prevent declaring/tagging `2.1.0`;
- the ordered Math IR, Backend Registry, Verification and v2.5 next steps.

Rebuild Graphify after changing that report so future construction agents do
not confuse technical completion with a released package version.

### v2.1 release closeout rebuild

Rebuilt on **2026-07-27** after the v2.1 metadata/documentation closeout
(version bumps to `2.1.0`, `CHANGELOG.md` entry, README status, Q0 inventory
delivery closeout, `technical-debt.md` closures). `GRAPH_REPORT.md` now
records baseline commit `7c5c4136` with **5241 nodes**, **8177 edges** and
**457 communities**; the local tool itself is now `graphifyy` v0.9.28
(previously v0.8.39 — command surface unchanged). The closeout changes are
committed as the v2.1 release commit immediately after this rebuild.

### v2.2 Math IR foundation rebuild

Rebuilt on **2026-07-27** after the v2.2 Math IR implementation
(`src/oec/modeling/`, `src/oec/backends/`, ADR 0020, `mathematics.solve_ir`,
and the associated unit/parity tests). **5496 nodes**, **8777 edges** and
**465 communities**. Package version, `CHANGELOG.md`, README status and any
tag remain unchanged in this pass — those are a separate closeout step, per
ADR 0020's own consequences section.

### v2.2 release closeout rebuild

Rebuilt on **2026-07-27** after the v2.2 metadata/documentation closeout
(version bumps to `2.2.0`, `CHANGELOG.md` entry, README status). `GRAPH_REPORT.md`
now records baseline commit `5bd11aba` with **5501 nodes**, **8783 edges** and
**475 communities**. The closeout changes are committed as the v2.2 release
commit immediately after this rebuild.

### v2.4 Backend Registry + Verification Engine rebuild (S1–S3)

Rebuilt on **2026-07-27** after implementing the v2.4 Backend Capability
Registry (`src/oec/backends/{capabilities,selection,fallback}.py` +
`adapters/`) and Verification Engine (`src/oec/verification/`), wired
additively into `ExecutionService.execute`, plus ADR 0021. This rebuild
lands on top of `oec==2.3.0` (Applied Math expansion, Waves A+B+C), released
by a separate session on this same branch between the v2.2 closeout and this
work — the corpus grew accordingly. **7898 nodes**, **11810 edges** and
**623 communities**. Package version, `CHANGELOG.md`, README status and any
tag remain unchanged in this pass — a separate closeout step, mirroring the
v2.1/v2.2 pattern. S4 (computational-kernel unification under
`kernel/computational`) is explicitly deferred; see ADR 0021's non-goals.

## Known limitations observed

`GRAPH_REPORT.md` flagged 33 weakly-connected nodes (mostly Markdown
section headers from ADRs and issue templates, which is expected — prose
structure, not code structure) and 9 inferred (not extracted) edges around
`VersionedRef`, worth a second look once the loader/registry start
consuming these models in Sprint 01.
