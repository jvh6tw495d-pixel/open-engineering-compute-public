Você é um engenheiro de stress test de física computacional. Gere casos de stress
adversarial para os 5 skills de física do release OEC 2.6.0 (P1–P5), para medir
DESEMPENHO e ROBUSTEZ deles rodando via a engine (validação de schema + subprocess
sandboxed). NÃO é para gerar casos que quebrem o schema — queremos casos VÁLIDOS
no schema porém desafiadores, para ver se a engine e a física aguentam.

# Skills e seus schemas de entrada

Abaixo está o input.schema.json de cada skill (respeite EXATAMENTE os tipos,
required, minimum/exclusiveMinimum, formats).

{SCHEMAS}

# O que gerar

Para CADA um dos 5 skills, gere exatamente estes 6 casos de stress:

1. edge_schema      — valores no limite do schema (ex: minItems=1 exatamente;
                      exclusiveMinimum logo acima de 0; strings minLength=1).
2. near_singular    — matriz/circuito quase singular (ex: redes quase
                      degeneradas, condutâncias quase iguais, valores extremos).
3. scale_up         — escala bem maior que o exemplo (ex: rede de ~50-100 barras
                      p/ dc_power_flow; malha/fatias numerosas p/ condução).
4. extreme_values   — magnitudes extremas mas válidas (ex: suscetâncias 1e6,
                      temperaturas 1e5 K, tensões tração 1e12 Pa — se o schema
                      permitir).
5. unbalanced_phys  — caso fisicamente consistente porém desbalanceado de forma
                      que o residual/balance DEVE reportar (não crashar) —
                      p/ validação da robustez do balance reporting.
6. adversarial      — payload válido no schema mas intencionalmente perverso:
                      nomes de barra maliciosos, strings com unicode/emojis,
                      muita repetição, injections do tipo muito parecidas mas
                      distintas — para ver se a engine aguenta sem crash.

REGRAS:
- TODOS os casos devem passar na validação de schema. Não adicione campos
  inexistentes, não viole required nem minimum.
- Não invente campos fora do schema.
- Para dc_power_flow: a soma das injections de barras não-slack não precisa ser
  zero (vamos ver o residual), mas cada suscetância > 0.
- Para cada skill, inclua um campo "oracle" SOMENTE quando houver um resultado
  fisicamente trivial que você possa calcular com segurança de cabeça
  (ex: fluxo de calor em regime estácionário de placa com dT simples, energia de
  queda livre m*g*h, tensão de uniaxial E*strain). Use unidades SI consistentes
  com o schema. Se não puder calcular com certeza, OMITA o oracle.
- Forneça o "name" curto de cada caso no formato "<skill_id>::<categoria>".

# FORMATO DE SAÍDA OBRIGATÓRIO

Responda EXCLUSIVAMENTE com um JSON válido (sem markdown, sem texto fora), neste shape:

{
  "cases": [
    {
      "skill_id": "electrical.dc_power_flow",
      "name": "electrical.dc_power_flow::edge_schema",
      "inputs": { ... },
      "oracle": { "campo.aninhado": valor }      // opcional
    },
    ...
  ]
}

O harness lê "cases" direto. Campo "inputs" DEVE conter exatamente o que o
skill espera no schema. Total: 5 skills x 6 casos = 30 casos.
