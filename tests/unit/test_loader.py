from pathlib import Path

import pytest

from oec.errors import SkillEntrypointError, SkillFrontMatterError, SkillManifestError
from oec.skills.loader.loader import load_skill
from oec.testing import write_skill_dir


def test_loads_a_valid_skill_directory(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path)
    skill = load_skill(skill_dir)
    assert skill.manifest.id == "mathematics.identity"
    assert skill.manifest.version == "0.1.0"
    assert skill.front_matter.id == "mathematics.identity"
    assert skill.input_schema == {"type": "object"}
    assert skill.output_schema == {"type": "object"}
    assert skill.path == skill_dir


def test_loads_the_real_example_fixture_used_across_the_repo() -> None:
    fixture_path = Path("tests/fixtures/skills/mathematics/identity")
    skill = load_skill(fixture_path)
    assert skill.manifest.id == "mathematics.identity"
    assert skill.manifest.status.value == "experimental"


def test_missing_skill_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SkillManifestError):
        load_skill(tmp_path / "does-not-exist")


def test_missing_manifest_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path, skip_manifest=True)
    with pytest.raises(SkillManifestError):
        load_skill(skill_dir)


def test_malformed_manifest_yaml_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path, manifest_raw="id: [unclosed\n")
    with pytest.raises(SkillManifestError):
        load_skill(skill_dir)


def test_non_mapping_manifest_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path, manifest_raw="- just\n- a\n- list\n")
    with pytest.raises(SkillManifestError):
        load_skill(skill_dir)


def test_manifest_failing_pydantic_validation_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path, manifest_overrides={"id": "NotValid"})
    with pytest.raises(SkillManifestError):
        load_skill(skill_dir)


def test_missing_skill_md_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path, skip_front_matter=True)
    with pytest.raises(SkillFrontMatterError):
        load_skill(skill_dir)


def test_frontmatter_id_mismatch_with_manifest_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(
        tmp_path, front_matter_overrides={"id": "mathematics.something_else"}
    )
    with pytest.raises(SkillFrontMatterError) as exc_info:
        load_skill(skill_dir)
    assert "id" in exc_info.value.details["mismatches"]


def test_frontmatter_title_mismatch_with_manifest_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path, front_matter_overrides={"title": "Different Title"})
    with pytest.raises(SkillFrontMatterError) as exc_info:
        load_skill(skill_dir)
    assert "title" in exc_info.value.details["mismatches"]


def test_missing_entrypoint_file_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path, skip_entrypoint=True)
    with pytest.raises(SkillEntrypointError):
        load_skill(skill_dir)


def test_missing_input_schema_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path, skip_input_schema=True)
    with pytest.raises(SkillEntrypointError):
        load_skill(skill_dir)


def test_missing_output_schema_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path, skip_output_schema=True)
    with pytest.raises(SkillEntrypointError):
        load_skill(skill_dir)


def test_invalid_json_input_schema_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path, input_schema_raw="{not valid json")
    with pytest.raises(SkillEntrypointError):
        load_skill(skill_dir)


def test_non_object_input_schema_is_rejected(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path, input_schema_raw="[1, 2, 3]")
    with pytest.raises(SkillEntrypointError):
        load_skill(skill_dir)


def test_loader_never_imports_the_entrypoint_module(tmp_path: Path) -> None:
    """The loader must not execute a skill's Python code (plan section 4.7)."""
    skill_dir = write_skill_dir(tmp_path, skip_entrypoint=True)
    (skill_dir / "implementation.py").write_text("raise RuntimeError('should never run')\n")
    skill = load_skill(skill_dir)  # must not raise RuntimeError
    assert skill.manifest.id == "mathematics.identity"
