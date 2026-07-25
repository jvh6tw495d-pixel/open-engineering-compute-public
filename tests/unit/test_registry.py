from pathlib import Path

import pytest

from _skill_helpers import write_skill_dir
from oec.errors import SkillNotFoundError, SkillVersionConflictError
from oec.skills.registry.registry import SkillRegistry, discover_skill_dirs


def test_register_loads_and_indexes_a_skill(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path)
    registry = SkillRegistry()
    skill = registry.register(skill_dir)
    assert skill.manifest.id == "mathematics.identity"
    assert registry.get_skill("mathematics.identity") is skill


def test_registering_same_id_and_version_twice_conflicts(tmp_path: Path) -> None:
    skill_dir_a = write_skill_dir(tmp_path, name="a")
    skill_dir_b = write_skill_dir(tmp_path, name="b")
    registry = SkillRegistry()
    registry.register(skill_dir_a)
    with pytest.raises(SkillVersionConflictError) as exc_info:
        registry.register(skill_dir_b)
    assert exc_info.value.details["skill_id"] == "mathematics.identity"


def test_two_versions_of_the_same_skill_coexist(tmp_path: Path) -> None:
    write_skill_dir(
        tmp_path,
        name="v1",
        manifest_overrides={"version": "0.1.0"},
        front_matter_overrides={"version": "0.1.0"},
    )
    write_skill_dir(
        tmp_path,
        name="v2",
        manifest_overrides={"version": "0.2.0"},
        front_matter_overrides={"version": "0.2.0"},
    )
    registry = SkillRegistry()
    report = registry.register_all(tmp_path)
    assert len(report.loaded) == 2
    assert not report.failures
    assert registry.get_skill("mathematics.identity").manifest.version == "0.2.0"
    assert registry.get_skill("mathematics.identity", version="0.1.0").manifest.version == "0.1.0"


def test_get_skill_unknown_id_raises_not_found() -> None:
    registry = SkillRegistry()
    with pytest.raises(SkillNotFoundError):
        registry.get_skill("mathematics.does_not_exist")


def test_get_skill_unknown_version_raises_not_found(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path)
    registry = SkillRegistry()
    registry.register(skill_dir)
    with pytest.raises(SkillNotFoundError):
        registry.get_skill("mathematics.identity", version="9.9.9")


def test_retired_skill_excluded_from_list_and_default_resolution(tmp_path: Path) -> None:
    write_skill_dir(
        tmp_path,
        manifest_overrides={"status": "retired"},
        front_matter_overrides={"status": "retired"},
    )
    registry = SkillRegistry()
    registry.register_all(tmp_path)

    assert registry.list_skills() == []
    assert registry.list_skills(include_retired=True)[0].id == "mathematics.identity"
    with pytest.raises(SkillNotFoundError):
        registry.get_skill("mathematics.identity")
    # explicit version still resolves a retired skill
    skill = registry.get_skill("mathematics.identity", version="0.1.0")
    assert skill.manifest.status.value == "retired"


def test_list_skills_is_sorted_by_id_then_version(tmp_path: Path) -> None:
    write_skill_dir(
        tmp_path,
        name="b",
        manifest_overrides={"id": "mathematics.beta", "title": "Beta"},
        front_matter_overrides={"id": "mathematics.beta", "title": "Beta"},
    )
    write_skill_dir(
        tmp_path,
        name="a",
        manifest_overrides={"id": "mathematics.alpha", "title": "Alpha"},
        front_matter_overrides={"id": "mathematics.alpha", "title": "Alpha"},
    )
    registry = SkillRegistry()
    registry.register_all(tmp_path)
    ids = [manifest.id for manifest in registry.list_skills()]
    assert ids == ["mathematics.alpha", "mathematics.beta"]


def test_search_filters_by_domain_and_tags(tmp_path: Path) -> None:
    write_skill_dir(
        tmp_path,
        name="a",
        manifest_overrides={"id": "electrical.foo", "domain": "electrical", "tags": ["mvp"]},
        front_matter_overrides={"id": "electrical.foo", "domain": "electrical"},
    )
    write_skill_dir(
        tmp_path,
        name="b",
        manifest_overrides={"id": "mathematics.bar", "domain": "mathematics", "tags": []},
        front_matter_overrides={"id": "mathematics.bar", "domain": "mathematics"},
    )
    registry = SkillRegistry()
    registry.register_all(tmp_path)

    assert [m.id for m in registry.search(domain="electrical")] == ["electrical.foo"]
    assert [m.id for m in registry.search(tags=["mvp"])] == ["electrical.foo"]
    assert registry.search(domain="mathematics", tags=["mvp"]) == []


def test_validate_returns_manifest_for_a_registered_skill(tmp_path: Path) -> None:
    skill_dir = write_skill_dir(tmp_path)
    registry = SkillRegistry()
    registry.register(skill_dir)
    manifest = registry.validate("mathematics.identity")
    assert manifest.id == "mathematics.identity"


def test_validate_raises_for_unregistered_skill() -> None:
    registry = SkillRegistry()
    with pytest.raises(SkillNotFoundError):
        registry.validate("mathematics.does_not_exist")


def test_register_all_collects_failures_without_stopping_discovery(tmp_path: Path) -> None:
    write_skill_dir(tmp_path, name="valid")
    write_skill_dir(
        tmp_path,
        name="broken",
        manifest_overrides={"id": "mathematics.broken_id_INVALID"},
        front_matter_overrides={"id": "mathematics.broken_id_INVALID"},
    )
    registry = SkillRegistry()
    report = registry.register_all(tmp_path)
    assert len(report.loaded) == 1
    assert len(report.failures) == 1
    assert registry.get_skill("mathematics.identity") is not None


def test_discover_skill_dirs_on_missing_root_returns_empty(tmp_path: Path) -> None:
    assert discover_skill_dirs(tmp_path / "does-not-exist") == []


def test_discover_skill_dirs_finds_nested_skill_yaml_files(tmp_path: Path) -> None:
    write_skill_dir(tmp_path, name="mathematics/identity")
    write_skill_dir(tmp_path, name="electrical/voltage_drop")
    dirs = discover_skill_dirs(tmp_path)
    assert len(dirs) == 2
