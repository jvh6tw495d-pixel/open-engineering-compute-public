"""Explicit Learning bootstrap — install only when the operator asks.

Training / ``.finetune()`` / ``.train()`` never call this module.
Unsloth and Axolotl never land in the OEC project venv.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from oec.learning.errors import LearningError
from oec.learning.install_hints import ART_PYPI, ART_WRONG_PYPI, AXOLOTL_PIN, UNSLOTH_PIN

ENVS_ROOT_ENV = "OEC_LEARNING_ENVS"
InstallerName = Literal["uv", "pip"]
StepStatus = Literal["planned", "skipped", "dry-run", "installed", "failed"]
Into = Literal["current-venv", "isolated-venv", "none"]


class CommandRunner(Protocol):
    def __call__(self, argv: Sequence[str], *, cwd: str | None = None) -> CommandResult: ...


@dataclass(frozen=True)
class CommandResult:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class BootstrapStep:
    name: str
    status: StepStatus
    into: Into
    python: str | None
    commands: tuple[tuple[str, ...], ...]
    reason: str
    cwd: str | None = None


@dataclass
class StepReport:
    name: str
    status: StepStatus
    into: Into
    python: str | None
    commands: list[list[str]]
    message: str
    cwd: str | None = None


@dataclass
class BootstrapReport:
    auto_install: bool = False
    dry_run: bool = False
    ok: bool = True
    steps: list[StepReport] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def learning_envs_root(override: Path | None = None) -> Path:
    if override is not None:
        return override
    raw = os.environ.get(ENVS_ROOT_ENV)
    if raw:
        return Path(raw)
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else Path.home() / "AppData" / "Local"
        return base / "oec-learning-envs"
    return Path.home() / ".local" / "share" / "oec-learning-envs"


def venv_python(root: Path, *, platform: str) -> Path:
    if platform == "win32":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def find_oec_project(start: Path | None = None) -> Path | None:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        pyproject = candidate / "pyproject.toml"
        if pyproject.is_file() and (
            'name = "open-engineering-compute"' in pyproject.read_text(encoding="utf-8")
        ):
            return candidate
    return None


def detect_installer() -> InstallerName:
    return "uv" if shutil.which("uv") else "pip"


def _wrong_art_installed() -> bool:
    if importlib.util.find_spec("art") is None:
        return False
    try:
        module = importlib.import_module("art")
    except Exception:
        return False
    return not callable(getattr(module, "train_grpo", None))


def _require_targets(
    *, extras: bool, art: bool, unsloth: bool, axolotl: bool, all_targets: bool
) -> None:
    if not any((extras, art, unsloth, axolotl, all_targets)):
        raise LearningError(
            "Select --all or at least one of --extras/--art/--unsloth/--axolotl. "
            "Training calls never auto-install packages."
        )


def plan_bootstrap(
    *,
    extras: bool = False,
    art: bool = False,
    unsloth: bool = False,
    axolotl: bool = False,
    all_targets: bool = False,
    platform: str | None = None,
    installer: InstallerName | None = None,
    project_root: Path | None = None,
    envs_root: Path | None = None,
    current_python: Path | None = None,
    cwd: Path | None = None,
) -> tuple[BootstrapStep, ...]:
    _require_targets(
        extras=extras, art=art, unsloth=unsloth, axolotl=axolotl, all_targets=all_targets
    )
    host = platform or sys.platform
    tool: InstallerName = installer or detect_installer()
    python = current_python or Path(sys.executable)
    project = project_root if project_root is not None else find_oec_project(cwd)
    root = learning_envs_root(envs_root)
    want_extras = extras or all_targets
    want_art = art or all_targets
    want_unsloth = unsloth or all_targets
    want_axolotl = axolotl or all_targets
    steps: list[BootstrapStep] = []
    if want_extras:
        steps.append(_plan_extras(tool=tool, python=python, project=project))
    if want_art:
        steps.append(_plan_art(tool=tool, python=python))
    if want_unsloth:
        steps.append(
            _plan_isolated(
                name="unsloth",
                package=UNSLOTH_PIN,
                tool=tool,
                host=host,
                python=python,
                project=project,
                env_root=root / "unsloth",
            )
        )
    if want_axolotl:
        steps.append(
            _plan_axolotl(
                tool=tool,
                host=host,
                python=python,
                project=project,
                env_root=root / "axolotl",
                explicit=axolotl and not all_targets,
            )
        )
    return tuple(steps)


def run_bootstrap(
    steps: Sequence[BootstrapStep],
    *,
    dry_run: bool = False,
    runner: CommandRunner | None = None,
) -> BootstrapReport:
    execute: CommandRunner = runner or _default_runner
    report = BootstrapReport(auto_install=False, dry_run=dry_run)
    for step in steps:
        if step.status == "skipped":
            report.steps.append(_report_from_step(step, "skipped", step.reason))
            continue
        if dry_run:
            report.steps.append(_report_from_step(step, "dry-run", step.reason))
            continue
        message = step.reason
        status: StepStatus = "installed"
        for command in step.commands:
            result = execute(command, cwd=step.cwd)
            if result.returncode != 0:
                status = "failed"
                detail = (result.stderr or result.stdout).strip() or f"exit {result.returncode}"
                message = f"{step.reason} Failed: {detail}"
                report.ok = False
                break
        report.steps.append(_report_from_step(step, status, message))
    return report


def bootstrap_status(
    *,
    platform: str | None = None,
    envs_root: Path | None = None,
) -> dict[str, object]:
    from oec.learning.capability import probe_optional

    host = platform or sys.platform
    root = learning_envs_root(envs_root)
    isolated = {
        name: {
            "python": str(venv_python(root / name, platform=host)),
            "exists": venv_python(root / name, platform=host).is_file(),
        }
        for name in ("unsloth", "axolotl")
    }
    return {
        "auto_install": False,
        "bootstrap": "oec learning bootstrap --all",
        "envs_root": str(root),
        "probes": probe_optional(),
        "isolated": isolated,
    }


def _plan_extras(*, tool: InstallerName, python: Path, project: Path | None) -> BootstrapStep:
    commands: tuple[tuple[str, ...], ...]
    if tool == "uv" and project is not None:
        commands = (("uv", "sync", "--extra", "foundation", "--extra", "neural"),)
        workdir: str | None = str(project)
        reason = "Install oec[foundation]+oec[neural] into this project via uv sync."
    elif tool == "uv":
        commands = (("uv", "pip", "install", "--python", str(python), "oec[foundation,neural]"),)
        workdir = None
        reason = "No OEC checkout found; install extras into the current interpreter."
    elif project is not None:
        commands = ((str(python), "-m", "pip", "install", "-e", ".[foundation,neural]"),)
        workdir = str(project)
        reason = "Install oec[foundation]+oec[neural] editable into this interpreter."
    else:
        commands = ((str(python), "-m", "pip", "install", "oec[foundation,neural]"),)
        workdir = None
        reason = "No OEC checkout found; install extras into the current interpreter."
    return BootstrapStep(
        name="extras",
        status="planned",
        into="current-venv",
        python=str(python),
        commands=commands,
        reason=reason,
        cwd=workdir,
    )


def _plan_art(*, tool: InstallerName, python: Path) -> BootstrapStep:
    commands: list[tuple[str, ...]] = []
    if _wrong_art_installed():
        if tool == "uv":
            commands.append(
                ("uv", "pip", "uninstall", "-y", "--python", str(python), ART_WRONG_PYPI)
            )
        else:
            commands.append((str(python), "-m", "pip", "uninstall", "-y", ART_WRONG_PYPI))
    if tool == "uv":
        commands.append(("uv", "pip", "install", "--python", str(python), ART_PYPI))
    else:
        commands.append((str(python), "-m", "pip", "install", ART_PYPI))
    return BootstrapStep(
        name="art",
        status="planned",
        into="current-venv",
        python=str(python),
        commands=tuple(commands),
        reason=f"Install {ART_PYPI} into the current interpreter (never the ASCII-art package).",
    )


def _plan_isolated(
    *,
    name: str,
    package: str,
    tool: InstallerName,
    host: str,
    python: Path,
    project: Path | None,
    env_root: Path,
) -> BootstrapStep:
    isolated = venv_python(env_root, platform=host)
    commands: list[tuple[str, ...]] = []
    if tool == "uv":
        commands.append(("uv", "venv", str(env_root), "--python", str(python)))
        commands.append(("uv", "pip", "install", "--python", str(isolated), package))
        if project is not None:
            commands.append(("uv", "pip", "install", "--python", str(isolated), "-e", str(project)))
    else:
        commands.append((str(python), "-m", "venv", str(env_root)))
        commands.append((str(isolated), "-m", "pip", "install", package))
        if project is not None:
            commands.append((str(isolated), "-m", "pip", "install", "-e", str(project)))
    return BootstrapStep(
        name=name,
        status="planned",
        into="isolated-venv",
        python=str(isolated),
        commands=tuple(commands),
        reason=(
            f"Create an isolated venv at {env_root} and install {package} there. "
            "Do not mix this interpreter with the OEC project venv."
        ),
    )


def _plan_axolotl(
    *,
    tool: InstallerName,
    host: str,
    python: Path,
    project: Path | None,
    env_root: Path,
    explicit: bool,
) -> BootstrapStep:
    if host == "win32":
        reason = (
            "Axolotl cannot be installed on native Windows (no triton wheel). "
            "Use WSL or Linux. "
            + ("Requested explicitly." if explicit else "Skipped by --all on this platform.")
        )
        return BootstrapStep(
            name="axolotl",
            status="skipped",
            into="none",
            python=None,
            commands=(),
            reason=reason,
        )
    return _plan_isolated(
        name="axolotl",
        package=AXOLOTL_PIN,
        tool=tool,
        host=host,
        python=python,
        project=project,
        env_root=env_root,
    )


def _report_from_step(step: BootstrapStep, status: StepStatus, message: str) -> StepReport:
    return StepReport(
        name=step.name,
        status=status,
        into=step.into,
        python=step.python,
        commands=[list(command) for command in step.commands],
        message=message,
        cwd=step.cwd,
    )


def _default_runner(argv: Sequence[str], *, cwd: str | None = None) -> CommandResult:
    completed = subprocess.run(list(argv), check=False, capture_output=True, text=True, cwd=cwd)
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )
