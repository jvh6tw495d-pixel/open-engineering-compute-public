from pathlib import Path

from typer.testing import CliRunner

from _skill_helpers import write_skill_dir
from oec import __version__
from oec.cli.main import app

runner = CliRunner()


def test_version_command_prints_the_installed_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_skills_list_shows_registered_skills(tmp_path: Path) -> None:
    write_skill_dir(tmp_path)
    result = runner.invoke(app, ["skills", "list", "--skills-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "mathematics.identity" in result.stdout


def test_skills_list_on_empty_root_reports_no_skills(tmp_path: Path) -> None:
    result = runner.invoke(app, ["skills", "list", "--skills-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "No skills found" in result.stdout


def test_skills_list_json_emits_machine_readable_output(tmp_path: Path) -> None:
    write_skill_dir(tmp_path)
    result = runner.invoke(app, ["skills", "list", "--skills-root", str(tmp_path), "--json"])
    assert result.exit_code == 0
    assert '"id": "mathematics.identity"' in result.stdout
    assert '"schema": true' in result.stdout


def test_skills_inspect_shows_metadata(tmp_path: Path) -> None:
    write_skill_dir(
        tmp_path,
        manifest_overrides={"description": "A trivial fixture skill.", "tags": ["fixture"]},
    )
    result = runner.invoke(
        app, ["skills", "inspect", "mathematics.identity", "--skills-root", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "mathematics.identity" in result.stdout
    assert "method: identity v1" in result.stdout
    assert "A trivial fixture skill." in result.stdout
    assert "tags: fixture" in result.stdout


def test_skills_inspect_json_emits_machine_readable_output(tmp_path: Path) -> None:
    write_skill_dir(tmp_path)
    result = runner.invoke(
        app,
        ["skills", "inspect", "mathematics.identity", "--skills-root", str(tmp_path), "--json"],
    )
    assert result.exit_code == 0
    assert '"id": "mathematics.identity"' in result.stdout


def test_skills_list_prints_warnings_for_skills_that_failed_to_load(tmp_path: Path) -> None:
    write_skill_dir(tmp_path, name="valid")
    write_skill_dir(
        tmp_path,
        name="broken",
        manifest_overrides={"id": "mathematics.broken_INVALID"},
        front_matter_overrides={"id": "mathematics.broken_INVALID"},
    )
    result = runner.invoke(app, ["skills", "list", "--skills-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "mathematics.identity" in result.output
    assert "warning" in result.output


def test_skills_inspect_unknown_skill_exits_nonzero(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["skills", "inspect", "mathematics.unknown", "--skills-root", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert "skill_not_found" in result.output


def test_skills_inspect_debug_mode_raises_the_real_exception(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["--debug", "skills", "inspect", "mathematics.unknown", "--skills-root", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert result.exception is not None


def test_skills_validate_reports_ok_for_a_valid_skill(tmp_path: Path) -> None:
    write_skill_dir(tmp_path)
    result = runner.invoke(
        app, ["skills", "validate", "mathematics.identity", "--skills-root", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "OK" in result.stdout


def test_skills_validate_unknown_skill_exits_nonzero(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["skills", "validate", "mathematics.unknown", "--skills-root", str(tmp_path)]
    )
    assert result.exit_code == 1
