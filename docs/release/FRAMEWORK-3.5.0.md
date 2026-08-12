# OEC 3.5.0 — Scientific Framework cut (W0–W8)

**Version:** `3.5.0`
**Baseline skills:** 144+ (includes foundation domain)

## Waves delivered

| Wave | Status |
|------|--------|
| W0 Architecture freeze | Specs + ADR 0034/0035 |
| W1 Scientific core MVP | distributions, hypothesis, jacobian, PDE 1D |
| W2 Experiment Engine | run_experiment, binds, gates, artifacts, REST, MCP |
| W3 Applied sciences MVP | waves/optics/EM/ideal-gas/thermochem |
| W4 Neural re-homolog | experiment builders for MLP + training modes |
| W5 Evolutionary re-homolog | optimize_single, NSGA2, hybrid; NEAT deferred |
| W6 Foundation models | `oec[foundation]`, embed/generate/capabilities |
| W7 Cross-domain library | `oec.experiment.cross_domain` |
| W8 Hardening | version, backends CLI, builders CLI, registry |

## Install

```bash
pip install -e ".[mcp,api,neural,evolutionary,foundation,optimization]"
```

Core remains free of torch / pymoo / transformers.

## Key CLIs

```bash
oec version
oec backends --json
oec experiment builders --json
oec experiment run --spec-file experiments/w3_wave_optics.json
```

## Out of scope (POST-OEC / later)

- Persistent scientific harness / autonomous agents
- NEAT/HyperNEAT productization
- Full PEFT train skill
- vLLM / llama.cpp adapters
