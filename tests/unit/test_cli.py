from pathlib import Path

from typer.testing import CliRunner

from oec import __version__
from oec.cli.main import app
from oec.testing import write_skill_dir

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


# --- `oec run` (ADR 0014) ---------------------------------------------
#
# write_skill_dir's default manifest has no explicit "validation" block,
# so ValidationPolicy's defaults apply -- including mathematical=true,
# which would make build_validators require a validation.py the fixture
# doesn't create. Every run-command test below disables mathematical
# explicitly, matching how the fixture's implementation.py is a trivial
# passthrough with no domain-specific checks of its own.
_NO_EXTRA_VALIDATION = {
    "validation": {
        "schema": True,
        "dimensional": False,
        "mathematical": False,
        "physical": False,
        "numerical": False,
    }
}


def test_run_command_verified_result_exits_zero(tmp_path: Path) -> None:
    write_skill_dir(tmp_path, manifest_overrides=_NO_EXTRA_VALIDATION)
    result = runner.invoke(
        app,
        [
            "run",
            "mathematics.identity",
            "--skills-root",
            str(tmp_path),
            "--input",
            '{"value": 42}',
        ],
    )
    assert result.exit_code == 0
    assert "VERIFIED" in result.stdout
    assert '"value": 42' in result.stdout


def test_run_command_json_emits_machine_readable_output(tmp_path: Path) -> None:
    write_skill_dir(tmp_path, manifest_overrides=_NO_EXTRA_VALIDATION)
    result = runner.invoke(
        app,
        [
            "run",
            "mathematics.identity",
            "--skills-root",
            str(tmp_path),
            "--input",
            "{}",
            "--json",
        ],
    )
    assert result.exit_code == 0
    assert '"status": "VERIFIED"' in result.stdout


def test_run_command_reads_input_from_file(tmp_path: Path) -> None:
    write_skill_dir(tmp_path, manifest_overrides=_NO_EXTRA_VALIDATION)
    input_file = tmp_path / "input.json"
    input_file.write_text('{"value": 7}', encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "run",
            "mathematics.identity",
            "--skills-root",
            str(tmp_path),
            "--input-file",
            str(input_file),
        ],
    )
    assert result.exit_code == 0
    assert '"value": 7' in result.stdout


def test_run_command_missing_input_file_exits_one_cleanly(tmp_path: Path) -> None:
    """Regression guard (independent review of Sprint 06, Finding 1): a
    nonexistent --input-file must produce a clean CLI error, not a raw
    FileNotFoundError traceback -- read_text() used to run outside any
    OECError-handling try/except."""
    write_skill_dir(tmp_path, manifest_overrides=_NO_EXTRA_VALIDATION)
    result = runner.invoke(
        app,
        [
            "run",
            "mathematics.identity",
            "--skills-root",
            str(tmp_path),
            "--input-file",
            str(tmp_path / "does_not_exist.json"),
        ],
    )
    assert result.exit_code == 1
    assert "cannot read --input-file" in result.output
    assert "Traceback" not in result.output


def test_run_command_reads_input_from_stdin(tmp_path: Path) -> None:
    write_skill_dir(tmp_path, manifest_overrides=_NO_EXTRA_VALIDATION)
    result = runner.invoke(
        app,
        ["run", "mathematics.identity", "--skills-root", str(tmp_path)],
        input='{"value": 9}',
    )
    assert result.exit_code == 0
    assert '"value": 9' in result.stdout


def test_run_command_rejects_both_input_file_and_input(tmp_path: Path) -> None:
    write_skill_dir(tmp_path, manifest_overrides=_NO_EXTRA_VALIDATION)
    input_file = tmp_path / "input.json"
    input_file.write_text("{}", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "run",
            "mathematics.identity",
            "--skills-root",
            str(tmp_path),
            "--input",
            "{}",
            "--input-file",
            str(input_file),
        ],
    )
    assert result.exit_code == 1


def test_run_command_malformed_json_input_exits_one(tmp_path: Path) -> None:
    write_skill_dir(tmp_path, manifest_overrides=_NO_EXTRA_VALIDATION)
    result = runner.invoke(
        app,
        ["run", "mathematics.identity", "--skills-root", str(tmp_path), "--input", "not json"],
    )
    assert result.exit_code == 1


def test_run_command_non_object_json_input_exits_one(tmp_path: Path) -> None:
    write_skill_dir(tmp_path, manifest_overrides=_NO_EXTRA_VALIDATION)
    result = runner.invoke(
        app, ["run", "mathematics.identity", "--skills-root", str(tmp_path), "--input", "[1, 2]"]
    )
    assert result.exit_code == 1


def test_run_command_unknown_skill_exits_one(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["run", "mathematics.unknown", "--skills-root", str(tmp_path), "--input", "{}"]
    )
    assert result.exit_code == 1


def test_run_command_invalid_status_exits_three(tmp_path: Path) -> None:
    write_skill_dir(
        tmp_path,
        manifest_overrides=_NO_EXTRA_VALIDATION,
        input_schema_raw='{"type": "object", "required": ["value"], "additionalProperties": false}',
    )
    result = runner.invoke(
        app, ["run", "mathematics.identity", "--skills-root", str(tmp_path), "--input", "{}"]
    )
    assert result.exit_code == 3
    assert "INVALID" in result.stdout


def test_run_command_failed_status_exits_four(tmp_path: Path) -> None:
    write_skill_dir(
        tmp_path,
        manifest_overrides=_NO_EXTRA_VALIDATION,
        implementation_code="def execute(inputs):\n    raise ValueError('boom')\n",
    )
    result = runner.invoke(
        app, ["run", "mathematics.identity", "--skills-root", str(tmp_path), "--input", "{}"]
    )
    assert result.exit_code == 4
    assert "FAILED" in result.stdout


def test_run_command_inconclusive_status_exits_two(tmp_path: Path) -> None:
    write_skill_dir(
        tmp_path,
        manifest_overrides={
            **_NO_EXTRA_VALIDATION,
            "method": {"id": "test", "version": "1", "iterative": True},
        },
        implementation_code=(
            "def execute(inputs):\n"
            "    return {'result': inputs, 'diagnostics': {'converged': False}}\n"
        ),
    )
    result = runner.invoke(
        app, ["run", "mathematics.identity", "--skills-root", str(tmp_path), "--input", "{}"]
    )
    assert result.exit_code == 2
    assert "INCONCLUSIVE" in result.stdout
