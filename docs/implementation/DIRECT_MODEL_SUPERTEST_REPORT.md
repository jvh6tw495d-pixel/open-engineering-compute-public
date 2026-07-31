# Direct model supertest report

**Date:** 2026-07-28 16:48 UTC
**Config source:** `C:\Users\joaop\AppData\Local\hermes\config.yaml`
**Arms:** `without_oec`, `extract_plus_oec`, `ops_plus_oec`

## Models tested

| Model | Provider | Source | Base URL |
|---|---|---|---|
| `nvidia/nemotron-3-ultra-550b-a55b` | `nvidia` | `default` | `https://integrate.api.nvidia.com/v1` |
| `nvidia/nemotron-3-super-120b-a12b` | `nvidia` | `fallback_1` | `https://integrate.api.nvidia.com/v1` |
| `z-ai/glm-5.2` | `nvidia` | `fallback_2` | `https://integrate.api.nvidia.com/v1` |
| `zai-org/glm-5` | `nvidia` | `fallback_3` | `https://integrate.api.nvidia.com/v1` |
| `zai-org/glm-51` | `nvidia` | `fallback_4` | `https://integrate.api.nvidia.com/v1` |
| `deepseek-ai/deepseek-v3.1-terminus` | `nvidia` | `fallback_5` | `https://integrate.api.nvidia.com/v1` |
| `deepseek-ai/deepseek-v32-exp-nim` | `nvidia` | `fallback_6` | `https://integrate.api.nvidia.com/v1` |
| `qwen/qwen3-coder-next` | `nvidia` | `fallback_7` | `https://integrate.api.nvidia.com/v1` |
| `qwen/qwen3-next-80b-a3b-instruct` | `nvidia` | `fallback_8` | `https://integrate.api.nvidia.com/v1` |
| `qwen/qwen3-next-80b-a3b-thinking` | `nvidia` | `fallback_9` | `https://integrate.api.nvidia.com/v1` |
| `qwen/qwen3-32b` | `nvidia` | `fallback_10` | `https://integrate.api.nvidia.com/v1` |
| `deepseek-r1:8b` | `custom:ollama` | `fallback_11` | `http://127.0.0.1:11434/v1` |
| `nemotron-3-nano:4b` | `custom:ollama` | `fallback_12` | `http://127.0.0.1:11434/v1` |
| `hf.co/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF:Q4_K_M` | `custom:ollama` | `fallback_13` | `http://127.0.0.1:11434/v1` |
| `qwen2.5:7b-instruct` | `custom:ollama` | `fallback_14` | `http://127.0.0.1:11434/v1` |
| `llama3.1:8b` | `custom:ollama` | `fallback_15` | `http://127.0.0.1:11434/v1` |
| `grok-4.5` | `opencode-go` | `opencode_go_1` | `https://opencode.ai/zen/go/v1` |
| `glm-5.2` | `opencode-go` | `opencode_go_2` | `https://opencode.ai/zen/go/v1` |
| `glm-5.1` | `opencode-go` | `opencode_go_3` | `https://opencode.ai/zen/go/v1` |
| `kimi-k3` | `opencode-go` | `opencode_go_4` | `https://opencode.ai/zen/go/v1` |
| `kimi-k2.7-code` | `opencode-go` | `opencode_go_5` | `https://opencode.ai/zen/go/v1` |
| `kimi-k2.6` | `opencode-go` | `opencode_go_6` | `https://opencode.ai/zen/go/v1` |
| `deepseek-v4-pro` | `opencode-go` | `opencode_go_7` | `https://opencode.ai/zen/go/v1` |
| `deepseek-v4-flash` | `opencode-go` | `opencode_go_8` | `https://opencode.ai/zen/go/v1` |
| `mimo-v2.5` | `opencode-go` | `opencode_go_9` | `https://opencode.ai/zen/go/v1` |
| `mimo-v2.5-pro` | `opencode-go` | `opencode_go_10` | `https://opencode.ai/zen/go/v1` |
| `hy3` | `opencode-go` | `opencode_go_11` | `https://opencode.ai/zen/go/v1` |

## Comparative scoreboard

| Model | Provider | A sem OEC | B extrair+OEC | C OPS+OEC | Best |
|---|---|---:|---:|---:|---|
| `nvidia/nemotron-3-ultra-550b-a55b` | `nvidia` | 0 | 10 | 5 | B |
| `nvidia/nemotron-3-super-120b-a12b` | `nvidia` | 0 | 10 | 5 | B |
| `z-ai/glm-5.2` | `nvidia` | 0 | 10 | 5 | B |
| `zai-org/glm-5` | `nvidia` | 0 | 0 | 0 | A |
| `zai-org/glm-51` | `nvidia` | 0 | 0 | 0 | A |
| `deepseek-ai/deepseek-v3.1-terminus` | `nvidia` | 0 | 0 | 0 | A |
| `deepseek-ai/deepseek-v32-exp-nim` | `nvidia` | 0 | 0 | 0 | A |
| `qwen/qwen3-coder-next` | `nvidia` | 0 | 0 | 0 | A |
| `qwen/qwen3-next-80b-a3b-instruct` | `nvidia` | 0 | 0 | 0 | A |
| `qwen/qwen3-next-80b-a3b-thinking` | `nvidia` | 0 | 0 | 0 | A |
| `qwen/qwen3-32b` | `nvidia` | 0 | 0 | 0 | A |
| `deepseek-r1:8b` | `custom:ollama` | 0 | 0 | 0 | A |
| `nemotron-3-nano:4b` | `custom:ollama` | 0 | 10 | 5 | B |
| `hf.co/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF:Q4_K_M` | `custom:ollama` | 0 | 10 | 5 | B |
| `qwen2.5:7b-instruct` | `custom:ollama` | 2 | 10 | 5 | B |
| `llama3.1:8b` | `custom:ollama` | 4 | 10 | 5 | B |
| `grok-4.5` | `opencode-go` | 0 | 0 | 0 | A |
| `glm-5.2` | `opencode-go` | 0 | 0 | 0 | A |
| `glm-5.1` | `opencode-go` | 0 | 0 | 0 | A |
| `kimi-k3` | `opencode-go` | 0 | 0 | 0 | A |
| `kimi-k2.7-code` | `opencode-go` | 0 | 0 | 0 | A |
| `kimi-k2.6` | `opencode-go` | 0 | 0 | 0 | A |
| `deepseek-v4-pro` | `opencode-go` | 0 | 0 | 0 | A |
| `deepseek-v4-flash` | `opencode-go` | 0 | 0 | 0 | A |
| `mimo-v2.5` | `opencode-go` | 0 | 0 | 0 | A |
| `mimo-v2.5-pro` | `opencode-go` | 0 | 0 | 0 | A |
| `hy3` | `opencode-go` | 0 | 0 | 0 | A |
