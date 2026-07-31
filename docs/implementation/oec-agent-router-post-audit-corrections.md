# OEC MCP agent router — correções pós-auditoria

**Status:** correções A/B validadas; ranking e domínios órfãos permanecem em aberto
**Base auditada:** working tree sobre `f1c09c3` (v2.5.1)
**Escopo:** router MCP, especialistas de domínio e harness/documentação de stress

## Resumo executivo

A auditoria confirmou que o conserto para o desvio indevido causado por
`execution: {}` é correto: um placeholder alucinado por LLM local não vence
mais um OPS, domínio preferido ou intenção explícita.

O ciclo de descoberta de otimização foi corrigido em duas etapas: o
especialista passou a aceitar `skill_id + inputs` para `optimization.*`, e o
discovery passou a devolver somente o objeto executável de exemplos
envelopados. O ciclo `request → candidate → retry → ExecutionResult` foi
confirmado com status `VALIDATED`.

## Correção A — placeholder `execution` não pode sequestrar o router

### Problema observado

LLMs locais podem chamar `agent.default` com uma solicitação válida de
otimização e incluir `execution: {}`. A regra anterior tratava a mera presença
da chave como sinal de revisão e encaminhava a chamada para
`agent.scientific_reviewer`, que falhava ao validar um `ExecutionResult` vazio.

### Correção implementada e validada

Em `src/oec/mcp/server.py`:

1. adicionar `_has_execution_payload(arguments)`;
2. considerar `execution` como sinal de revisão apenas quando for um objeto
   contendo `status`, `skill`, `method` e `started_at`;
3. manter a precedência existente para os demais sinais quando `execution` for
   vazio ou incompleto:
   `ops`/`ops_document` → `preferred_domain` → `skill_id` → `demo_label` →
   inferência por `request` → erro honesto.

### Evidência de validação

- `execution: {}` + `ops` seleciona `agent.optimization_specialist`;
- `execution: {}` + `preferred_domain: mathematics` seleciona
  `agent.applied_mathematics`;
- `execution` minimamente estruturado ainda seleciona
  `agent.scientific_reviewer`;
- o caso de stress de knapsack, com `ops` válido e `execution: {}`, executa
  pela trilha de otimização sem `ValidationError` do reviewer;
- `tests/integration/test_mcp_server.py`: **65 passed**;
- Ruff no router e nesses testes: **passou**.

### Limite deliberado

A verificação no router é estrutural, não semântica. Um objeto contendo as
quatro chaves mas valores inválidos segue para o reviewer, que continua sendo
a autoridade para validar o `ExecutionResult` completo.

## Correção B — fechar o ciclo de descoberta para otimização (P1 pendente)

### Reprodução confirmada

1. Chamada:

```json
{
  "request": "minimize cost of a linear blending problem",
  "preferred_domain": "optimization"
}
```

2. Resultado não-erro: `agent.default` seleciona
`agent.optimization_specialist` e sugere, por exemplo,
`optimization.cvar_lp`, com `example_inputs`.

3. Repetição conforme a instrução do próprio fallback:

```json
{
  "skill_id": "optimization.cvar_lp",
  "inputs": { "...": "example_inputs retornado" }
}
```

4. Resultado atual:

```json
{
  "error": "agent.optimization_specialist requires 'ops' or 'demo_label'"
}
```

Isso torna o fallback de otimização um beco sem saída operacional, apesar de
ele ser um payload estruturado e não um erro de transporte.

### Correção recomendada

Estender apenas `agent.optimization_specialist` para aceitar o contrato já
anunciado pelo fallback:

```python
if "skill_id" in arguments and "inputs" in arguments:
    skill_id = str(arguments["skill_id"])
    if not skill_id.startswith("optimization."):
        raise ValueError("agent.optimization_specialist only accepts optimization.* skills")
    return engine.run(skill_id, arguments["inputs"]).model_dump(mode="json")
```

Regras adicionais:

