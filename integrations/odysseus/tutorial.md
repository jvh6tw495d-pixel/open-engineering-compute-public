# Odysseus × OEC — end-to-end tutorial (handbook §15.1 / Fase 7)

This walk-through is host-agnostic: any MCP client that can launch a
stdio server works (Odysseus, Claude Desktop-style configs, custom
hosts). OEC never imports Odysseus.

## 0. Prerequisites

```bash
cd /path/to/OEC
uv sync --extra mcp
uv run oec skills list --skills-root skills
```

Confirm at least one math and one electrical skill appear.

## 1. Start OEC as an MCP server

```bash
uv run oec server mcp --skills-root skills
```

The process speaks MCP over **stdio**. Leave it managed by the host —
do not type into this terminal.

## 2. Configure the host

Copy [`local-mcp.example.json`](local-mcp.example.json) into your host's
MCP config. Set `cwd` to the absolute path of this repository.

Restart / reload the host so it spawns `uv run oec server mcp ...`.

## 3. List skills

Ask the host (natural language is fine):

> What OEC skills are available?

The host should call the MCP tool `list_skills` and show ids such as
`mathematics.solve_root` and `electrical.three_phase_power`.

## 4. Run a calculation

> Balanced three-phase load at 380 V line-to-line, 10 A, 0.8 lagging —
> compute P, Q and S.

Host calls tool `electrical.three_phase_power` with:

```json
{
  "voltage_line_to_line": { "value": 380, "unit": "V" },
  "current_line": { "value": 10, "unit": "A" },
  "power_factor": 0.8,
  "power_factor_type": "lagging"
}
```

## 5. Read the result

The tool returns a full `ExecutionResult` JSON. Surface at least:

| Field | Why |
|---|---|
| `status` | Trust gate (`VERIFIED`, `INVALID`, …) |
| `result` | Values **with units** |
| `method` / provenance | Methodology + skill version |
| `diagnostics` / `warnings` | Numerical honesty |
| `provenance.run_id` | Audit trail |

Never invent numbers when `status` is `INVALID` or `FAILED`.

## 6. Smoke without a GUI host

The same scientific path is available without Odysseus:

```bash
uv run oec run electrical.three_phase_power --input '{
  "voltage_line_to_line": {"value": 380, "unit": "V"},
  "current_line": {"value": 10, "unit": "A"},
  "power_factor": 0.8
}' --skills-root skills
```

```python
from oec.sdk import run

result = run(
    "electrical.three_phase_power",
    {
        "voltage_line_to_line": {"value": 380, "unit": "V"},
        "current_line": {"value": 10, "unit": "A"},
        "power_factor": 0.8,
    },
    skills_root="skills",
)
print(result.status, result.result)
```

ADR 0005 guarantees the scientific content matches MCP/REST/CLI/SDK.

## Security reminder

Alpha MCP has no auth and no rate limit (ADR 0015 §4). Prefer stdio on
the same machine. Do not expose to untrusted networks.
