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

## Known limitations observed

`GRAPH_REPORT.md` flagged 33 weakly-connected nodes (mostly Markdown
section headers from ADRs and issue templates, which is expected — prose
structure, not code structure) and 9 inferred (not extracted) edges around
`VersionedRef`, worth a second look once the loader/registry start
consuming these models in Sprint 01.
