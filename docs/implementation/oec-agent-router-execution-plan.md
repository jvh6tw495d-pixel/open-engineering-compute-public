# OEC agent/router execution plan

Data: 2026-07-30

## Objetivo

Restaurar o modo agent-first do OEC no runtime real do MCP/Hermes, eliminando a falha:

```text
No module named 'agents'
```

O foco deste plano é execução prática. A ideia é dar ao Claude uma sequência clara de trabalho, com critérios de aceite objetivos.

## Estado atual

Hoje o comportamento observado é:

- skills diretas do OEC funcionam;
- `agent.default`, `agent.applied_mathematics` e `agent.optimization_specialist` falham no runtime real;
- o erro principal é de import/runtime, não de matemática, não de backend numérico, nem do contrato OPS.

Resumo:

- OEC raw skills: OK
- OEC `agent.*`: quebrado
- causa provável: a camada `agents/` depende implicitamente da repo root em `sys.path`

## Evidência-base

### 1. Imports diretos no MCP server

O arquivo [src/oec/mcp/server.py](C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC\src\oec\mcp\server.py) importa diretamente:

- `from agents.optimization_specialist.specialist import OptimizationSpecialist`
- `from agents.scientific_reviewer.reviewer import ScientificReviewer`
- `from agents.applied_mathematics.specialist import AppliedMathematicsSpecialist`
- `from agents.time_series.specialist import TimeSeriesSpecialist`
- `from agents.energy.specialist import EnergySpecialist`

### 2. A própria documentação dos agents já avisa

Em [agents/README.md](C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC\agents\README.md), a camada `agents/` é descrita como:

- dev-only companion layer;
- localizada na raiz do repositório;
- fora de `src/oec/`;
- dependente da repo root em `sys.path`.

Isso explica por que:

- `pytest` a partir da raiz pode passar;
- o runtime real do Hermes/MCP pode falhar.

## Plano de execução

## Etapa 1 — confirmar a causa raiz

### Objetivo

Provar com evidência curta que a falha está no import path do runtime MCP.

### Tarefas

1. Identificar o entrypoint real usado para subir o MCP no ambiente do Hermes.
2. Inspecionar o `sys.path` efetivo desse runtime.
3. Reproduzir a importação de `from agents...` nesse mesmo contexto.
4. Confirmar se a importação passa apenas quando a repo root é explicitamente adicionada.

### Resultado esperado

Uma conclusão inequívoca:

- sem repo root no path: falha
- com repo root no path: sucesso

Se isso não ficar provado, não seguir para patch estrutural às cegas.

## Etapa 2 — aplicar o patch mínimo

### Objetivo

Restaurar rapidamente o modo `agent.*` sem refatorar a arquitetura inteira agora.

### Estratégia recomendada

Garantir explicitamente que a raiz do repositório entre em `sys.path` antes dos imports da camada `agents`.

### Pontos possíveis de correção

Preferência:

1. entrypoint/launcher real do MCP usado pelo Hermes
2. fallback dentro de [src/oec/mcp/server.py](C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC\src\oec\mcp\server.py)

### Requisito

O usuário final não pode depender de:

- export manual de `PYTHONPATH`
- abrir shell na raiz
- truques de ambiente de desenvolvimento

### Resultado esperado

As chamadas `agent.*` passam a importar corretamente no runtime real.

## Etapa 3 — criar teste que capture esse bug de verdade

### Objetivo

Impedir regressão do tipo “passa no pytest, quebra no Hermes”.

### Tarefas

1. Adicionar teste de import/runtime que valide a disponibilidade da camada `agents` no contexto do MCP.
2. Garantir que o teste não dependa implicitamente da repo root já estar no `sys.path`.
3. Se necessário, isolar esse cenário em subprocesso controlado.

### Cobertura mínima

Validar estes caminhos:

- `list_agents`
- `agent.default`
- `agent.applied_mathematics`
- `agent.optimization_specialist`

### Resultado esperado

Antes do patch, o teste deve conseguir representar a falha real.

Depois do patch, o teste deve passar.

## Etapa 4 — validar com smoke test real no Hermes

### Objetivo

Comprovar que o problema foi resolvido fora do ambiente de teste local.

### Sequência mínima de smoke test

1. `list_agents`
2. `agent.default` com pedido textual simples de otimização
3. `agent.optimization_specialist` com `demo_label`
4. `agent.applied_mathematics` com caso simples governado

### Critério

Não basta passar em testes internos. Precisa funcionar no runtime externo real.

### Regra de aceite

Se passar no pytest mas falhar no Hermes, o bug não está resolvido.

## Etapa 5 — preparar correção estrutural

### Objetivo

Eliminar a fragilidade arquitetural que causou o problema.

### Melhor direção de longo prazo

Escolher uma destas abordagens:

1. mover `agents/` para dentro de `src/oec/agents/`
2. transformar `agents/` em pacote companion instalável
3. ajustar o processo de build/install para sempre disponibilizar `agents` ao runtime MCP

### Observação

Essa etapa pode vir depois do patch mínimo, mas não deve ser esquecida.

O patch mínimo resolve a operação; a correção estrutural resolve a causa sistêmica.

## Ordem ideal de execução

Executar nesta ordem:

1. reproduzir a falha de import
2. identificar o startup real do MCP
3. aplicar o patch mínimo de path/import
4. validar os imports dos agents
5. rodar testes MCP/integration
6. rodar smoke real no Hermes
7. documentar follow-up estrutural

## Riscos por caminho

## Caminho A — patch mínimo de `sys.path`

### Vantagens

- diff pequeno
- restaura o fluxo rápido
- menor risco imediato de quebrar outras áreas

### Riscos

- mantém dependência implícita de path
- pode esconder problema de empacotamento
- pode voltar a quebrar em outro launcher/runtime

## Caminho B — correção estrutural

### Vantagens

- aproxima desenvolvimento e produção
- elimina dependência frágil de cwd/PYTHONPATH
- melhora previsibilidade do MCP agent-first

### Riscos

- diff maior
- pode exigir ajuste de imports, testes e docs
- maior chance de efeitos colaterais no curto prazo

## Recomendação prática

Fazer em duas fases:

### Fase 1

Aplicar o patch mínimo para restaurar operação agora.

### Fase 2

Abrir sequência de hardening para empacotar `agents/` corretamente.

## Critérios mínimos de aceite

Só considerar pronto quando tudo abaixo for verdadeiro:

1. `list_agents` responde no Hermes.
2. `agent.default` seleciona corretamente um specialist.
3. `agent.optimization_specialist` executa com `demo_label`.
4. `agent.applied_mathematics` executa um caso simples governado.
5. Nenhuma dessas chamadas depende de ação manual do usuário para ajustar path.
6. Existe pelo menos um teste automatizado cobrindo esse cenário de runtime.

## Definição de pronto

O problema só está realmente resolvido quando:

- o modo default documentado do MCP volta a funcionar;
- o Hermes consegue usar `agent.default`;
- os specialists deixam de falhar por import;
- a correção fica protegida por teste;
- o time registra, separadamente, a dívida técnica de empacotamento estrutural, se o patch inicial for apenas paliativo.

## TL;DR operacional

- Confirmar o import bug no runtime real
- Corrigir path/import no startup do MCP
- Testar `list_agents` + `agent.default` + specialists
- Validar no Hermes
- Registrar follow-up estrutural para empacotar `agents/` direito
