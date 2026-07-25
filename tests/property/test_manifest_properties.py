import re

from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from oec.skills.schemas.manifest import SkillManifest, SkillStatus

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

_LOWER_SEGMENT = st.from_regex(r"[a-z][a-z0-9_]{0,12}", fullmatch=True)
_VALID_ID = st.lists(_LOWER_SEGMENT, min_size=2, max_size=4).map(".".join)
_VALID_VERSION = st.tuples(
    st.integers(min_value=0, max_value=99),
    st.integers(min_value=0, max_value=99),
    st.integers(min_value=0, max_value=99),
).map(lambda t: f"{t[0]}.{t[1]}.{t[2]}")

_BASE_KWARGS = {
    "status": SkillStatus.EXPERIMENTAL,
    "domain": "mathematics",
    "title": "Property Fixture",
    "entrypoint": {"module": "implementation", "function": "execute"},
    "schemas": {"input": "input.schema.json", "output": "output.schema.json"},
    "method": {"id": "identity", "version": "1"},
}


@given(skill_id=_VALID_ID, version=_VALID_VERSION)
def test_any_dot_separated_lowercase_id_and_semver_version_is_accepted(
    skill_id: str, version: str
) -> None:
    manifest = SkillManifest(**_BASE_KWARGS, id=skill_id, version=version)
    assert manifest.id == skill_id
    assert manifest.version == version


@given(
    bad_id=st.text(min_size=1, max_size=20).filter(
        lambda s: "\x00" not in s and not _looks_like_a_valid_id(s)
    )
)
def test_any_id_without_the_domain_dot_name_shape_is_rejected(bad_id: str) -> None:
    try:
        SkillManifest(**_BASE_KWARGS, id=bad_id, version="0.1.0")
    except ValidationError:
        return
    raise AssertionError(f"expected {bad_id!r} to be rejected as an invalid skill id")


def _looks_like_a_valid_id(value: str) -> bool:
    return bool(_ID_PATTERN.match(value))


@given(
    bad_version=st.text(min_size=1, max_size=15).filter(
        lambda s: "\x00" not in s and not _looks_like_a_valid_version(s)
    )
)
def test_any_non_semver_version_is_rejected(bad_version: str) -> None:
    try:
        SkillManifest(**_BASE_KWARGS, id="mathematics.identity", version=bad_version)
    except ValidationError:
        return
    raise AssertionError(f"expected {bad_version!r} to be rejected as an invalid version")


def _looks_like_a_valid_version(value: str) -> bool:
    return bool(_VERSION_PATTERN.match(value))
