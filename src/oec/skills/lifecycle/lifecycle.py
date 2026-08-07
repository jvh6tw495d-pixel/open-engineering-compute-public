"""Lifecycle rules for skill status transitions (plan section 8.3).

- ``experimental``: may change without preserving backwards compatibility.
- ``validated``: golden cases and technical review approved.
- ``stable``: public contract, must stay backwards compatible.
- ``deprecated``: available, but a replacement is indicated.
- ``retired``: not loaded by default.

This module only encodes the ordering and the transition rule; it does not
persist history, changelogs, or migrations — those are out of scope until a
component actually needs to change a skill's status at runtime.
"""

from __future__ import annotations

from oec.errors import OECValidationError
from oec.skills.schemas.manifest import SkillStatus

_ORDER: tuple[SkillStatus, ...] = (
    SkillStatus.EXPERIMENTAL,
    SkillStatus.VALIDATED,
    SkillStatus.STABLE,
    SkillStatus.DEPRECATED,
    SkillStatus.RETIRED,
)
_RANK: dict[SkillStatus, int] = {status: index for index, status in enumerate(_ORDER)}


def is_loadable_by_default(status: SkillStatus) -> bool:
    """Whether a skill in this status is included in the registry by default.

    Only ``retired`` skills are excluded (plan section 8.3: "retired: não
    carregada por padrão").
    """
    return status is not SkillStatus.RETIRED


def validate_transition(current: SkillStatus, new: SkillStatus) -> None:
    """Raise if moving a skill from ``current`` to ``new`` status is illegal.

    Only forward-or-equal moves along the lifecycle order are allowed
    (e.g. ``experimental`` -> ``stable`` or ``stable`` -> ``stable`` for a
    same-status version bump). Moving backwards — e.g. ``stable`` ->
    ``experimental`` — would silently break the compatibility guarantee
    the earlier status implied, so it is rejected.
    """
    if _RANK[new] < _RANK[current]:
        raise OECValidationError(
            f"illegal lifecycle transition: {current.value!r} -> {new.value!r} "
            "(status cannot move backwards)",
            code="skill_lifecycle_regression",
            details={"current": current.value, "new": new.value},
        )
