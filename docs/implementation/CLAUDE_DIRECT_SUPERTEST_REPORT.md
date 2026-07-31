# Direct model supertest report

**Date:** 2026-07-28 17:02 UTC
**Config source:** `C:\Users\joaop\AppData\Local\hermes\config.yaml`
**Arms:** `without_oec`, `extract_plus_oec`, `ops_plus_oec`

## Models tested

| Model | Provider | Source | Base URL |
|---|---|---|---|
| `sonnet` | `claude-cli` | `claude_cli_1` | `claude-cli` |
| `opus` | `claude-cli` | `claude_cli_2` | `claude-cli` |
| `fable` | `claude-cli` | `claude_cli_3` | `claude-cli` |

## Comparative scoreboard

| Model | Provider | A sem OEC | B extrair+OEC | C OPS+OEC | Best |
|---|---|---:|---:|---:|---|
| `sonnet` | `claude-cli` | 7 | 10 | 5 | B |
| `opus` | `claude-cli` | 10 | 10 | 5 | A |
| `fable` | `claude-cli` | 0 | 0 | 0 | A |
