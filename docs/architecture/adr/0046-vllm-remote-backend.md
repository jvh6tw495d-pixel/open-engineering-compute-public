# ADR 0046: vLLM Remote Backend (HTTP client only)

- **Status:** accepted
- **Date:** 2026-08-17
- **Phase:** post-3.6 (Scientific AI follow-on)
- **Related:** ADR 0038, 0040, 0041
- **Supersedes (partially):** ADR 0040 D2 — re-opens **vLLM**, client only.
  llama.cpp / SGLang remain out.

## Context

ADR 0040 D2 excluded vLLM, llama.cpp, and SGLang from 3.6: "HF Transformers
only; residual debt" (tracked as `D-AI-04`). vLLM the **engine** is a
Linux+NVIDIA CUDA project with no supported Windows install path — vendoring
it, or adding it as an `oec[...]` extra, would break `--all-extras` on
Windows and pull a GPU-only dependency into an optional group that otherwise
installs cleanly everywhere.

Operators who already run a vLLM server (on a GPU box, in a container, behind
a load balancer) still want OEC to call it for generation, the same way
`scripts/llama_oec_experiment.py` already calls a locally-running Ollama
server over plain HTTP. That pattern — OEC as a client of an
already-running, separately-operated inference server — does not require
installing vLLM, `torch`, or any GPU library into the OEC process at all.

## Decision

1. **Client only.** OEC never imports, vendors, or installs the `vllm`
   Python package. It talks to a **running, OpenAI-compatible vLLM HTTP
   server** (`POST {base_url}/v1/completions`) using the Python standard
   library (`urllib`) — no `openai` SDK, no `requests`, no new dependency of
   any kind. This keeps vLLM support **out of `pyproject.toml` entirely**:
   it is not `oec[foundation]`, not a new extra, and does not change what
   `--all-extras` installs on any platform.
2. **llama.cpp and SGLang stay out** of scope for this ADR. `D-AI-04` closes
   for vLLM only; llama.cpp/SGLang residual debt remains open.
3. **Fail-closed.** If the configured server is unreachable, times out, or
   returns a response that doesn't parse as a completions payload, the
   skill returns a structured `vllm_unreachable` error. It never invents,
   truncates-and-continues, or falls back to a local model for the missing
   text.
4. **No adapter/PEFT reload on this path.** `foundation.generate`'s
   `adapter_path` reload (ADR 0041 §3) is a local-Transformers-process
   concept — a LoRA adapter directory has no meaning against a remote vLLM
   server's already-loaded model. `VllmGenerateSpec` has no `adapter_path`
   field and rejects the key outright (`extra="forbid"`) rather than
   silently ignoring it.
5. **New skill `foundation.vllm_generate`** (`network_access: true`) is the
   only network-reaching path added by this ADR. `foundation.generate`
   (Transformers, local process) keeps `network_access: false` — it is not
   changed to support vLLM or any other remote backend.
6. **Bounded timeout.** Every HTTP call carries a fixed, short timeout
   (30 s) — no unbounded hang waiting on a remote server.

## Non-goals

- Running, packaging, or vendoring the vLLM engine itself.
- llama.cpp / SGLang clients (tracked separately under `D-AI-04`).
- Streaming completions, chat-completions, embeddings, or any endpoint other
  than `/v1/completions`.
- Authentication/mTLS to the remote server (operators front it with their
  own network controls; out of scope here as it is for the existing Ollama
  script).

## Consequences

- `D-AI-04` closes for **vLLM** (client path only); llama.cpp/SGLang remain
  open debt.
- `GenerationBackend.VLLM` exists alongside `GenerationBackend.TRANSFORMERS`
  for capability discovery (`foundation.capabilities`), but only
  `foundation.vllm_generate` exercises it — `foundation.generate` continues
  to reject any backend other than `transformers`.
- Core install and `oec[foundation]` are both unaffected: no new dependency,
  no new extra, Windows and `--all-extras` behavior unchanged.
