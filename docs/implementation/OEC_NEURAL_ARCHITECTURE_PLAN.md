# OEC Neural Architecture IR — Plano de Implementação

## 1. Contexto

O OEC já possui runtime e skills neurais para famílias como:

- MLP;
- CNN1D;
- LSTM / GRU;
- TCN;
- Transformer encoder;
- Autoencoder;
- GCN / GraphSAGE / GAT.

Também possui infraestrutura evolutionary/neuroevolution.

O gap atual é outro: o OEC conhece principalmente **famílias executáveis**,
mas ainda não possui uma representação arquitetural composicional e governada
que expresse:

```text
Primitive
  ↓
Activation
  ↓
Block
  ↓
Motif
  ↓
Family
  ↓
Macroarchitecture
```

O objetivo desta iniciativa é preencher esse intervalo.

---

## 2. Objetivo

Adicionar ao OEC uma camada declarativa:

```text
oec.neural.architecture
```

capaz de responder perguntas como:

- quais blocos aceitam um `VECTOR`?
- quais blocos produzem uma `SEQUENCE`?
- um `Conv2D` pode conectar diretamente a um `KAN`?
- qual adapter é necessário entre `FEATURE_MAP_2D` e `VECTOR`?
- esta arquitetura forma um grafo válido?
- quais famílias estão disponíveis no catálogo governado?

A camada não treina redes diretamente.

Ela descreve e valida arquitetura.

A execução continua sendo responsabilidade do runtime neural do OEC/PyTorch.

---

## 3. Arquitetura-alvo

```text
                         OEC
                          │
                   Neural Skills
                          │
                    Neural Runtime
                          │
          ┌───────────────┴───────────────┐
          │ Neural Architecture IR v0.1  │
          └───────────────┬───────────────┘
                          │
          ┌───────────────┼────────────────┐
          │               │                │
       Taxonomy      Block Registry   Compatibility
          │               │                │
          └───────────────┼────────────────┘
                          │
                    ArchitectureGraph
                          │
                       PyTorch
```

A ordem conceitual é:

1. IR descreve;
2. validator verifica;
3. builder futuro materializa;
4. runtime treina;
5. result/provenance registra.

---

## 4. Princípios de projeto

### 4.1 Fail-closed

Arquiteturas desconhecidas ou conexões incompatíveis devem falhar.

Nunca:

```python
try:
    build_anything(user_python)
except:
    pass
```

### 4.2 Catálogo fechado

Blocos válidos são registrados explicitamente.

### 4.3 IR pertencente ao OEC

A representação não deve depender de objetos internos de PyTorch,
PyG ou outra biblioteca.

### 4.4 Backends substituíveis

O IR descreve sem depender do backend.

No futuro:

```text
Architecture IR
├── PyTorch builder
├── JAX builder
└── outro backend
```

sem alterar o contrato científico.

### 4.5 Compatibilidade explícita

Cada bloco declara:

- input kind;
- output kind;
- rank;
- constraints;
- capabilities.

### 4.6 Adapters explícitos

Mudanças de representação não devem ser implícitas.

Exemplo:

```text
FEATURE_MAP_2D
    ↓ GlobalAveragePool2D
VECTOR
    ↓ KAN
VECTOR
```

e não:

```text
FEATURE_MAP_2D → KAN
```

com reshape silencioso.

---

## 5. Hierarquia da taxonomia

### Nível A — Primitives

- Linear
- Conv1D
- Conv2D
- Conv3D
- Pool
- MatMul
- Add
- Multiply
- Softmax
- SplineFunction
- MessagePassing

### Nível B — Activations

- ReLU
- LeakyReLU
- PReLU
- ELU
- SELU
- GELU
- SiLU / Swish
- Mish
- Tanh
- Sigmoid
- Softplus

### Nível C — Blocks

- MLP
- ResidualMLP
- GLU
- GEGLU
- SwiGLU
- ConvBlock
- ResidualConv
- AttentionBlock
- TransformerBlock
- KANBlock
- LSTMBlock
- GRUBlock
- TCNBlock
- GCNBlock
- GraphSAGEBlock
- GATBlock

### Nível D — Motifs

- ResidualStack
- Encoder
- Decoder
- Bottleneck
- InceptionBranch
- DenseConnectivity
- MultiBranchFusion
- MessagePassingStack

### Nível E — Families

