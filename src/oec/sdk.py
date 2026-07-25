"""The public ``oec`` Python SDK: run a registered skill without touching
``SkillRegistry``/``ExecutionService``/validator wiring directly (ADR 0014).

This is the "import direto em Python" surface deferred from Sprint 03
(``docs/sprints/sprint-03-execution-validation.md``) — distinct from
:mod:`oec.testing`, which stays a test-authoring helper
(``load_skill_module``, ``write_skill_dir``), not a runtime execution
facade. :class:`Engine` is what ``oec run`` (the CLI) is built on top
of, and what a script/notebook/service embedding OEC should use instead
of the lower-level pieces this module wraps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oec.execution.factory import build_validators
from oec.execution.models import ExecutionRequest, ExecutionResult
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry


class Engine:
    """Discovers skills under ``skills_root`` once, then runs any of them.

    ``ExecutionService`` binds one validator list for its whole lifetime
    (Sprint 03 design, unchanged by this SDK) — appropriate for a caller
    that repeatedly executes one known skill, wrong for something that
    must run *any* registered skill. ``Engine`` owns one
    ``ExecutionService`` per ``(skill_id, resolved_version)``, built
    lazily via :func:`~oec.execution.factory.build_validators` the first
    time that skill is run and cached after that — the registry scan and
    validator discovery both happen at most once per skill per
    ``Engine`` instance, not once per call.
    """

    def __init__(self, skills_root: str | Path = "skills") -> None:
        self._registry = SkillRegistry()
        report = self._registry.register_all(Path(skills_root))
        # A broken skill directory (e.g. one under active development)
        # does not stop every other skill from running -- mirrors the CLI's
        # existing `skills list`/`inspect` behavior, which also tolerates
        # individual registration failures rather than refusing to start.
        # A caller who wants to know what failed can inspect this list;
        # attempting to *run* one of the failed skills still raises, via
        # SkillRegistry.get_skill's own SkillNotFoundError.
        self.registration_failures = report.failures
        self._services: dict[tuple[str, str], ExecutionService] = {}

    def run(
        self,
        skill_id: str,
        inputs: dict[str, Any],
        *,
        skill_version: str | None = None,
        seed: int | None = None,
        trace_id: str | None = None,
        requested_by: str | None = None,
    ) -> ExecutionResult:
        """Execute ``skill_id`` with ``inputs`` and return the full result.

        Raises whatever :meth:`~oec.skills.registry.registry.SkillRegistry.get_skill`
        raises (e.g. :class:`~oec.errors.SkillNotFoundError`) if the
        skill or version can't be resolved.
        """
        skill = self._registry.get_skill(skill_id, skill_version)
        cache_key = (skill.manifest.id, skill.manifest.version)
        service = self._services.get(cache_key)
        if service is None:
            input_validators, result_validators = build_validators(skill)
            service = ExecutionService(
                self._registry,
                input_validators=input_validators,
                result_validators=result_validators,
            )
            self._services[cache_key] = service

        request_kwargs: dict[str, Any] = {
            "skill_id": skill.manifest.id,
            "skill_version": skill.manifest.version,
            "inputs": inputs,
        }
        if seed is not None:
            request_kwargs["seed"] = seed
        if trace_id is not None:
            request_kwargs["trace_id"] = trace_id
        if requested_by is not None:
            request_kwargs["requested_by"] = requested_by

        return service.execute(ExecutionRequest(**request_kwargs))


def run(
    skill_id: str,
    inputs: dict[str, Any],
    *,
    skills_root: str | Path = "skills",
    skill_version: str | None = None,
    seed: int | None = None,
    trace_id: str | None = None,
    requested_by: str | None = None,
) -> ExecutionResult:
    """One-shot convenience: build a throwaway :class:`Engine` and run one skill.

    For running more than one skill, or the same skill repeatedly,
    construct an :class:`Engine` directly instead — this function
    re-scans ``skills_root`` and rebuilds validators on every call.
    """
    engine = Engine(skills_root=skills_root)
    return engine.run(
        skill_id,
        inputs,
        skill_version=skill_version,
        seed=seed,
        trace_id=trace_id,
        requested_by=requested_by,
    )