- preservar `ops` e `demo_label` como caminhos prioritários e compatíveis;
- não aceitar skills fora de `optimization.` por meio do especialista;
- deixar a validação de schema, unidades e execução sob responsabilidade de
  `Engine.run`, sem duplicar lógica de skills no router;
- manter o resultado/proveniência nativo do `Engine`.

### Testes obrigatórios para a Correção B

1. `agent.default` com pedido de otimização e `preferred_domain` retorna pelo
   menos um candidato `optimization.*`;
2. executar novamente via `agent.default` com `skill_id + example_inputs`
   retorna resultado não-erro;
3. executar diretamente em `agent.optimization_specialist` com o mesmo par
   retorna resultado não-erro;
4. `skill_id` fora de `optimization.*` pelo especialista retorna erro
   estruturado e explícito;
5. teste de ciclo completo:
   `request → candidate → retry → ExecutionResult`;
6. rodar a bateria Ollama após a implementação e registrar o novo artefato,
   sem tratar ausência de chamada de ferramenta pelo modelo como sucesso de
   precisão.

### Correção complementar necessária — normalizar `example_inputs`

Durante a validação independente do retry, foi encontrado um segundo detalhe
de contrato: vários arquivos em `examples/` usam o envelope humano
`{"description": "…", "input": {…}}`. O discovery entregava o envelope
inteiro como `example_inputs`, mas o contrato manda reutilizá-lo diretamente
como `inputs`. Isso gerava um `ExecutionResult` honesto com status `INVALID`,
porque `description` e `input` não pertencem ao schema da skill.

A correção deve ficar em `oec.mcp.discovery._first_example()`:

- quando o exemplo tiver um campo `input` que seja objeto, devolver somente
  esse objeto;
- preservar exemplos legados já planos;
- testar o retry usando `candidate["example_inputs"]` sem normalização no
  teste, e exigir status utilizável (`VALIDATED`, `VERIFIED`,
  `CONVERGED_WITH_WARNINGS` ou `APPROXIMATE`).

Assim, `example_inputs` volta a significar literalmente o que o nome e a
documentação prometem: um payload pronto para a chamada seguinte.

## Correção C — qualidade do harness de stress (P2)

`scripts/ollama_agent_stress_test.py` reproduz bem o ambiente Hermes, mas
ainda possui dois avisos Ruff e um erro mypy locais ao incluí-lo na checagem.

Correções pequenas:

- substituir o `try/except/pass` ao desserializar argumentos por tratamento
  explícito e tipado;
- combinar os context managers aninhados apontados pelo Ruff;
- converter/validar o retorno JSON de `_ollama_chat` para `dict[str, Any]`
  antes de retorná-lo.

Critério: Ruff e mypy devem passar também para o harness, além do escopo
oficial já aplicado em `src/oec`.

## Correção D — higiene de evidência e documentação (P2)

Antes do commit/release:

1. alinhar a data do relatório de stress com a data real de execução;
2. corrigir caracteres corrompidos no Markdown (`â€”` e similares);
3. descrever o estado com precisão:
   - correto: "fallback de descoberta adicionado";
   - ainda incorreto: "free-text deixou de ser beco sem saída" para
     otimização, até a Correção B estar entregue e comprovada;
4. atualizar `docs/implementation/technical-debt.md` se ele divergir do
   código (por exemplo, quanto à existência de logging nos `except` amplos);
5. só registrar Graphify como evidência do commit que realmente contiver as
   correções, distinguindo a working tree não commitada da release v2.5.1.

## Critério de encerramento

O pacote de correções estará pronto quando:

- a Correção A continuar verde;
- o ciclo de fallback de otimização completar sem erro;
- a repetição guiada por `skill_id + inputs` produzir um resultado governado
  pelo `Engine`;
- a suíte focal de MCP, Ruff e mypy definidos acima passarem;
- um stress pós-fix comprovar estabilidade de transporte e registrar
separadamente os casos em que o modelo escolhe não usar ferramentas.
