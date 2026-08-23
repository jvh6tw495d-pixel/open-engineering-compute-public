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
- glu
- swiglu
- conv1d
- conv2d
- residual_conv
- lstm
- gru
- tcn
- attention
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
- orphan check;
- connection compatibility check;
- deterministic serialization.

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

para `BlockSpec` / `ArchitectureGraph`.

Sem alterar comportamento numérico.

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
- FNO
- DeepONet
- PINN motif

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

A7 aceita somente **cadeia linear estrita** (um root, um sink, `edges == nodes - 1`,
sem forks/joins/componentes desconectados). Grafos ramificados falham fechado.
Blocos sem builder (KAN/GNN/A6 extras) falham fechado **antes** do import torch.

---

## Wave A8 — Governance

Adicionar:

- manifest;
- provenance;
- architecture fingerprint;
- registry version;
- compatibility version;
- experimental/stable status;
- audit de catálogo.

Fingerprint:

```text
sha256(canonical ArchitectureGraph JSON)
```

### Gate

Mesma arquitetura → mesmo fingerprint.

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
- architecture search;
- mutation;
- crossover;
- HST;
- evolvability;
- population ecology;
- autonomous research harness.

Esses consumidores devem entrar somente depois que o IR estiver governado.
