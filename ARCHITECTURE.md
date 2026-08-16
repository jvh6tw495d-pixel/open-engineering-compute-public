# ARCHITECTURE — OEC

> Standing decision: framework layers freeze (W0) · ADR 0034 / ADR 0035
> **Open source:** este repositório não deve conter referências a marcas privadas, clientes ou propriedade intelectual não pública.

---

## 1. Identidade

| Campo | Valor |
|-------|--------|
| Projeto | OEC (Open Engineering Compute) |
| Papel | Biblioteca/motor **open source** de engenharia e ciência computacional governada |
| Owner | comunidade / João (contrib) |
| Produção autorizada? | conforme licença do projeto |
| Versão baseline (W0) | `3.4.1` → roadmap framework `3.5.x` |

---

## 2. Camadas do framework

Documento normativo: **[`docs/architecture/OEC-FRAMEWORK-LAYERS.md`](docs/architecture/OEC-FRAMEWORK-LAYERS.md)**

```text
OEC Architecture
├── Core
├── Applied Sciences
├── ML / Neural
├── Evolutionary
├── Foundation Models
└── Experiment Infrastructure
```

### Regras congeladas

1. **Core ↛ ML/AI** — install core sem torch/transformers
2. **ML/AI → Core** — neural/evo/foundation consomem `ExecutionResult`, units, provenance
3. **Backend externo ≠ API pública** — SciPy/PyTorch/pymoo/HF atrás de contratos OEC

### Fora de escopo (POST-OEC)

Harness científico persistente (agentes autónomos, durable research state) — **não** neste repositório.

---

## 3. Contratos canónicos

| Contrato | Onde |
|----------|------|
| Skill + `ExecutionResult` | ADR 0001 / 0007 · `docs/contracts/execution-result.md` |
| Spec family (Experiment, Dataset, Model, …) | ADR 0035 · `src/oec/experiment/specs.py` |
| Experiment layer | ADR 0034 · runner em W2 |
| Neural contracts | ADR 0031 · `src/oec/neural/contracts.py` |
| Backend registry | ADR 0021 |

---

## 4. Roadmap

**[`docs/implementation/FRAMEWORK-ROADMAP-W0-W8.md`](docs/implementation/FRAMEWORK-ROADMAP-W0-W8.md)**

```text
W0 Architecture Freeze → W1 Scientific Core → W2 Experiment Engine
 → W3 Applied Sciences → W4 Neural → W5 Evolutionary
 → W6 Foundation Models → W7 Hybrid experiments → W8 Hardening
```

Prioridade imediata: **W0 → W1 → W2**.

---

## 5. Superfícies de interface

Thin adapters over `Engine` (ADR 0005 / 0015):

- SDK · CLI · REST · MCP
- Agents (`agents/`) — companion layer, fora do wheel core

---

## 6. Dependências de ecossistema

Consumidores externos podem chamar OEC como ferramenta determinística.
Instrumentação de LLM/observability fica **no consumidor**, não no core OEC.
