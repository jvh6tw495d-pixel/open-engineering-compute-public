Você é um engenheiro de stress test de física computacional. Gere casos de stress
adversarial para os 5 skills de física do release OEC 2.6.0 (P1–P5), para medir
DESEMPENHO e ROBUSTEZ deles rodando via a engine (validação de schema + subprocess
sandboxed). NÃO é para gerar casos que quebrem o schema — queremos casos VÁLIDOS
no schema porém desafiadores, para ver se a engine e a física aguentam.

# Skills e seus schemas de entrada

Abaixo está o input.schema.json de cada skill (respeite EXATAMENTE os tipos,
required, minimum/exclusiveMinimum, formats).

{
  "electrical.dc_power_flow": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "electrical.dc_power_flow input",
    "type": "object",
    "properties": {
      "lines": {
        "type": "array",
        "minItems": 1,
        "items": {
          "type": "object",
          "properties": {
            "from_bus": {
              "type": "string",
              "minLength": 1
            },
            "to_bus": {
              "type": "string",
              "minLength": 1
            },
            "susceptance": {
              "type": "number",
              "exclusiveMinimum": 0,
              "description": "B_ij = 1 / X_ij, per-unit (pu)."
            }
          },
          "required": [
            "from_bus",
            "to_bus",
            "susceptance"
          ],
          "additionalProperties": false
        },
        "description": "Meshed network branches. The graph formed by all lines must be connected."
      },
      "injections": {
        "type": "object",
        "minProperties": 1,
        "additionalProperties": {
          "type": "number"
        },
        "description": "bus id -> active-power injection, per-unit (pu, dimensionless); positive = generation entering the bus. Required for every bus appearing in 'lines', including the slack bus."
      },
      "slack_bus": {
        "type": "string",
        "minLength": 1,
        "description": "Reference bus (theta = 0). Must appear in 'lines'."
      },
      "atol": {
        "type": "number",
        "exclusiveMinimum": 0,
        "description": "Absolute KCL residual tolerance override (pu). Defaults to 1e-9."
      },
      "rtol": {
        "type": "number",
        "exclusiveMinimum": 0,
        "description": "Relative KCL residual tolerance override. Defaults to 1e-9."
      }
    },
    "required": [
      "lines",
      "injections",
      "slack_bus"
    ],
    "additionalProperties": false
  },
  "thermal.conduction_1d": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "thermal.conduction_1d input",
    "type": "object",
    "properties": {
      "conductivity": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number",
            "exclusiveMinimum": 0
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "W / (m * K)"
      },
      "area": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number",
            "exclusiveMinimum": 0
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "m ** 2"
      },
      "length": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number",
            "exclusiveMinimum": 0
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "m"
      },
      "hot_temperature": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number"
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "K",
        "description": "Any temperature-compatible unit (K, degC, degF) is accepted."
      },
      "cold_temperature": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number"
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "K",
        "description": "Any temperature-compatible unit (K, degC, degF) is accepted."
      },
      "heat_out": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number"
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "W",
        "description": "Optional measured/assumed outgoing heat rate. Defaults to the computed heat_rate (trivially balanced) when omitted."
      }
    },
    "required": [
      "conductivity",
      "area",
      "length",
      "hot_temperature",
      "cold_temperature"
    ],
    "additionalProperties": false
  },
  "mechanics.energy_1d": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "mechanics.energy_1d input",
    "type": "object",
    "properties": {
      "mass": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number",
            "exclusiveMinimum": 0
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "kg"
      },
      "height_initial": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number"
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "m"
      },
      "height_final": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number"
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "m"
      },
      "velocity_initial": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number"
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "m / s"
      },
      "velocity_final": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number"
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "m / s"
      },
      "work_in": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number"
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "J",
        "description": "External work done on the system between the two states. Defaults to 0 J."
      },
      "losses": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number",
            "minimum": 0
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "J",
        "description": "Non-conservative losses (friction, drag, ...). Defaults to 0 J."
      },
      "gravity": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number",
            "exclusiveMinimum": 0
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false,
        "x-oec-unit": "m / s ** 2",
        "description": "Defaults to standard gravity (9.80665 m/s^2)."
      }
    },
    "required": [
      "mass",
      "height_initial",
      "height_final",
      "velocity_initial",
      "velocity_final"
    ],
    "additionalProperties": false
  },
  "fluids.bernoulli": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "fluids.bernoulli input",
    "type": "object",
    "$defs": {
      "quantity": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number"
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false
      }
    },
    "properties": {
      "pressure_upstream": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "Pa"
      },
      "pressure_downstream": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "Pa"
      },
      "velocity_upstream": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "m / s"
      },
      "velocity_downstream": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "m / s"
      },
      "elevation_upstream": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "m"
      },
      "elevation_downstream": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "m"
      },
      "density": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "kg / m ** 3"
      },
      "friction_factor": {
        "type": "number",
        "minimum": 0,
        "description": "Darcy friction factor f, dimensionless. Supplied as input; not derived from Reynolds number or pipe roughness."
      },
      "length": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "m"
      },
      "diameter": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "m"
      },
      "gravity": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "m / s ** 2",
        "description": "Defaults to standard gravity (9.80665 m/s^2)."
      }
    },
    "required": [
      "pressure_upstream",
      "pressure_downstream",
      "velocity_upstream",
      "velocity_downstream",
      "elevation_upstream",
      "elevation_downstream",
      "density",
      "friction_factor",
      "length",
      "diameter"
    ],
    "additionalProperties": false
  },
  "materials.linear_constitutive": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "materials.linear_constitutive input",
    "type": "object",
    "$defs": {
      "quantity": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number"
          },
          "unit": {
            "type": "string"
          }
        },
        "required": [
          "value",
          "unit"
        ],
        "additionalProperties": false
      }
    },
    "properties": {
      "material_id": {
        "type": "string",
        "minLength": 1,
        "description": "Sourced material table id (e.g. steel_astm_a36). When set, elastic modulus is looked up; elastic_modulus must be omitted."
      },
      "elastic_modulus": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "Pa",
        "description": "Young's modulus E. Required when material_id is omitted."
      },
      "strain": {
        "type": "number",
        "description": "Engineering strain epsilon (dimensionless). Provide this OR original_length + deformation."
      },
      "original_length": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "m",
        "description": "Gauge length L0. Used with deformation when strain is omitted."
      },
      "deformation": {
        "allOf": [
          {
            "$ref": "#/$defs/quantity"
          }
        ],
        "x-oec-unit": "m",
        "description": "Axial elongation Delta L. Used with original_length when strain is omitted."
      }
    },
    "allOf": [
      {
        "oneOf": [
          {
            "required": [
              "material_id"
            ],
            "not": {
              "required": [
                "elastic_modulus"
              ]
            }
          },
          {
            "required": [
              "elastic_modulus"
            ],
            "not": {
              "required": [
                "material_id"
              ]
            }
          }
        ]
      },
      {
        "oneOf": [
          {
            "required": [
              "strain"
            ],
            "not": {
              "required": [
                "original_length",
                "deformation"
              ]
            }
          },
          {
            "required": [
              "original_length",
              "deformation"
            ],
            "not": {
              "required": [
                "strain"
              ]
            }
          }
        ]
      }
    ],
    "additionalProperties": false
  }
}

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

Regra ABSOLUTA de execução: NÃO use terminal, NÃO leia nenhum arquivo além do
que está neste prompt, NÃO escreva NENHUM arquivo no repositório, NÃO rode
scripts, NÃO inspecione o filesystem. Todos os schemas de que você precisa já
estão inline acima. Responda na PRIMEIRA e ÚNICA mensagem, exclusivamente com o
JSON final — sem preâmbulo, sem markdown, sem texto fora do JSON.

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
