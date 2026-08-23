# OEC Neural Architecture IR — Waves

## Visão

```text
A0 Contracts
   ↓
A1 Taxonomy
   ↓
A2 Registry
   ↓
A3 Compatibility
   ↓
A4 Graph IR
   ↓
A5 Existing-family mapping
   ↓
A6 Expanded blocks
   ↓
A7 Backend builders
   ↓
A8 Governance / promotion
```

---

## Wave A0 — Contracts

### Entregas

- `TensorKind`
- `NeuralFamily`
- `BlockCategory`
- `BlockSpec`
- `BlockParameterSpec`
- `CompatibilityResult`

### Gate

Nenhuma dependência PyTorch no import.

---

## Wave A1 — Taxonomy

### Famílias iniciais

- feedforward
- convolutional
- recurrent
- attention
- transformer
- graph
- autoencoder
- kan

### Ativações

- relu
- leaky_relu
- gelu
- silu
- mish
- tanh
- sigmoid
- softplus

### Gate

IDs estáveis e documentados.

---

## Wave A2 — Governed Block Registry

### Blocos iniciais

- linear
- mlp
- residual_mlp
- swiglu
- conv1d
- conv2d
- lstm
- gru
- tcn
- self_attention
- transformer_encoder
- kan
- gcn
- graphsage
- gat
- encoder
- decoder

### Gate

- duplicate IDs falham;
- lookup desconhecido falha;
- catálogo pode ser serializado.

---

## Wave A3 — Compatibility + Adapters

### Adapters iniciais

- flatten
- global_avg_pool_1d
- global_avg_pool_2d
- sequence_pool
- vector_to_sequence
- graph_global_pool

### Gate

Testes:

```text
Conv2D → KAN = invalid
Conv2D → GAP2D → KAN = valid
Transformer → sequence_pool → MLP = valid
GNN → graph_global_pool → MLP = valid
```

---

## Wave A4 — ArchitectureGraph IR

### Entregas

- `NodeGene`
- `EdgeGene`
- `ArchitectureGraph`
- DAG check;
- orphan check (isolated nodes when `len(nodes) > 1`);
- connection compatibility check;
- JSON-finite config;
- deterministic fingerprint (normalized defaults + catalog hash).

### Gate

Um grafo válido e um inválido devem produzir resultados determinísticos.

---

## Wave A5 — Mapear skills existentes

Mapear a superfície atual:

```text
neural.mlp.*
neural.autoencoder.*
neural.cnn1d
neural.lstm
neural.gru
neural.tcn
neural.transformer.*
neural.gcn
neural.graphsage
neural.gat
```

para `BlockSpec` / `ArchitectureGraph`, traduzindo parâmetros
arquiteturais (não epochs/lr/seed). Sem alterar comportamento numérico
das skills.

### Gate

Golden atual continua verde.

---

## Wave A6 — Expandir catálogo neural

### Feedforward

- GEGLU
- residual gated
- highway

### CNN

- depthwise
- separable
- dilated
- grouped
- squeeze-excitation

### Attention

- cross-attention
- local attention
- linear attention

### KAN

- spline KAN
- RBF KAN
- hybrid KAN/MLP

### Continuous / scientific

- NeuralODE
- FNO 1D (`fno`) e FNO 2D (`fno_2d`)
- DeepONet
- PINN motif

GEGLU é SEQUENCE→SEQUENCE. `cross_attention` exige portas nomeadas
`(query, context)` e não entra em cadeia unária.

### Gate

Cada novo bloco possui:

- contrato;
- compatibilidade;
- teste;
- backend requirement explícito.

---

## Wave A7 — Backend Builders

Primeiro backend:

```text
PyTorch
```

API:

```python
build_architecture(graph, registry, backend="torch")
```

### Gate

Architecture IR continua importável sem torch.

`torch` só é requerido no builder.

