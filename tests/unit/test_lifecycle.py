import pytest

from oec.errors import OECValidationError
from oec.skills.lifecycle.lifecycle import is_loadable_by_default, validate_transition
from oec.skills.schemas.manifest import SkillStatus


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (SkillStatus.EXPERIMENTAL, True),
        (SkillStatus.VALIDATED, True),
        (SkillStatus.STABLE, True),
        (SkillStatus.DEPRECATED, True),
        (SkillStatus.RETIRED, False),
    ],
)
def test_is_loadable_by_default(status: SkillStatus, expected: bool) -> None:
    assert is_loadable_by_default(status) is expected


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (SkillStatus.EXPERIMENTAL, SkillStatus.EXPERIMENTAL),
        (SkillStatus.EXPERIMENTAL, SkillStatus.VALIDATED),
        (SkillStatus.EXPERIMENTAL, SkillStatus.STABLE),
        (SkillStatus.EXPERIMENTAL, SkillStatus.RETIRED),
        (SkillStatus.STABLE, SkillStatus.STABLE),
        (SkillStatus.STABLE, SkillStatus.DEPRECATED),
        (SkillStatus.DEPRECATED, SkillStatus.RETIRED),
    ],
)
def test_forward_and_same_status_transitions_are_legal(
    current: SkillStatus, new: SkillStatus
) -> None:
    validate_transition(current, new)  # must not raise


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (SkillStatus.STABLE, SkillStatus.EXPERIMENTAL),
        (SkillStatus.VALIDATED, SkillStatus.EXPERIMENTAL),
        (SkillStatus.DEPRECATED, SkillStatus.STABLE),
        (SkillStatus.RETIRED, SkillStatus.STABLE),
    ],
)
def test_backward_transitions_are_rejected(current: SkillStatus, new: SkillStatus) -> None:
    with pytest.raises(OECValidationError) as exc_info:
        validate_transition(current, new)
    assert exc_info.value.code == "skill_lifecycle_regression"
    assert exc_info.value.details == {"current": current.value, "new": new.value}
