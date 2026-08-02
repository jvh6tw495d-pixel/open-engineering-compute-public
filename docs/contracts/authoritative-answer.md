# `authoritative_answer` contract (v2.5.3, Waves 1–2)

**Status:** normative for `oec.mcp` agent-tool responses (`_AGENT_TOOL_SCHEMAS`
in `src/oec/mcp/server.py`).
**Scope:** MCP agent tools only (`agent.*`). REST/SDK/CLI are out of scope
for this release (see `v2.5.3-EXECUTION-PLAN.md` §16).
**Meta:** a weak host must never be able to turn a correct OEC solve into an
incorrect final JSON answer.

## Envelope (Wave 1)

Every successful `agent.*` call is additively normalized at the `call_tool`
boundary (`src/oec/mcp/envelope.py::normalize`). See `docs/mcp/README.md` for
the full envelope shape, `kind` taxonomy, and the nine live response shapes.
This document covers the Wave 2 addition: `claimed_answer` and
`host_output_diverged`.

## `claimed_answer` (Wave 2, host-voluntary)

A host may attach `claimed_answer` to any `agent.*` tool call, alongside its
normal arguments. It is **not** a new MCP tool and **not** required — every
`_AGENT_TOOL_SCHEMAS` entry declares it as an optional, unconstrained
property (`{}` in JSON Schema — any JSON value is accepted structurally).
`agent.default` and `agent.scientific_reviewer` also keep their existing
narrower `claimed_objective` (number) / `claimed_solver_status` (string)
fields; `claimed_answer` is a separate, additional channel and does not
replace them (see "Interaction" below).

OEC compares `claimed_answer` against the `authoritative_answer` it just
computed and, on disagreement, adds a `host_output_diverged` warning to the
response. **This never changes `authoritative_answer`.** The comparison is
fail-closed and purely additive:

- No claim provided → no comparison, no warning.
- Claim matches within policy → no warning.
- Claim disagrees, or cannot be verified (NaN/Infinity) → `host_output_diverged`
  is added; `authoritative_answer` is returned exactly as OEC computed it,
  untouched.
- The check only runs when the agent-tool call reached its normal success
  surface (`status: "ok"`). `needs_clarification` / `needs_more_information`
  responses never mint authority by design (Wave 1), so a leftover claim
  there is not treated as "host corruption" — nothing was computed yet.

## Comparison policy

Implementation: `src/oec/mcp/divergence.py`. Policy version:
`DIVERGENCE_POLICY_VERSION = "1.0"`, carried on every
`host_output_diverged.policy_version`. Bump this version (per plan §11 item 9)
whenever a tolerance or comparison rule below changes — hosts may depend on
the current silence/firing behavior at the margin.

### Canonicalization (always post-serialization)

Comparison never runs on pre-serialization Python objects. Both sides are
round-tripped through the same canonical form the MCP transport itself uses:

```python
json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
```

This is why `(1, 2, 3)` (tuple) and `[1, 2, 3]` (list) compare equal — they
serialize identically — and why dict key insertion order never causes a
false mismatch.

### Numeric tolerance (versioned)

| Constant | Value |
|---|---|
| `DEFAULT_ABS_TOLERANCE` | `1e-9` |
| `DEFAULT_REL_TOLERANCE` | `1e-6` |

Two numbers are equal if `math.isclose(a, b, rel_tol=DEFAULT_REL_TOLERANCE,
abs_tol=DEFAULT_ABS_TOLERANCE)`. `int` and `float` compare as numbers (`1`
and `1.0` are equal); `bool` never coerces to/from a number (`True` is never
equal to `1`).

### NaN / Infinity — fail-closed

If either side of a numeric comparison is `NaN` or `±Infinity`, the pair is
**always flagged** (`reason: "nan_or_inf_unverifiable"`), never silently
treated as equal or unequal-but-ignored. These values do not round-trip
losslessly through JSON, so OEC cannot verify the claim — fail-closed means
surfacing that uncertainty, not guessing.

### Subset claims

A host may claim only part of the answer. Comparison walks the **claim's**
keys, not the authority's:

- A key present in `authoritative_answer.values` but **absent** from the
  claim is not compared and never causes a mismatch (the host simply didn't
  claim it).
- A key present in the **claim** but absent from
  `authoritative_answer.values` is flagged
  (`reason: "claimed_key_not_in_authoritative"`) — the host asserted
  something OEC never produced.

### Null vs. absence

These are distinguished deliberately:

- Omitting a key from the claim → no check (subset policy above).
- Explicitly claiming `"key": null` → compared like any other value. If the
  authoritative value is non-null, this is flagged
  (`reason: "null_vs_value"`); if the authoritative value is also `null`,
  it matches.

### Lists

Length must match first (`reason: "list_length_mismatch"` otherwise); then
elements are compared pairwise by index, recursing under the same rules.

### `QuantityValue`-shaped objects

No special-cased type — a `{"value": ..., "unit": ...}` object is compared
like any other dict (subset-per-key). A unit mismatch (e.g. `"kW"` vs
`"MW"`) is a plain string mismatch on the `unit` key; magnitude mismatches
go through the numeric tolerance above. OEC does not perform unit conversion
when comparing claims.

## Structured `host_output_diverged` shape

```json
{
  "policy_version": "1.0",
  "reason": "value_mismatch",
  "mismatches": [
    {
      "path": "$.objective_value",
      "reason": "value_mismatch",
      "authoritative": 1.0,
      "claimed": -999999.0
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `policy_version` | Comparison policy version (see above) |
| `reason` | `"value_mismatch"` (one or more field-level mismatches) or `"no_authoritative_answer"` (claim provided but OEC minted no authority at all — e.g. a blocked `INVALID`/`FAILED` execution) |
| `mismatches` | List of field-level records; `path` is a JSON-Pointer-ish string (`$.a.b[2].c`) rooted at `authoritative_answer.values` |
| `mismatches[].reason` | One of: `value_mismatch`, `type_mismatch`, `list_length_mismatch`, `null_vs_value`, `claimed_key_not_in_authoritative`, `nan_or_inf_unverifiable`, `authoritative_answer_absent` |

## Interaction with `claimed_objective` / `claimed_solver_status`

`agent.scientific_reviewer` (and `agent.default` when routed there) already
accepts `claimed_objective` / `claimed_solver_status` as narrow, domain-specific
inputs to the reviewer's own audit checks (`agents/scientific_reviewer/reviewer.py`)
— these feed `checks[]` in the review report itself and predate Wave 2.
`claimed_answer` is independent: it is compared generically against whatever
`authoritative_answer` the call produced (for the reviewer, `kind:
"review_result"` with `values: {passed, checks}`). Both can be sent on the
same call without conflict.

## Rules hosts should rely on

- `authoritative_answer` is never overwritten, augmented, or "corrected" by a
  `claimed_answer` — under no circumstances does OEC trust the host's claim
  over its own computation.
- Absence of `host_output_diverged` means either no claim was sent, or the
  claim matched within policy. It does not mean "verified true" in any
  stronger sense than "matched OEC's own output."
- Treat `host_output_diverged` as a strong signal that the host's own
  downstream narration/state has drifted from what OEC actually computed.
