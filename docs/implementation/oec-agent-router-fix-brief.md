# OEC agent/router fix brief

Data: 2026-07-30

## Resumo executivo

Os testes recentes mostram uma separação clara:

- as skills brutas do OEC estão funcionando;
- a camada de agents/router do MCP está quebrada no ambiente atual;
- o sintoma principal é `No module named 'agents'` ao chamar `agent.default`, `agent.applied_mathematics` e `agent.optimization_specialist`.

Conclusão prática: hoje o OEC é confiável quando chamado pelas skills diretas, mas o modo “agent-first” prometido na documentação MCP não está operacional fora do contexto de testes executados a partir da raiz do repositório.

## Evidência já observada

### 1. Skills diretas funcionam

- `linear_least_squares` retornou payload válido e consistente.
- `optimization.lp` reconheceu o payload OPS e chegou ao backend HiGHS.

### 2. Agents de alto nível falham

Falhas reportadas nos testes manuais via host runtime/MCP:

- `agent.default`
- `agent.applied_mathematics`
- `agent.optimization_specialist`

Erro central:

```text
No module named 'agents'
```

### 3. A causa está documentada no próprio repositório

O arquivo [agents/README.md](C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC\agents\README.md) já afirma explicitamente:

- `agents/` fica na raiz do repositório, fora de `src/oec/`;
- imports `from agents.<specialist>...` só resolvem quando a raiz do repositório está em `sys.path`;
- isso costuma funcionar em `pytest` rodando da raiz, mas não é garantido no runtime real do MCP.

Ou seja: o comportamento quebrado no host runtime é compatível com a arquitetura atual.

## Ponto exato do problema

O MCP server importa os agents diretamente em [src/oec/mcp/server.py](C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC\src\oec\mcp\server.py).

Trechos críticos:

- `from agents.optimization_specialist.specialist import OptimizationSpecialist`
- `from agents.scientific_reviewer.reviewer import ScientificReviewer`
- `from agents.applied_mathematics.specialist import AppliedMathematicsSpecialist`
- `from agents.time_series.specialist import TimeSeriesSpecialist`
- `from agents.energy.specialist import EnergySpecialist`

Esses imports acontecem dentro do runtime do MCP, mas o runtime aparentemente não está sendo iniciado com a raiz do repositório no `PYTHONPATH`.

## Diagnóstico

Isto não parece ser:

- falha matemática do OEC;
- falha do backend HiGHS;
- falha do contrato OPS;
- falha primária do modelo local.

Isto parece ser:

- falha de empacotamento/runtime da camada `agents`;
- dependência implícita de `sys.path` de desenvolvimento;
- desalinhamento entre “funciona em testes locais” e “funciona no MCP real”.

## Objetivo da correção

Fazer com que o modo padrão documentado do MCP funcione de verdade:

- `list_agents` deve responder;
- `agent.default` deve rotear e executar;
- `agent.applied_mathematics` deve executar requests governadas;
- `agent.optimization_specialist` deve executar demos e payloads OPS;
- tudo isso sem depender de rodar `pytest` a partir da raiz do repositório.

## Opções de correção

### Opção A — correção mínima de runtime

Garantir que a raiz do repositório entre em `sys.path` quando o MCP server subir.

Exemplos de abordagem:

- ajustar o entrypoint do MCP para injetar a repo root no startup;
- ajustar o launcher usado pelo host runtime/OEC para exportar `PYTHONPATH`;
- resolver a raiz dinamicamente em `src/oec/mcp/server.py` antes dos imports.

Vantagem:

- menor diff;
- restaura rapidamente o funcionamento atual.

Desvantagem:

- continua dependendo de convenção frágil;
- mantém `agents/` como camada “fora do pacote”.

### Opção B — correção estrutural recomendada

Mover ou empacotar a camada de agents de forma que ela seja importável sem hacks de `PYTHONPATH`.

Exemplos:

- transformar `agents/` em pacote instalável do projeto;
- incorporar os agents sob `src/oec/agents/`;
- criar um pacote companion explícito, instalado junto no ambiente que sobe o MCP.

Vantagem:

- elimina o erro de import pela raiz;
- aproxima testes e produção;
- reduz divergência entre docs e runtime real.

Desvantagem:

- diff maior;
- pode exigir ajustes em imports, testes e docs.

## Recomendação

Para destravar rápido sem perder qualidade:

1. aplicar **Opção A** para restaurar o runtime do MCP agora;
2. abrir follow-up para **Opção B** como hardening/2.5.1 ou 2.5.2.

## Critério mínimo de aceite

A correção só deve ser considerada pronta se os cenários abaixo passarem no runtime real do MCP, não só em unit/integration local:

1. `list_agents` responde com catálogo válido.
2. `agent.default` recebe request textual de otimização e seleciona `agent.optimization_specialist`.
3. `agent.optimization_specialist` executa `demo_label: "diet"` e devolve payload válido.
4. `agent.applied_mathematics` executa um caso simples e devolve payload válido.
5. nenhuma dessas chamadas depende de export manual de `PYTHONPATH` pelo usuário.

## Testes recomendados

### A. Teste de import/runtime

Adicionar um teste que simule o cenário real do MCP sem assumir a repo root implicitamente em `sys.path`.

O objetivo é provar:

- ou que o servidor prepara o path corretamente;
- ou que os agents já são importáveis por empacotamento.

### B. Teste E2E MCP real

Expandir ou adaptar [tests/integration/test_mcp_server.py](C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC\tests\integration\test_mcp_server.py) para cobrir explicitamente o path de runtime usado no MCP real, não apenas o ambiente confortável do pytest.

### C. Smoke externo

Após o patch, repetir via host runtime:

- `list_agents`
- `agent.default`
- `agent.optimization_specialist`
- `agent.applied_mathematics`

Se isso não passar no host runtime, a correção ainda não está concluída.

## Observações adicionais

Houve também erros de tool-calling em alguns modelos locais menores, mas isso é um problema separado. O erro `No module named 'agents'` é real e independe da qualidade do modelo. Mesmo um modelo bom continuará falhando se o runtime do OEC não conseguir importar a camada de agents.

## Entrega esperada do patch

O patch ideal deve incluir:

- correção do runtime/import path dos agents;
- teste que falha antes e passa depois;
- nota curta em docs MCP explicando que o modo agent-first agora é suportado no runtime real;
- se a correção for só paliativa, registrar dívida técnica para empacotar `agents/` corretamente.

## TL;DR para execução

- OEC raw skills: OK
- OEC agent/router: quebrado por import/runtime
- erro principal: `No module named 'agents'`
- correção imediata: garantir importabilidade dos agents no runtime do MCP
- aceite real: passar também no host runtime, não só no pytest
