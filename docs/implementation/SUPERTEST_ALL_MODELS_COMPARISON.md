# Comparativo geral — superteste de todos os modelos

Data: 2026-07-28

Legenda:

- A = sem OEC
- B = extração estruturada + OEC
- C = OPS JSON + OEC
- OK = executou de verdade
- Parcial = executou, mas com falha em um dos braços
- Bloqueado = falha de acesso/plano/permissão
- Inválido = endpoint/model ID indisponível

## 1. Comparativo — só modelos que realmente executaram o teste

| Modelo | Grupo | A | B | C | Melhor | Status | Leitura curta |
|---|---|---:|---:|---:|---|---|---|
| `gpt-5.6-sol` | OpenAI interno | - | - | - | ótimo analítico | OK | achou o ótimo global candidato e contou 3 máximos locais mais conservadores |
| `gpt-5.6-terra` | OpenAI interno | - | - | - | ótimo analítico | OK | achou o mesmo ótimo e contou 5 máximos locais incluindo fronteira tangencial |
| `opus` | Claude CLI | 10 | 10 | 5 | A/B | OK | melhor desempenho puro entre os LLMs testados diretamente |
| `sonnet` | Claude CLI | 7 | 10 | 5 | B | OK | muito forte, principalmente com OEC |
| `nvidia/nemotron-3-ultra-550b-a55b` | NIM | 0 | 10 | 5 | B | Parcial | timeout no modo A; excelente com OEC |
| `nvidia/nemotron-3-super-120b-a12b` | NIM | 0 | 10 | 5 | B | Parcial | mesmo padrão do ultra |
| `z-ai/glm-5.2` | NIM | 0 | 10 | 5 | B | Parcial | muito forte com OEC |
| `llama3.1:8b` | Ollama | 4 | 10 | 5 | B | OK | melhor local pequeno no modo A |
| `qwen2.5:7b-instruct` | Ollama | 2 | 10 | 5 | B | OK | local consistente |
| `nemotron-3-nano:4b` | Ollama | 0 | 10 | 5 | B | Parcial | parsing ruim no A, muito bom no B |
| `hf.co/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF:Q4_K_M` | Ollama | 0 | 10 | 5 | B | Parcial | erro 500 no A; bom com OEC |
| `deepseek-r1:8b` | Ollama | 0 | 0 | 0 | - | Falhou | timeout/extração ruim |

## 2. Ranking prático — só quem realmente está utilizável

### Melhor resposta pura, sem OEC

| Posição | Modelo | Nota A | Observação |
|---|---:|---:|---|
| 1 | `opus` | 10 | melhor puro |
| 2 | `sonnet` | 7 | muito forte |
| 3 | `llama3.1:8b` | 4 | melhor local pequeno |
| 4 | `qwen2.5:7b-instruct` | 2 | aceitável |

### Melhor uso operacional com OEC

| Grupo | Modelos que chegaram a 10 no modo B |
|---|---|
| OpenAI interno | `gpt-5.6-sol`, `gpt-5.6-terra` resolveram o problema diretamente com alta confiança analítica, então entram acima como referência qualitativa |
| Claude | `opus`, `sonnet` |
| NIM | `nvidia/nemotron-3-ultra-550b-a55b`, `nvidia/nemotron-3-super-120b-a12b`, `z-ai/glm-5.2` |
| Ollama | `llama3.1:8b`, `qwen2.5:7b-instruct`, `nemotron-3-nano:4b`, `Qwythos-9B-Claude-Mythos-5-1M` |

## 3. Consensos e diferenças

### Consenso forte

- o melhor modo operacional hoje é `B = extração + OEC`
- `OPS + OEC` ainda funciona, mas perde para o modo B
- `opus` e `sonnet` foram os melhores LLMs “puros” testados diretamente
- `sol` e `terra` convergiram para o mesmo ótimo:
  - `x = -0.00931758`
  - `y = 1.58136796`
  - `f = 8.10621358944`

### Diferença relevante

- `sol` contou 3 máximos locais
- `terra` contou 5

Isso não muda o ótimo global; muda só o critério de contagem de máximos de fronteira.

## 4. Leitura executiva

Se a pergunta for “quem é melhor para produção hoje?”, a resposta fica:

1. `extract + OEC` como default
2. `opus` e `sonnet` como melhores modelos puros
3. `nemotron ultra/super` e `glm-5.2` da NIM como melhores parceiros do OEC
4. `llama3.1:8b` como melhor pequeno local geral

Se a pergunta for “o que está impedindo a comparação completa?”, a resposta fica:

- OpenCode Go está barrado por `403`
- parte do catálogo NIM no fallback está quebrado (`404/410`)
- `fable` está sem créditos

## 5. Próximos passos

1. limpar fallback NIM inválido
2. destravar OpenCode Go
3. manter OEC router com default em agentes/extração
4. se quiser um ranking final enxuto, usar só:
   - `gpt-5.6-sol`
   - `gpt-5.6-terra`
   - `opus`
   - `sonnet`
   - `nvidia/nemotron-3-ultra-550b-a55b`
   - `nvidia/nemotron-3-super-120b-a12b`
   - `z-ai/glm-5.2`
   - `llama3.1:8b`
   - `qwen2.5:7b-instruct`
