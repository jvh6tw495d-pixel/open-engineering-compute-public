"""Pre/post verification checks (v2.4, ADR 0021).

Two plain functions, called directly from ``ExecutionService.execute`` the
same way ``compute_status``/``build_provenance`` already are — not an
injected ``InputValidator``/``ResultValidator`` — because this is a
cross-cutting, always-on aggregation over data the service already has in
hand, not a per-skill pluggable layer.

Both functions mostly *aggregate* signals the existing validator layers
already compute (schema/dimensional/mathematical/physical outcomes for
pre-checks; the ``numerical`` layer's outcomes and ``diagnostics`` for
post-checks) rather than re-implementing them, plus one genuinely new
pass/fail check: ``backend_fit``. This is an honest v0, not a claim of
"full formal verification" without both pre and post structure.

``lp_gap_report`` is deliberately *not* a pass/fail check, even though it
lives in the post-check list: HiGHS's MIP gap has no OEC-configured target
tolerance to assert against, and adding one without a documented,
defensible source would be exactly the kind of fabricated number this
codebase's gates exist to catch. Its ``passed`` is always ``None`` --
reported, not evaluated -- and it is only emitted when a gap was actually
returned, rather than padding the list with an always-passing placeholder.
``provenance_integrity`` (renamed from an earlier "reproducibility") *is*
a real, narrow pass/fail check -- has ``build_provenance`` set an
``input_hash`` -- not a claim that anything was re-run and compared.
"""

from __future__ import annotations

from typing import Any

from oec.backends.fallback import check_backend_availability
from oec.skills.loader.models import LoadedSkill
from oec.validation.base import Severity, ValidationOutcome
from oec.verification.report import PostVerificationCheck, PreVerificationCheck

_PRE_INPUT_LAYERS = frozenset({"schema", "dimensional", "mathematical", "physical"})


def run_pre_verification(
    skill: LoadedSkill, outcomes: list[ValidationOutcome]
) -> list[PreVerificationCheck]:
    """Return the pre-execution :class:`PreVerificationCheck` list for ``skill``."""
    input_errors = [
        outcome
        for outcome in outcomes
        if outcome.layer in _PRE_INPUT_LAYERS and outcome.severity is Severity.ERROR
    ]
    checks = [
        PreVerificationCheck(
            name="input_validation",
            passed=not input_errors,
            message=None if not input_errors else "; ".join(_all_messages(input_errors)),
            details={"failing_layers": sorted({o.layer for o in input_errors})},
        )
    ]

    backend_outcomes = check_backend_availability(skill.manifest.method.id)
    checks.append(
        PreVerificationCheck(
            name="backend_fit",
            passed=not backend_outcomes,
            message=None if not backend_outcomes else "; ".join(_all_messages(backend_outcomes)),
            details={"method_id": skill.manifest.method.id},
        )
    )
    return checks


def run_post_verification(
    skill: LoadedSkill,
    result: dict[str, Any],
    diagnostics: dict[str, Any],
    outcomes: list[ValidationOutcome],
    provenance: dict[str, Any],
) -> list[PostVerificationCheck]:
    """Return the post-execution :class:`PostVerificationCheck` list for ``skill``."""
    checks: list[PostVerificationCheck] = []

    if skill.manifest.method.iterative:
        converged = diagnostics.get("converged")
        checks.append(
            PostVerificationCheck(
                name="convergence",
                passed=converged is not False,
                message=None if converged is not False else "method did not converge",
                details={"converged": converged},
            )
        )

    numerical_warnings = [
        outcome
        for outcome in outcomes
        if outcome.layer == "numerical" and outcome.severity is not Severity.OK
    ]
    numerical_messages = _all_messages(numerical_warnings)
    checks.append(
        PostVerificationCheck(
            name="residuals_and_conditioning",
            passed=not numerical_warnings,
            message=None if not numerical_messages else "; ".join(numerical_messages),
            details={},
        )
    )

    mip_gap = result.get("mip_gap")
    if mip_gap is not None:
        # Reported, not evaluated: HiGHS has no OEC-configured target gap
        # tolerance to assert against (see module docstring).
        checks.append(
            PostVerificationCheck(
                name="lp_gap_report",
                passed=None,
                details={"mip_gap": mip_gap},
            )
        )

    # A real, if narrow, pass/fail check: build_provenance always sets
    # input_hash today, so this should never actually fail -- unlike
    # lp_gap_report above, it has a well-defined true/false criterion
    # (unlike "reproducibility," it does not claim anything was re-run).
    input_hash = provenance.get("input_hash")
    checks.append(
        PostVerificationCheck(
            name="provenance_integrity",
            passed=bool(input_hash),
            message=None if input_hash else "provenance is missing input_hash",
            details={"input_hash": input_hash},
        )
    )
    return checks


def _all_messages(outcomes: list[ValidationOutcome]) -> list[str]:
    return [message for outcome in outcomes for message in outcome.messages]
