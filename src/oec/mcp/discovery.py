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


def _tokenize(text: str) -> set[str]:
    return {word.lower() for word in _WORD_RE.findall(text) if len(word) > 2}


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
        haystack = _tokenize(
            f"{manifest.title} {manifest.description} {manifest.id} {' '.join(manifest.tags)}"
        )
        scored.append((len(request_tokens & haystack), manifest))

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