A7 aceita **cadeia linear estrita** (um root, um sink, sem forks/skips extras/
componentes desconectados), com uma exceção: um nó cujo bloco declara arity > 1
portas de entrada (`cross_attention`) pode ter indegree == arity ("named
join") — ver "Também landed" abaixo. Fora essa exceção, grafos ramificados
falham fechado.

KAN, GNN (`gcn`/`graphsage`/`gat`) e FNO (`fno`/`fno_2d`) têm builders
honestos nesta wave (basis B-spline/RBF real, `build_gnn` reutilizado com
`edge_index` obrigatório em todo nó de grafo, rfft/irfft rank-preserving).
Continuam fail-closed, sem builder, **antes** do import torch:
`local_attention`, `linear_attention`, `neural_ode`, `deeponet`, `pinn_motif`.

---

## Wave A8 — Governance (landed)

`oec.neural.architecture.governance`:

- `ArchitectureManifest` (graph fingerprint, registry version, catalog hash,
  `compatibility_version`, backend, experimental flags used, optional
  `created_at`, closed-key `ArchitectureProvenance`) via `manifest_for_graph()`;
- `audit_catalog()` — duplicate ids, experimental blocks missing
  `backend_requirements`, unknown parameter kinds, unsealed registry, missing
  `input_ports`, experimental/stable id partition. Fail-closed: unsealed
  registry and missing `backend_requirements` are **errors** (`valid=False`),
  not warnings;
- `manifest_for_graph()` fails closed: requires a **sealed** registry,
  requires `graph.validate_graph()` to pass, and closes `backend` to a known
  set (`RegistrySealedError` / `ArchitectureValidationError`);
- `compatibility_version` is part of the fingerprint canonical payload
  (catalog 0.2.1 → 0.2.2 → 0.2.3, the second bump for `output_ports`).

Fingerprint:

```text
sha256(canonical ArchitectureGraph JSON)  # includes compatibility_version
```

### Gate

Mesma arquitetura + mesmo catálogo selado → mesmo fingerprint. **Landed.**

Também landed nesta wave (fora do escopo original de A8, mas dependente dela):

- **Named-port wiring:** `EdgeGene.target_port`/`source_port`; `validate_graph`
  exige que todo `input_port` declarado seja conectado exatamente uma vez;
  `check_connection` verifica apenas tensor kind (arity é checado no grafo).
  `cross_attention` prova o caso: dois roots nomeados (`query`, `context`)
  convergem via named join.
- **A7 torch builders expandidos:** `kan` (B-spline/RBF honesto), `gcn`/
  `graphsage`/`gat` (via `oec.kernel.neural.gnn`, `graph_global_pool` real),
  `fno`/`fno_2d`, `cross_attention`, e os extras A6 honestos (geglu, highway,
  residual_gated, depthwise/separable/dilated/grouped conv,
  squeeze_excitation, self_attention, swiglu, residual_mlp,
  vector_to_sequence, tcn). `local_attention`, `linear_attention`,
  `neural_ode`, `deeponet`, `pinn_motif` continuam fail-closed.
- **A5 hidden_dims N-layer:** `graph_for_skill("neural.mlp.*")` expande
  `hidden_dims` multi-largura em uma cadeia `linear` honesta em vez de
  espremer na primeira largura; autoencoders multi-largura preservam todas
  as larguras declaradas.
- **A8+ search:** `oec.neural.architecture.search.search_graphs()` — busca
  core-safe sobre família fechada de candidatos (MLP/CNN1d/LSTM), objetivo
  fechado e built-in (`objective: Literal["param_count"]`, estimativa de
  parâmetros — sem callback de fitness de nenhum tipo), independente de
  `neural.search_architecture` (ADR 0033) e **não é TITAN**.
- **A8+ port e attention hardening:** `BlockSpec.output_ports` fecha
  `EdgeGene.source_port` (`source_port` desconhecido falha fechado);
  `d_model`/`nhead` exigem `d_model % nhead == 0` e `nhead <= d_model` em
  `validate_config`, antes do torch; blocos de grafo (`gcn`/`graphsage`/
  `gat`) sempre recebem `edge_index`, inclusive fora da raiz da cadeia;
  `fno`/`fno_2d` rejeitam rank incorreto explicitamente.

---

# Sequência recomendada

Para implementação imediata:

```text
PR-1: A0 + A1 + A2
PR-2: A3
PR-3: A4
PR-4: A5
PR-5: A6 Feedforward/CNN/KAN
PR-6: A7 PyTorch builder
PR-7: A8 governance
```

---

# Fora de escopo destas waves

Explicitamente fora:

- TITAN;
- HST;
- evolvability;
- population ecology;
- autonomous research harness.

Esses consumidores devem entrar somente depois que o IR estiver governado.
