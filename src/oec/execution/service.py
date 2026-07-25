"""The Skill Execution Service: resolve -> validate -> execute -> validate -> status.

Pipeline (plan section 10.4)::

    ExecutionRequest
       -> resolve skill (SkillRegistry)
       -> run input validators (schema/dimensional/mathematical/physical)
       -> execute in sandbox (ADR 0012) if no input validator reported an error
       -> run result validators (numerical/invariants)
       -> enforce the convergence-declaration contract (ADR 0013)
       -> compute_status (ADR 0007)
       -> build provenance
       -> ExecutionResult

Validators are injected, not imported here — this module only depends on
the frozen ``InputValidator``/``ResultValidator`` protocols
(``oec.validation.base``), never on any concrete validator layer. That
is what let this module and the concrete validator layers be built in
parallel in Sprint 03 (see ``docs/sprints/sprint-03-*.md``).

A validator that raises is not trusted to have made a judgment — its
exception becomes an ERROR-severity outcome (fail closed) rather than
crashing the whole execution (found in the Sprint 03 review: a single
buggy validator used to take the entire service down instead of
producing a classified ``INVALID``/``FAILED`` result).

Input normalization is currently a passthrough: no real skill yet
declares ``QuantityValue``-shaped inputs. Wiring
``oec.kernel.units.normalize`` into this step is deferred until a real
skill's input schema needs it — see ``docs/development/codebase-map.md``.
"""

from __future__ import annotations

import time
import traceback
from datetime import UTC, datetime
from typing import Any

from oec.common import VersionedRef
from oec.execution.models import ExecutionRequest, ExecutionResult
from oec.execution.provenance import SandboxReport, build_provenance
from oec.execution.sandbox import run_in_sandbox
from oec.execution.status import compute_status
from oec.skills.loader.models import LoadedSkill
from oec.skills.registry.registry import SkillRegistry
from oec.validation.base import InputValidator, ResultValidator, Severity, ValidationOutcome

_CONVERGENCE_CONTRACT_MESSAGE = (
    "method.iterative=true but the implementation did not report "
    "diagnostics['converged'] -- an iterative method must state whether it "
    "converged; omission is not the same as 'exact, no convergence concept'"
)


class ExecutionService:
    """Executes skills against a given :class:`SkillRegistry`."""

    def __init__(
        self,
        registry: SkillRegistry,
        *,
        input_validators: list[InputValidator] | None = None,
        result_validators: list[ResultValidator] | None = None,
    ) -> None:
        self._registry = registry
        self._input_validators = input_validators or []
        self._result_validators = result_validators or []

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute ``request`` and return a structured, auditable result.

        Raises whatever :meth:`SkillRegistry.get_skill` raises (e.g.
        :class:`~oec.errors.SkillNotFoundError`) if the skill cannot be
        resolved -- there is no meaningful ``ExecutionResult`` to build
        without a resolved skill and method to reference.
        """
        started_at = datetime.now(UTC)
        start = time.monotonic()

        skill = self._registry.get_skill(request.skill_id, request.skill_version)
        normalized_inputs = dict(request.inputs)

        outcomes = self._run_input_validators(skill, normalized_inputs)

        implementation_failed = False
        result: dict[str, Any] = {}
        diagnostics: dict[str, Any] = {}
        converged: bool | None = None

        if not any(outcome.severity is Severity.ERROR for outcome in outcomes):
            sandbox_result = run_in_sandbox(
                skill_path=skill.path,
                module=skill.manifest.entrypoint.module,
                function=skill.manifest.entrypoint.function,
                inputs=normalized_inputs,
                timeout_seconds=skill.manifest.execution.timeout_seconds,
            )
            if sandbox_result.failed:
                implementation_failed = True
                diagnostics = {
                    "error_output": sandbox_result.error_output,
                    "timed_out": sandbox_result.timed_out,
                }
            else:
                result = sandbox_result.result
                diagnostics = sandbox_result.diagnostics
                outcomes.extend(
                    self._run_result_validators(skill, normalized_inputs, result, diagnostics)
                )

                if skill.manifest.method.iterative:
                    if "converged" not in diagnostics:
                        implementation_failed = True
                        diagnostics = {
                            **diagnostics,
                            "error_output": _CONVERGENCE_CONTRACT_MESSAGE,
                            "timed_out": False,
                        }
                    else:
                        converged = bool(diagnostics["converged"])

        status = compute_status(
            outcomes,
            implementation_failed=implementation_failed,
            converged=None if implementation_failed else converged,
        )

        completed_at = datetime.now(UTC)
        duration_ms = (time.monotonic() - start) * 1000

        provenance = build_provenance(
            trace_id=request.trace_id,
            requested_by=request.requested_by,
            seed=request.seed,
            sandbox=SandboxReport(
                timeout_enforced=True,
                network_isolation_enforced=False,
                filesystem_isolation_enforced=False,
                memory_limit_enforced=False,
            ),
        )

        warnings = [
            message
            for outcome in outcomes
            if outcome.severity is Severity.WARNING
            for message in outcome.messages
        ]

        return ExecutionResult(
            status=status,
            skill=VersionedRef(id=skill.manifest.id, version=skill.manifest.version),
            method=VersionedRef(id=skill.manifest.method.id, version=skill.manifest.method.version),
            inputs=request.inputs,
            normalized_inputs=normalized_inputs,
            result=result,
            diagnostics=diagnostics,
            validation={"outcomes": [outcome.model_dump(mode="json") for outcome in outcomes]},
            warnings=warnings,
            provenance=provenance,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )

    def _run_input_validators(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        outcomes: list[ValidationOutcome] = []
        for validator in self._input_validators:
            try:
                outcomes.extend(validator.validate(skill, normalized_inputs))
            except Exception as exc:  # noqa: BLE001 -- a crashing validator must not crash the service
                outcomes.append(_validator_crash_outcome(validator, exc))
        return outcomes

    def _run_result_validators(
        self,
        skill: LoadedSkill,
        normalized_inputs: dict[str, Any],
        result: dict[str, Any],
        diagnostics: dict[str, Any],
    ) -> list[ValidationOutcome]:
        outcomes: list[ValidationOutcome] = []
        for result_validator in self._result_validators:
            try:
                outcomes.extend(
                    result_validator.validate(skill, normalized_inputs, result, diagnostics)
                )
            except Exception as exc:  # noqa: BLE001 -- a crashing validator must not crash the service
                outcomes.append(_validator_crash_outcome(result_validator, exc))
        return outcomes


def _validator_crash_outcome(validator: object, exc: Exception) -> ValidationOutcome:
    layer = getattr(validator, "layer", type(validator).__name__)
    return ValidationOutcome(
        layer=str(layer),
        severity=Severity.ERROR,
        messages=[f"validator {type(validator).__name__} raised {type(exc).__name__}: {exc}"],
        details={"traceback": traceback.format_exc()},
    )
