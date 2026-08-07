from pathlib import Path

import pytest

from oec.errors import SkillEntrypointError
from oec.testing import load_skill_module


def test_load_skill_module_imports_the_file(tmp_path: Path) -> None:
    (tmp_path / "implementation.py").write_text("VALUE = 42\n", encoding="utf-8")
    module = load_skill_module(tmp_path, "implementation")
    assert module.VALUE == 42


def test_missing_module_raises_skill_entrypoint_error(tmp_path: Path) -> None:
    with pytest.raises(SkillEntrypointError):
        load_skill_module(tmp_path, "does_not_exist")


def test_two_skills_with_same_module_name_dont_collide(tmp_path: Path) -> None:
    skill_a = tmp_path / "a"
    skill_b = tmp_path / "b"
    skill_a.mkdir()
    skill_b.mkdir()
    (skill_a / "implementation.py").write_text("VALUE = 'a'\n", encoding="utf-8")
    (skill_b / "implementation.py").write_text("VALUE = 'b'\n", encoding="utf-8")

    module_a = load_skill_module(skill_a, "implementation")
    module_b = load_skill_module(skill_b, "implementation")

    assert module_a.VALUE == "a"
    assert module_b.VALUE == "b"
