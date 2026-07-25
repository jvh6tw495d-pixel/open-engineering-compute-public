# Sprint 01 — Contrato e registry de skills

- **Datas:** 2026-07-24/25 (execução em sessão única)
- **Executor:** Claude Code
- **Status:** concluída

## Objetivo

Tornar uma skill um objeto carregável, validável e versionado: parser de
`skill.yaml`/`skill.md`, `SkillLoader`, `SkillRegistry`, lifecycle, erros
estruturados e uma CLI mínima de listagem e inspeção.

## Entregas

- **Correção de forma do `SkillManifest`** (achado no início da sprint):
  o Sprint 00 tinha modelado `input_schema`/`output_schema` e
  `execution_policy`/`validation_policy` como campos flat, divergindo do
  exemplo de `skill.yaml` da seção 8.2 do plano (que usa blocos aninhados
  `schemas:`/`execution:`/`validation:`). Corrigido antes de escrever
  qualquer `skill.yaml` real, para que os arquivos batam com o formato
  que o plano efetivamente especifica.
- `oec.skills.loader.frontmatter`: `SkillFrontMatter` + `parse_front_matter`
  — parser do bloco YAML `---` no topo do `skill.md`.
- `oec.skills.loader.loader`: `load_skill(path) -> LoadedSkill` — carrega
  `skill.yaml`, carrega `skill.md`, cruza os dois (id/version/status/
  domain/title precisam bater), confirma que o arquivo do entrypoint
  existe (sem importar/executar) e que os JSON Schemas de entrada/saída
  existem e são JSON válido.
- `oec.skills.registry.registry`: `SkillRegistry` — `register`,
  `register_all` (discovery recursivo, falhas não derrubam os irmãos),
  `list_skills` (exclui `retired` por padrão), `get_skill` (resolve a
  versão mais alta não-retirada, ou uma versão exata), `search`
  (domínio/tags), `validate`. Conflito de `id`+`version` duplicado levanta
  `SkillVersionConflictError`.
- `oec.skills.lifecycle.lifecycle`: `is_loadable_by_default`,
  `validate_transition` (proíbe regressão de status, ex.: `stable` →
  `experimental`).
- 3 novas subclasses de erro: `SkillFrontMatterError`,
  `SkillEntrypointError`, `SkillVersionConflictError`.
- `oec.cli.main`: `oec version`, `oec skills list/inspect/validate`
  (saída humana via Rich e `--json`; `--debug` relança a exceção real;
  exit code 1 em falha). CLI agora é dependência core, não extra opcional.
- Skill experimental de exemplo: `tests/fixtures/skills/mathematics/identity/`
  — decisão consciente de não colocá-la em `skills/` (catálogo real de
  skills de engenharia, seção 14), já que é apenas fixture de teste do
  loader/registry, não uma skill de engenharia de verdade.
- `tests/_skill_helpers.py` + `tests/conftest.py`: helper
  `write_skill_dir()` compartilhado entre `tests/unit` e `tests/property`.
- 94 testes no total (68 novos nesta sprint): unitários (loader, registry,
  lifecycle, frontmatter, CLI via `typer.testing.CliRunner`) e 2 suites de
  teste de propriedade (Hypothesis): robustez da validação de id/version
  do manifesto, e resolução correta da versão máxima pelo registry.

## Arquivos alterados

31 arquivos novos/modificados (ver commits abaixo para o detalhamento
exato por área).

## Commits

```text
c578a19 chore: promote pyyaml/typer/rich to core dependencies
6291d64 chore(pre-commit): add new core deps to the mypy hook's isolated env
5b73c11 refactor(skills): reshape SkillManifest and extend the error hierarchy
5a002f9 feat(skills): add lifecycle transition rules
80a4008 feat(skills): add skill.md front matter parser
992d4de feat(skills): add SkillLoader and the mathematics.identity example skill
8517733 feat(skills): add SkillRegistry
81a4e0d feat(cli): add oec version and skills list/inspect/validate
2ef5c4f test: add property-based tests for manifest validation and version resolution
9000f94 docs(development): update codebase map for Sprint 01
```

Todos locais; nenhum remote configurado, nenhum push.

## Testes

```text
uv run pytest -q
94 passed in ~11s
```

## Cobertura

99% em `src/oec` (410 statements, 1 miss — `cli/main.py`'s
`if __name__ == "__main__":` guard, which is standard boilerplate not
exercised under pytest). Todos os módulos novos (`loader.py`,
`models.py`, `frontmatter.py`, `registry.py`, `lifecycle.py`,
`manifest.py`) em 100%; `cli/main.py` em 95% — acima do critério de
aceite de ≥90% por módulo.

