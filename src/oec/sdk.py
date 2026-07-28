"""The public ``oec`` Python SDK: run a registered skill without touching
``SkillRegistry``/``ExecutionService``/validator wiring directly (ADR 0014).

This is the "import direto em Python" surface deferred from Sprint 03
(``docs/sprints/sprint-03-execution-validation.md``) — distinct from
:mod:`oec.testing`, which stays a test-authoring helper
(``load_skill_module``, ``write_skill_dir``), not a runtime execution
facade. :class:`Engine` is what ``oec run`` (the CLI), the REST API, and
the MCP server are all built on top of.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from oec.core.scientific_result import ScientificResult, from_execution_result
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

    :meth:`run` serializes every execution through a single lock (ADR
    0015): with zero OS-level resource isolation per skill subprocess
    (ADR 0012), the only safe concurrency bound for the Alpha is
    "one skill executes at a time," matching the plan's own
    synchronous execution model — and it incidentally makes the
    ``_services`` cache safe under concurrent callers (the REST API,
    the MCP server) without a separate lock for that.
    """

    def __init__(self, skills_root: str | Path = "skills") -> None:
        self.skills_root = Path(skills_root)
        self.registry = SkillRegistry()
        report = self.registry.register_all(self.skills_root)
        # A broken skill directory (e.g. one under active development)
        # does not stop every other skill from running -- mirrors the CLI's
        # existing `skills list`/`inspect` behavior, which also tolerates
        # individual registration failures rather than refusing to start.
        # A caller who wants to know what failed can inspect this list;
        # attempting to *run* one of the failed skills still raises, via
        # SkillRegistry.get_skill's own SkillNotFoundError.
        self.registration_failures = report.failures
        self._services: dict[tuple[str, str], ExecutionService] = {}
        self._lock = threading.Lock()

    def warm(self) -> None:
        """Eagerly build every registered skill's ``ExecutionService``.

        Optional for a short-lived caller (``oec run`` executes one
        skill and exits — there is nothing to warm ahead of that);
        required for a long-lived one (REST/MCP, ADR 0015) so a skill's
        validator-discovery failure (:class:`~oec.errors.SkillEntrypointError`,
        ADR 0014 — e.g. an ambiguous or missing ``validation.py``
        validator) surfaces at server startup, not on that skill's
        first request.
        """
        with self._lock:
            for manifest in self.registry.list_skills(include_retired=True):
                self._get_or_build_service_locked(manifest.id, manifest.version)

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
        skill or version can't be resolved. Blocks until any other
        execution already in progress on this ``Engine`` finishes (see
        the class docstring and ADR 0015) — safe but not fast under
        concurrent callers, an explicit Alpha-stage tradeoff.
        """
        with self._lock:
            skill = self.registry.get_skill(skill_id, skill_version)
            service = self._get_or_build_service_locked(skill.manifest.id, skill.manifest.version)

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

    def run_scientific(
        self,
        skill_id: str,
        inputs: dict[str, Any],
        *,
        skill_version: str | None = None,
        seed: int | None = None,
        trace_id: str | None = None,
        requested_by: str | None = None,
    ) -> ScientificResult:
        """Run a skill and return :class:`~oec.core.ScientificResult` (ADR 0019).

        Does not change :meth:`run` / ``ExecutionResult`` contracts.
        """
        return from_execution_result(
            self.run(
                skill_id,
                inputs,
                skill_version=skill_version,
                seed=seed,
                trace_id=trace_id,
                requested_by=requested_by,
            )
        )

    def _get_or_build_service_locked(self, skill_id: str, skill_version: str) -> ExecutionService:
        """Must only be called while holding ``self._lock``."""
        cache_key = (skill_id, skill_version)
        service = self._services.get(cache_key)
        if service is None:
            skill = self.registry.get_skill(skill_id, skill_version)
            input_validators, result_validators = build_validators(skill)
            service = ExecutionService(
                self.registry,
                input_validators=input_validators,
                result_validators=result_validators,
            )
            self._services[cache_key] = service
        return service


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
