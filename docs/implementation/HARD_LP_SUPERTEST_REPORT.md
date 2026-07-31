# Hard LP supertest report

**Date:** 2026-07-28 18:02 UTC
**Arms:** `without_oec`, `extract_plus_oec`, `ops_plus_oec`

| Model | Provider | A sem OEC | B extrair+OEC | C OPS+OEC | Best |
|---|---|---:|---:|---:|---|
| `nvidia/nemotron-3-ultra-550b-a55b` | `nvidia` | 0 | 10 | 6 | B |
| `nvidia/nemotron-3-super-120b-a12b` | `nvidia` | 0 | 10 | 6 | B |
| `z-ai/glm-5.2` | `nvidia` | 3 | 10 | 6 | B |
| `zai-org/glm-5` | `nvidia` | 0 | 0 | 0 | A |
| `zai-org/glm-51` | `nvidia` | 0 | 0 | 0 | A |
| `deepseek-ai/deepseek-v3.1-terminus` | `nvidia` | 0 | 0 | 0 | A |
| `deepseek-ai/deepseek-v32-exp-nim` | `nvidia` | 0 | 0 | 0 | A |
| `qwen/qwen3-coder-next` | `nvidia` | 0 | 0 | 0 | A |
| `qwen/qwen3-next-80b-a3b-instruct` | `nvidia` | 0 | 0 | 0 | A |
| `qwen/qwen3-next-80b-a3b-thinking` | `nvidia` | 0 | 0 | 0 | A |
| `qwen/qwen3-32b` | `nvidia` | 0 | 0 | 0 | A |
| `deepseek-r1:8b` | `custom:ollama` | 0 | 0 | 0 | A |
| `nemotron-3-nano:4b` | `custom:ollama` | 0 | 10 | 6 | B |
| `hf.co/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF:Q4_K_M` | `custom:ollama` | 0 | 10 | 0 | B |
| `qwen2.5:7b-instruct` | `custom:ollama` | 1 | 10 | 0 | B |
| `llama3.1:8b` | `custom:ollama` | 2 | 6 | 6 | B |
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
| `sonnet` | `claude-cli` | 0 | 10 | 6 | B |
| `opus` | `claude-cli` | 0 | 10 | 6 | B |
| `fable` | `claude-cli` | 0 | 0 | 0 | A |