## Checks executados

| Check | Resultado |
|---|---|
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 55 files already formatted |
| `uv run mypy` (strict) | Success: no issues found in 28 source files |
| `uv run bandit -c pyproject.toml -r src/oec` | No issues identified |
| `uv run pytest -q` | 94 passed, 99% coverage |
| `uv build` | sdist + wheel built successfully |
| `graphify update .` | 376 nodes, 634 edges, 41 communities |

## Graphify

Atualizado ao final da sprint (`uv tool run --from graphifyy graphify
update .`). Cresceu de 143→376 nós e 166→634 arestas. `write_skill_dir()`
(helper de teste) e `load_skill()` são agora os nós de maior grau do
grafo — esperado, dado que quase todo teste da sprint passa pelo loader
através desse helper. `docs/development/codebase-map.md` atualizado com
o fluxo de execução atual (discover → load → validate → resolve, ainda
sem execução real).

## Decisões

- **Reshape do `SkillManifest` antes de qualquer skill real** — evita
  reescrever `skill.yaml` fixtures/exemplos depois; documentado como
  achado desta sprint, não como uma escolha nova (é uma correção de um
  desvio da Sprint 00 em relação ao plano).
- **Skill de exemplo em `tests/fixtures/`, não em `skills/`** — mantém o
  catálogo público de skills (seção 14) livre de uma skill fictícia sem
  metodologia real; a fixture existe só para provar que loader/registry
  funcionam ponta a ponta.
- **Loader nunca importa o módulo de implementação da skill** — só
  confirma que o arquivo existe. Alinhado à seção 4.7 (não executar
  código não confiável sem necessidade); a Execution Service (Sprint 03)
  é quem vai de fato importar/rodar.
- **`typer`/`rich` viraram dependências core**, não mais extra `cli` —
  a CLI já é entregável a partir desta sprint, então instalar `oec`
  precisa funcionar sem flags de extras.
- **Hook mypy do pre-commit precisou de `additional_dependencies`
  explícitas** (`pyyaml`, `types-PyYAML`, `typer`, `rich`) porque roda em
  venv isolado, separado do ambiente `uv` do projeto — descoberto ao
  tentar o primeiro commit desta sprint; documentado para não repetir o
  troubleshooting em sprints futuras.
- **Ordem de commit importa quando há stash de pre-commit**: arquivos
  *tracked e modificados* (não os *untracked*) são stashados durante o
  hook; se um arquivo untracked já referencia a forma nova de um arquivo
  tracked-mas-ainda-não-commitado, o mypy do hook vê uma mistura
  inconsistente. Resolvido commitando `manifest.py`+`errors.py` juntos,
  antes de qualquer arquivo que dependa deles.

## Riscos

- Nenhum caminho de execução real ainda tocou o `implementation.py` de
  uma skill — a Execution Service (Sprint 03) é o primeiro lugar que vai
  de fato importar/rodar código de skill, e é onde riscos de
  sandboxing/timeout real aparecem pela primeira vez.
- `oec skills list` sem `--skills-root` aponta para `./skills` por
  padrão, que hoje está vazio — comportamento correto, mas fácil de
  confundir com "a CLI está quebrada" ao rodar sem argumentos antes da
  Sprint 04/08 popularem o catálogo real.

## Dívida técnica

- `SkillLifecycle.validate_transition` implementado e testado, mas ainda
  não chamado de lugar nenhum em runtime (não existe fluxo de
  atualização/re-registro de skill ainda).
- Loader valida que os arquivos de schema são JSON sintaticamente válido,
  mas não valida contra o meta-schema do JSON Schema — deferido para a
  Validation Engine (Sprint 03).
- Duas branches menores não cobertas em `cli/main.py` (mensagem de erro
  sem `details`; `__main__` guard) — aceitável dentro do critério de
  ≥90% por módulo, mas listado para não esquecer.

## Itens adiados

Execution Service, Validation Engine, engine de unidades (Pint), skills
matemáticas/elétricas reais, REST API, MCP, Odysseus, Open Science — tudo
conforme escopo da Sprint 01 (seção 33).

## Próxima sprint

**Sprint 02 — Kernel de unidades e normalização** (semanas 5–6): Pint,
`QuantityValue`, conversão, normalização, validação dimensional, ADR de
unidades.
