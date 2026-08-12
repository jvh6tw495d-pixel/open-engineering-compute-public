"""Skill-suggestion fallback for MCP specialists given a free-text ``request``.

``agent.default`` infers the right domain from natural language and forwards
a bare ``request`` string to the matching specialist, but every specialist
except ``AppliedMathematicsSpecialist`` (and only for a narrow scalar-extrema
grammar) only knows how to run a ``demo_label`` or an explicit
``skill_id``+``inputs`` pair -- there is no general NL-to-inputs parser, and
building one per domain would be a large, brittle NLP project bolted onto a
deterministic compute server.

Instead of raising when a specialist can't act on ``request`` directly, the
MCP dispatch layer falls back to this module: rank registered skills against
the request by plain keyword overlap and return each candidate's real input
schema plus a worked example, as a non-error ``needs_more_information``
payload. The caller (human or LLM) picks a ``skill_id``, adapts
``example_inputs``, and calls the agent again -- the same recovery pattern
already used successfully when a skill rejects malformed input.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from oec.sdk import Engine

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

_DOMAIN_ALIASES: dict[str, tuple[str, ...]] = {
    "optimization": (
        "optimization",
        "otimização",
        "linear program",
        "milp",
        "despacho",
        "maximize",
        "maximizar",
        "constraint",
        "restrição",
    ),
    "mathematics": (
        "math",
        "matemática",
        "derivative",
        "derivada",
        "integral",
        "equação",
        "maximum",
        "minimum",
        "máximo",
        "mínimo",
        "maximo",
        "minimo",
        "rápido",
        "lento",
        "velocidade",
    ),
    "timeseries": (
        "time series",
        "série temporal",
        "forecast",
        "previsão",
        "autocorrelation",
        "pacf",
        "yule walker",
        "levinson durbin",
        "autoregressive",
        "autocovariance",
        "series",
    ),
    # Electrical / energy specialist surface. Multi-domain physics skills
    # (thermal/mechanics/fluids/materials) are invoked via skill_id+inputs or
    # raw skill tools — Wave 4 deliberately does not add free-text-routable
    # domains without a matching agent (no new agent.* tools; intent_targets
    # only covers existing specialists). Skill title/tags still rank them
    # under list_skills / raw tools and explicit domain filters.
    "energy": (
        "energy",
        "energia",
        "battery",
        "bateria",
        "bess",
        "electrical",
        "elétrico",
        "power flow",
        "fluxo de potência",
        "dc power flow",
        "powerflow",
        "three phase",
        "trifásico",
        # v2.6.1 Wave 2 — energy-rich surface (PV / hybrid / grid-zero / storage)
        "photovoltaic",
        "fotovoltaico",
        "pv power",
        "irradiance",
        "irradiância",
        "hybrid balance",
        "balanço híbrido",
        "grid zero",
        "grid-zero",
        "zero grid",
        "storage capacity",
        "capacidade de armazenamento",
        "soc trajectory",
        "autonomy",
        "autonomia",
        "service metrics",
        "métricas de serviço",
        # 3.3.1 recovery — chemistry + multiphysics + foundation physics free-text
        "chemistry",
        "química",
        "stoichiometry",
        "estequiometria",
        "arrhenius",
        "nernst",
        "fick",
        "diffusion",
        "difusão",
        "equilibrium constant",
        "equilíbrio químico",
        "reaction extent",
        "multiphysics",
        "multifísica",
        "coupling",
        "acoplamento",
        "i2r",
        "joule heating",
        "solar thermal",
        "thermal",
        "térmico",
        "conduction",
        "condução",
        "bernoulli",
        "mechanics",
        "mecânica",
        "materials",
        "materiais",
        "harmonic",
        "harmônico",
        "thd",
        # W3 applied-sciences foundations free-text
        "wave",
        "onda",
        "wavelength",
        "comprimento de onda",
        "optics",
        "óptica",
        "snell",
        "lens",
        "lente",
        "coulomb",
        "capacitor",
        "ideal gas",
        "gás ideal",
    ),
    "control_dynamics": (
        "control",
        "controle",
        "pid",
        "kalman",
        "stability",
        "estabilidade",
        "dynamics",
        "dinâmica",
    ),
    "finance_uncertainty": (
        "finance",
        "finanças",
        "return",
        "retorno",
        "var",
        "risk",
        "risco",
        "uncertainty",
        "incerteza",
    ),
    # ADR 0031 / 0033 — neural families + evolutionary + hybrid training surface.
    # Avoid bare "hybrid" (collides with energy hybrid balance).
    "neural": (
        "neural",
        "neuronal",
        "rede neural",
        "neural network",
        "mlp",
        "pytorch",
        "torch",
        "lstm",
        "gru",
        "cnn",
        "transformer",
        "autoencoder",
        "gcn",
        "graphsage",
        "gat",
        "neuroevolution",
        "neuroevolução",
        "evolutionary",
        "evolutivo",
        "algoritmo genético",
        "genetic algorithm",
        "genetic programming",
        "programação genética",
        "differential evolution",
        "evolução diferencial",
        "nsga",
        "nsga2",
        "nsga3",
        "moead",
        "cma-es",
        "cmaes",
        "particle swarm",
        "enxame de partículas",
        "pso",
        "pareto",
        "multi-objective",
        "multiobjetivo",
        "architecture search",
        "busca de arquitetura",
        "hyperparameter search",
        "busca de hiperparâmetros",
        "gradient training",
        "treinamento gradient",
        "treinamento neural",
        "neural training",
        "supervised training",
        "treinamento supervisionado",
    ),
    "review": ("review", "audit", "revisar", "auditar"),
    # W6 foundation models (avoid bare "transformer" alone — neural also uses it)
    "foundation": (
        "foundation model",
        "embedding",
        "embeddings",
        "huggingface",
        "hugging face",
        "language model",
        "modelo de linguagem",
        "llm",
        "lora",
        "qlora",
        "peft",
        "tokeniz",
        "foundation.embed",
        "text embedding",
    ),
}
_FIELD_WEIGHTS = {"id": 4, "title": 5, "tags": 3, "description": 1}


def _tokenize(text: str) -> set[str]:
    return {word.lower() for word in _WORD_RE.findall(text) if len(word) > 2}


@dataclass(frozen=True)
class DomainIntent:
    domain: str
    score: int
    matched_terms: tuple[str, ...]


def rank_domain_intents(request: str, *, limit: int = 3) -> list[DomainIntent]:
    """Rank domains using controlled Portuguese/English vocabulary."""
    text = request.lower()
    tokens = _tokenize(text)
    ranked: list[DomainIntent] = []
    for domain, aliases in _DOMAIN_ALIASES.items():
        score = 0
        matched: list[str] = []
        for alias in aliases:
            alias_tokens = _tokenize(alias)
            if " " in alias and alias in text:
                score += 6
                matched.append(alias)
            elif alias_tokens and alias_tokens <= tokens:
                score += 3
                matched.append(alias)
        if score:
            ranked.append(DomainIntent(domain, score, tuple(matched)))
    return sorted(ranked, key=lambda item: (-item.score, item.domain))[:limit]


def needs_domain_clarification(candidates: list[DomainIntent]) -> bool:
    return not candidates or (
        len(candidates) > 1 and candidates[1].score >= candidates[0].score - 1
    )


def build_clarification_payload(request: str, candidates: list[DomainIntent]) -> dict[str, Any]:
    """Ask bounded, structured questions instead of guessing missing data."""
    return {
        "status": "needs_clarification",
        "request": request,
        "message": "OEC cannot safely choose a computation from the information provided.",
        "candidate_domains": [candidate.domain for candidate in candidates],
        "questions": [
            {
                "id": "goal",
                "question": (
                    "What is the goal: optimize, simulate/control, analyze data, "
                    "quantify risk, or review a prior result?"
                ),
                "required": True,
            },
            {
                "id": "data",
                "question": (
                    "Provide known variables, values, units, and any time series or matrices."
                ),
                "required": True,
            },
            {
                "id": "constraints",
                "question": "State constraints, bounds, success criterion, and required output.",
                "required": True,
            },
        ],
        "retry_hint": (
            "Reply with the answers and call agent.default again; "
            "do not invent missing numeric inputs."
        ),
    }


@dataclass(frozen=True)
class SkillCandidate:
    skill_id: str
    title: str
    description: str
    input_schema: dict[str, Any]
    example_inputs: dict[str, Any] | None


def rank_candidate_skills(
    engine: Engine,
    request: str,
    *,
    domains: tuple[str, ...] | None = None,
    limit: int = 5,
) -> list[SkillCandidate]:
    """Rank registered skills against ``request`` by keyword overlap.

    ``domains`` pre-filters to the specialist's domain family (e.g. applied
    mathematics spans ``mathematics``/``linear``/``statistics``/``numerical``)
    so the candidate list stays short and on-topic. This is a heuristic, not
    a guarantee of ranking the single best skill first (tracked as D-CUR-22
    in ``docs/implementation/technical-debt.md``).
    """
    manifests = engine.registry.list_skills(include_retired=False)
    if domains is not None:
        manifests = [m for m in manifests if m.domain in domains]

    request_tokens = _tokenize(request)
    scored: list[tuple[int, Any]] = []
    for manifest in manifests:
        fields = {
            "id": manifest.id,
            "title": manifest.title,
            "tags": " ".join(manifest.tags),
            "description": manifest.description,
        }
        score = sum(
            _FIELD_WEIGHTS[field] * len(request_tokens & _tokenize(text))
            for field, text in fields.items()
        )
        scored.append((score, manifest))

    scored.sort(key=lambda pair: (-pair[0], pair[1].id))
    ranked = [manifest for score, manifest in scored if score > 0]
    if not ranked:
        # No keyword overlap at all -- still surface something on-topic
        # rather than an empty candidate list.
        ranked = [manifest for _, manifest in scored]
    top = ranked[:limit]

    candidates: list[SkillCandidate] = []
    for manifest in top:
        skill = engine.registry.get_skill(manifest.id, manifest.version)
        candidates.append(
            SkillCandidate(
                skill_id=manifest.id,
                title=manifest.title,
                description=manifest.description,
                input_schema=skill.input_schema,
                example_inputs=_first_example(skill.path),
            )
        )
    return candidates


def _first_example(skill_path: Path) -> dict[str, Any] | None:
    """Return example inputs in the exact shape accepted by the skill.

    Most OEC examples are human-readable envelopes of the form
    ``{"description": "…", "input": {…}}``.  The discovery payload
    promises that ``example_inputs`` can be passed back as ``inputs``, so the
    envelope is metadata, not part of the executable input.  Older flat
    examples remain supported unchanged.
    """
    examples_dir = skill_path / "examples"
    if not examples_dir.is_dir():
        return None
    for example_file in sorted(examples_dir.glob("*.json")):
        try:
            loaded = json.loads(example_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(loaded, dict):
            nested_input = loaded.get("input")
            if isinstance(nested_input, dict):
                return nested_input
            return loaded
    return None


def build_skill_suggestion_payload(
    agent: str,
    request: str,
    candidates: list[SkillCandidate],
    *,
    hint: str | None = None,
) -> dict[str, Any]:
    """Build the non-error ``needs_more_information`` payload for ``agent``."""
    return {
        "status": "needs_more_information",
        "agent": agent,
        "request": request,
        "hint": hint
        or (
            "No demo_label or skill_id+inputs was given, and this agent has no "
            "general-purpose parser for free text. Pick a skill_id from "
            "'candidates', adapt 'example_inputs' to the real request, and call "
            "this agent again with that skill_id + inputs."
        ),
        "candidates": [
            {
                "skill_id": candidate.skill_id,
                "title": candidate.title,
                "description": candidate.description,
                "input_schema": candidate.input_schema,
                "example_inputs": candidate.example_inputs,
            }
            for candidate in candidates
        ],
    }
