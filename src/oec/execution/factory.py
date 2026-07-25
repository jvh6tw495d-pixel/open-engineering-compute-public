"""Assembles a skill's validators from its manifest (ADR 0014).

Every ``tests/integration/test_*_end_to_end.py`` since Sprint 04 has
hand-built an ``ExecutionService`` with a hardcoded
``[SchemaValidator(), <SkillSpecificValidator>()]`` — the caller had to
already know, out of band, which validator class a given skill needs.
:func:`build_validators` is what a CLI/SDK that must run *any*
registered skill uses instead: reads ``skill.manifest.validation``
(``ValidationPolicy``) and assembles the right list, discovering the
skill's own ``validation.py`` validator by introspection rather than
requiring an explicit registration point.
"""

from __future__ import annotations

import inspect
from typing import cast

from oec.errors import SkillEntrypointError
from oec.skills.loader.models import LoadedSkill
from oec.testing import load_skill_module
from oec.validation.base import InputValidator, ResultValidator
from oec.validation.dimensions import DimensionalValidator
from oec.validation.invariants import InvariantValidator
from oec.validation.numerical import NumericalDiagnosticsValidator
from oec.validation.schema import SchemaValidator


def build_validators(
    skill: LoadedSkill,
) -> tuple[list[InputValidator], list[ResultValidator]]:
    """Build the input/result validator lists ``skill.manifest.validation`` declares.

    ``InvariantValidator`` is always included among the result
    validators regardless of policy — it is a structural guarantee (no
    NaN/Inf, output-schema shape), not an opt-out layer. ``physical:
    true`` wires nothing here by design (ADR 0014): physical checks are
    expected inside the skill's own ``validation.py``, the same way
    ``mathematical: true`` checks reuse ``oec.validation.mathematical``'s
    helpers.
    """
    policy = skill.manifest.validation

    input_validators: list[InputValidator] = []
    if policy.schema_layer:
        input_validators.append(SchemaValidator())
    if policy.dimensional:
        input_validators.append(DimensionalValidator())
    if policy.mathematical:
        input_validators.append(_discover_skill_validator(skill))

    result_validators: list[ResultValidator] = [InvariantValidator()]
    if policy.numerical:
        result_validators.append(NumericalDiagnosticsValidator())

    return input_validators, result_validators


def _discover_skill_validator(skill: LoadedSkill) -> InputValidator:
    """Find the one class in ``skill``'s ``validation.py`` shaped like an ``InputValidator``.

    Scans the module for a class that is defined in it (not merely
    imported into it -- filters out things like ``LoadedSkill`` or
    ``ExpressionError`` that every skill's ``validation.py`` imports)
    and declares both a ``layer`` attribute and a callable ``validate``
    -- duck-typed, since ``oec.validation.base``'s protocols aren't
    ``@runtime_checkable``. Raises :class:`~oec.errors.SkillEntrypointError`
    if none or more than one such class is found, so a missing/ambiguous
    validator is a loud failure, not a silently-skipped layer.
    """
    module = load_skill_module(skill.path, "validation")

    candidates = [
        obj
        for obj in vars(module).values()
        if inspect.isclass(obj)
        and obj.__module__ == module.__name__
        and hasattr(obj, "layer")
        and callable(getattr(obj, "validate", None))
    ]

    if not candidates:
        raise SkillEntrypointError(
            f"skill {skill.manifest.id!r} declares validation.mathematical=true "
            f"but no InputValidator-shaped class was found in {skill.path / 'validation.py'}",
            details={"skill_id": skill.manifest.id, "path": str(skill.path)},
        )
    if len(candidates) > 1:
        raise SkillEntrypointError(
            f"skill {skill.manifest.id!r}'s validation.py has {len(candidates)} "
            "InputValidator-shaped classes; exactly one is required for auto-discovery",
            details={
                "skill_id": skill.manifest.id,
                "candidates": [c.__name__ for c in candidates],
            },
        )
    return cast(InputValidator, candidates[0]())
