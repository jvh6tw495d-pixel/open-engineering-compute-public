# Superteste consolidado de modelos

Data: 2026-07-28

## Escopo

Este consolidado junta duas execuções:

- rodada base direta: NIM + Ollama + OpenCode Go
- rodada Anthropic local: Claude CLI (`sonnet`, `opus`, `fable`)

Arquivos-fonte:

- `docs/implementation/DIRECT_MODEL_SUPERTEST_RESULTS.json`
- `docs/implementation/DIRECT_MODEL_SUPERTEST_REPORT.md`
- `docs/implementation/CLAUDE_DIRECT_SUPERTEST_RESULTS.json`
- `docs/implementation/CLAUDE_DIRECT_SUPERTEST_REPORT.md`

## O que foi testado

Cada modelo foi avaliado em três modos:

- A: sem OEC
- B: extração estruturada pelo modelo + execução pelo OEC
- C: geração de OPS JSON pelo modelo + validação/execução pelo OEC

## Resultado executivo

### Melhores resultados confirmados

| Modelo | Provedor | A sem OEC | B extração + OEC | C OPS + OEC | Observação |
|---|---|---:|---:|---:|---|
| `opus` | `claude-cli` | 10 | 10 | 5 | melhor desempenho bruto sem OEC; empatou com OEC no modo B |
| `sonnet` | `claude-cli` | 7 | 10 | 5 | forte sem OEC, excelente com OEC |
| `nvidia/nemotron-3-ultra-550b-a55b` | `nvidia` | 0 | 10 | 5 | falhou por timeout sem OEC, mas foi ótimo com OEC |
| `nvidia/nemotron-3-super-120b-a12b` | `nvidia` | 0 | 10 | 5 | mesmo padrão do ultra |
| `z-ai/glm-5.2` | `nvidia` | 0 | 10 | 5 | mesmo padrão do ultra |
| `nemotron-3-nano:4b` | `ollama` | 0 | 10 | 5 | local pequeno, mas muito bom no modo B |
| `qwen2.5:7b-instruct` | `ollama` | 2 | 10 | 5 | local consistente com ajuda do OEC |
| `llama3.1:8b` | `ollama` | 4 | 10 | 5 | melhor local “sem OEC” entre os pequenos testados |

### Padrão principal observado

O padrão mais forte do superteste foi:

- sem OEC: desempenho muito irregular
- com extração estruturada + OEC: melhor modo geral
- com OPS + OEC: funcional, mas ainda abaixo do modo B

Em outras palavras: hoje, o melhor default operacional continua sendo o roteamento para o OEC com extração estruturada.

## Falhas e bloqueios encontrados

### Anthropic

- `sonnet`: OK
- `opus`: OK
- `fable`: bloqueado por créditos de uso

Erro observado no `fable`:

- `Fable 5 requires usage credits`

### OpenCode Go

Todos os modelos dessa rota falharam com `HTTP 403 Forbidden`, incluindo:

- `grok-4.5`
- `glm-5.2`
- `glm-5.1`
- `kimi-k3`
- `kimi-k2.7-code`
- `kimi-k2.6`
- `deepseek-v4-pro`
- `deepseek-v4-flash`
- `mimo-v2.5`
- `mimo-v2.5-pro`
- `hy3`

Interpretação:

- a rota existe
- a chave está configurada
- mas a conta/plano/escopo atual não está autorizando essas chamadas

Ou seja: isso não é falha do benchmark, e sim falha de acesso.

### NIM

Parte dos IDs configurados no fallback não está válida ou disponível hoje:

- vários `404 Not Found`
- alguns `410 Gone`

Isso indica drift de catálogo/model IDs na NIM, não problema do OEC.

### OpenAI “puro”

Não foi incluído nesta rodada porque não há credencial `OPENAI_API_KEY` ativa no ambiente local do Hermes.

## Conclusões práticas

1. O default mais robusto continua sendo:
   - modelo extrai estrutura
   - OEC resolve
   - resposta final sai com suporte do OEC

2. `opus` foi o melhor modelo puro desta leva.

3. `sonnet` também foi muito bem e já entrega um comportamento forte para uso geral.

4. Entre os modelos locais pequenos, `llama3.1:8b` foi o melhor sem OEC, e `nemotron-3-nano:4b` ficou muito forte no modo B.

5. A rota OpenCode Go ainda não pode entrar numa comparação “justa” porque está barrada por `403`.

6. A configuração NIM precisa de uma limpeza de IDs inválidos para o fallback ficar realmente confiável.

## Próximos passos recomendados

### Prioridade alta

1. Limpar os modelos NIM com `404/410` do fallback do Hermes.
2. Resolver a autorização do OpenCode Go para destravar `grok`, `glm`, `kimi`, `deepseek-v4`, `mimo` e `hy3`.
3. Manter `extract + OEC` como modo padrão do router do OEC.

### Prioridade média

4. Adicionar OpenAI puro ao benchmark assim que houver `OPENAI_API_KEY`.
5. Rodar uma segunda bateria só com os “melhores sobreviventes” para comparação mais profunda.

### Prioridade opcional

6. Fazer um benchmark final “champions only” com:
   - `opus`
   - `sonnet`
   - `nvidia/nemotron-3-ultra-550b-a55b`
   - `nvidia/nemotron-3-super-120b-a12b`
   - `z-ai/glm-5.2`
   - `nemotron-3-nano:4b`
   - `llama3.1:8b`

## Artefatos gerados nesta rodada

- `scripts/direct_model_supertest.py` agora suporta também `claude-cli`
- `docs/implementation/CLAUDE_DIRECT_SUPERTEST_RESULTS.json`
- `docs/implementation/CLAUDE_DIRECT_SUPERTEST_REPORT.md`
- `docs/implementation/SUPERTEST_CONSOLIDATED_REPORT.md`
