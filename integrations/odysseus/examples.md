# Odysseus examples — natural language to OEC skills

These walks assume Odysseus (or an equivalent MCP host) is configured
with [`local-mcp.example.json`](local-mcp.example.json) and can call
OEC tools.

## 1. Discover skills

**User:** “What engineering skills can you run?”

**Host action:** call MCP tool `list_skills`.

**Expect:** JSON catalog of skill ids, versions, titles and domains —
including `mathematics.*` and `electrical.*`.

## 2. Math root (dimensionless)

**User:** “Find the positive root of x² − 2 between 0 and 2.”

**Host action:** tool `mathematics.solve_root` with

```json
{
  "expression": "x**2 - 2",
  "bracket": [0, 2]
}
```

**Expect:** `ExecutionResult` with `status` usable (`VERIFIED` /
`VALIDATED` / …), `result` near `√2`, method identity, diagnostics and
provenance (`skill` version, `run_id`, …).

## 3. Three-phase power (units)

**User:** “A balanced three-phase load at 380 V line-to-line draws 10 A
at 0.8 lagging. What are P, Q and S?”

**Host action:** tool `electrical.three_phase_power` with

```json
{
  "voltage_line_to_line": { "value": 380, "unit": "V" },
  "current_line": { "value": 10, "unit": "A" },
  "power_factor": 0.8,
  "power_factor_type": "lagging"
}
```

**Expect:** active ≈ 5.27 kW, reactive ≈ 3.95 kvar, apparent ≈ 6.58 kVA,
`status: VERIFIED`. Equivalent inputs in `kV` / `mA` must agree after
ADR 0016 normalization.

## 4. Presenting results

Always surface at least:

- numeric values **with units**;
- methodology / method id and skill version from provenance;
- warnings and diagnostics when present;
- validation status (`VERIFIED`, `INVALID`, …) — do not invent numbers
  when status is `INVALID` / `FAILED`.
