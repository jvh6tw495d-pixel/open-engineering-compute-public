import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.skills.registry.registry import SkillRegistry
from oec.testing import write_skill_dir

_VERSION_TUPLES = st.lists(
    st.tuples(
        st.integers(min_value=0, max_value=9),
        st.integers(min_value=0, max_value=9),
        st.integers(min_value=0, max_value=9),
    ),
    min_size=1,
    max_size=6,
    unique=True,
)


@settings(deadline=None)
@given(version_tuples=_VERSION_TUPLES)
def test_get_skill_without_version_always_resolves_the_highest_registered_version(
    version_tuples: list[tuple[int, int, int]],
) -> None:
    # A fresh directory per Hypothesis example: pytest's tmp_path fixture is
    # only instantiated once per test *call*, not once per @given example,
    # so reusing it here would leak skill dirs from earlier examples.
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        registry = SkillRegistry()
        versions = [f"{major}.{minor}.{patch}" for major, minor, patch in version_tuples]

        for index, version in enumerate(versions):
            write_skill_dir(
                root,
                name=f"v{index}",
                manifest_overrides={"version": version},
                front_matter_overrides={"version": version},
            )

        report = registry.register_all(root)
        assert not report.failures

        resolved = registry.get_skill("mathematics.identity")
        expected_max = max(version_tuples)
        want = f"{expected_max[0]}.{expected_max[1]}.{expected_max[2]}"
        assert resolved.manifest.version == want