- FeedForward
- Convolutional
- Recurrent
- Attention
- Transformer
- KAN
- Graph
- Spiking
- ContinuousDepth / Neural ODE
- Neural Operator
- Physics-Informed

### Nível F — Macroarchitectures

- Autoencoder
- Denoising Autoencoder
- VAE
- EncoderDecoder
- Siamese
- MixtureOfExperts
- GAN
- Diffusion denoiser graph

---

## 6. Tipos neurais iniciais

O IR v0.1 deve começar pequeno:

```text
SCALAR
VECTOR
SEQUENCE
IMAGE_1D
IMAGE_2D
VOLUME_3D
FEATURE_MAP_1D
FEATURE_MAP_2D
FEATURE_MAP_3D
GRAPH
NODE_FEATURES
GRAPH_EMBEDDING
LATENT
ANY
```

`ANY` só deve ser permitido para elementos puramente estruturais e nunca
como atalho para ignorar compatibilidade.

---

## 7. BlockSpec

Contrato mínimo:

```python
BlockSpec(
    id="swiglu",
    family=NeuralFamily.FEEDFORWARD,
    category=BlockCategory.BLOCK,
    input_kinds={TensorKind.VECTOR},
    output_kind=TensorKind.VECTOR,
    parameters={...},
    capabilities={...},
)
```

Campos recomendados:

- `id`
- `display_name`
- `family`
- `category`
- `input_kinds`
- `output_kind`
- `parameter_schema`
- `capabilities`
- `experimental`
- `backend_requirements`
- `notes`

---

## 8. Compatibility Engine

API-alvo:

```python
check_connection(source_spec, target_spec)
```

Resultado:

```python
CompatibilityResult(
    compatible=False,
    reason="FEATURE_MAP_2D cannot feed VECTOR-only KAN block",
    suggested_adapters=["global_avg_pool_2d"],
)
```

O importante é não conectar por tentativa.

---

## 9. Architecture Graph IR

Estrutura mínima:

```text
ArchitectureGraph
├── nodes: NodeGene[]
└── edges: EdgeGene[]
```

`NodeGene`:

- id;
- block_id;
- config.

`EdgeGene`:

- source;
- target.

A v0.1 não precisa representar pesos.

É arquitetura, não checkpoint.

---

## 10. Builders futuros

Depois do IR estabilizar:

```text
oec.kernel.neural.builders
├── pytorch_graph_builder.py
├── pytorch_blocks.py
└── parameter_validation.py
```

A construção deve usar exclusivamente registros conhecidos.

---

## 11. Integração com skills existentes

Não quebrar:

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

Em uma wave posterior, cada skill pode publicar também uma representação
`ArchitectureGraph` equivalente.

Exemplo:

```text
neural.mlp.classifier
    ↓
ArchitectureGraph
    ↓
PyTorch builder
```

Mas isso não precisa ocorrer na primeira PR.

---

## 12. KAN

KAN deve entrar após o núcleo do IR estar pronto.

Primeiro:

```text
KANBlock:
VECTOR → VECTOR
```

com catálogo fechado de basis:

```text
bspline
rbf
```

O OEC não precisa implementar matemática KAN do zero; pode usar backend
governado em wave futura.

---

## 13. O que não fazer agora

Não incluir:

- TITAN;
- NAS;
- busca arquitetural;
- mutation/crossover;
- HST;
- fitness;
- population;
- seleção;
- geração de código Python arbitrário;
- HyperNEAT;
- modelos foundation dentro do Architecture IR.

O objetivo desta etapa é **preparar o terreno**.

---

## 14. Definition of Done v0.1

- enum de famílias;
- enum de tipos tensoriais;
- `BlockSpec`;
- registry fechado;
- catálogo inicial;
- compatibility checker;
- adapters iniciais;
- `ArchitectureGraph`;
- validação de DAG;
- testes unitários;
- documentação;
- nenhum `torch` obrigatório no import do IR.

---

## 15. Critério de sucesso

Se o seguinte for possível sem importar PyTorch, v0.1 cumpriu o objetivo:

```python
graph = ArchitectureGraph(...)
graph.validate(default_registry)
```

e o sistema conseguir explicar:

```text
VALID
```

ou:

```text
INVALID:
conv2d outputs FEATURE_MAP_2D,
kan accepts VECTOR.
Suggested adapter: global_avg_pool_2d
```

Esse é o conhecimento arquitetural que posteriormente poderá ser consumido
por mecanismos externos de busca, sem acoplar esses mecanismos ao runtime.
