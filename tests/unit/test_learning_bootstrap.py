"""Explicit Learning bootstrap — operator-triggered, never from training."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from oec.cli.main import app
from oec.learning import plan_bootstrap, run_bootstrap
from oec.learning.bootstrap import CommandResult, bootstrap_status
from oec.learning.errors import LearningError
from oec.learning.install_hints import ART_PYPI, UNSLOTH_PIN


def test_plan_requires_an_explicit_target() -> None:
    with pytest.raises(LearningError, match="never auto-install"):
        plan_bootstrap()


def test_all_on_windows_skips_axolotl_and_isolates_unsloth(tmp_path: Path) -> None:
    current = tmp_path / "project-venv" / "python.exe"
    steps = plan_bootstrap(
        all_targets=True,
        platform="win32",
        installer="uv",
        project_root=tmp_path,
        envs_root=tmp_path / "envs",
        current_python=current,
    )
    by_name = {step.name: step for step in steps}
    assert set(by_name) == {"extras", "art", "unsloth", "axolotl"}
    assert by_name["art"].into == "current-venv"
    assert any(ART_PYPI in part for cmd in by_name["art"].commands for part in cmd)
    assert by_name["unsloth"].into == "isolated-venv"
    assert str(current) not in by_name["unsloth"].python
    assert "unsloth" in (by_name["unsloth"].python or "")
    install_unsloth = [
        cmd for cmd in by_name["unsloth"].commands if any(UNSLOTH_PIN in part for part in cmd)
    ]
    assert install_unsloth
    assert all(str(current) not in cmd for cmd in install_unsloth)
    assert by_name["axolotl"].status == "skipped"
    assert by_name["axolotl"].commands == ()
    extras_cmd = " ".join(by_name["extras"].commands[0])
    assert "--extra foundation" in extras_cmd
    assert "--all-extras" not in extras_cmd


def test_unsloth_never_installs_into_current_venv(tmp_path: Path) -> None:
    current = tmp_path / "oec-python"
    steps = plan_bootstrap(
        unsloth=True,
        platform="linux",
        installer="pip",
        project_root=None,
        envs_root=tmp_path / "envs",
        current_python=current,
    )
    step = steps[0]
    assert step.name == "unsloth"
    assert step.into == "isolated-venv"
    for command in step.commands:
        if any(UNSLOTH_PIN in part for part in command):
            assert str(current) not in command
            assert command[0].endswith("python") or "python" in command[0]


def test_dry_run_does_not_invoke_runner(tmp_path: Path) -> None:
    called: list[tuple[str, ...]] = []

    def runner(argv: list[str] | tuple[str, ...], *, cwd: str | None = None) -> CommandResult:
        called.append(tuple(argv))
        return CommandResult(1, "", "should not run")

    steps = plan_bootstrap(
        art=True,
        installer="uv",
        platform="win32",
        project_root=None,
        current_python=tmp_path / "python",
    )
    report = run_bootstrap(steps, dry_run=True, runner=runner)
    assert called == []
    assert report.auto_install is False
    assert report.dry_run is True
    assert report.ok is True
    assert report.steps[0].status == "dry-run"
    assert report.steps[0].name == "art"


def test_runner_failure_marks_step_failed(tmp_path: Path) -> None:
    def runner(argv: list[str] | tuple[str, ...], *, cwd: str | None = None) -> CommandResult:
        return CommandResult(2, "", "network down")

    steps = plan_bootstrap(
        art=True,
        installer="pip",
        platform="linux",
        project_root=None,
        current_python=tmp_path / "python",
    )
    report = run_bootstrap(steps, runner=runner)
    assert report.ok is False
    assert report.steps[0].status == "failed"
    assert "network down" in report.steps[0].message


def test_status_never_claims_auto_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OEC_LEARNING_ENVS", str(tmp_path / "envs"))
    payload = bootstrap_status(platform="win32", envs_root=tmp_path / "envs")
    assert payload["auto_install"] is False
    assert payload["bootstrap"] == "oec learning bootstrap --all"
    isolated = payload["isolated"]
    assert isinstance(isolated, dict)
    assert isolated["unsloth"]["exists"] is False


def test_cli_bootstrap_without_target_exits_1() -> None:
    result = CliRunner().invoke(app, ["learning", "bootstrap"])
    assert result.exit_code == 1
    assert "never auto-install" in result.output


def test_cli_bootstrap_dry_run_all_is_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OEC_LEARNING_ENVS", str(tmp_path / "envs"))
    result = CliRunner().invoke(app, ["learning", "bootstrap", "--all", "--dry-run"])
    assert result.exit_code == 0
    assert "openpipe-art" in result.output
    assert "isolated" in result.output.lower() or "unsloth" in result.output
    assert "Training calls still never auto-install" in result.output


def test_cli_status_json_flags_no_auto_install() -> None:
    result = CliRunner().invoke(app, ["learning", "status", "--json"])
    assert result.exit_code == 0
    assert '"auto_install": false' in result.stdout
    assert "oec learning bootstrap --all" in result.stdout
