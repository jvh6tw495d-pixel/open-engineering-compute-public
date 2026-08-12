"""OEC command-line interface — a thin adapter over the Skill Registry
and the ``oec`` SDK facade.

Per ADR 0005 (thin interface adapters), this module holds no scientific or
validation logic of its own: it only translates CLI arguments into
`SkillRegistry`/`oec.sdk.Engine` calls and formats the result as JSON or
human-readable text. ``version``, the ``skills`` subcommands (list/
inspect/validate), ``run`` (ADR 0014), and ``server api``/``server mcp``
(ADR 0015) launch the REST/MCP interfaces built on the same `Engine`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.table import Table

from oec import __version__
from oec.errors import OECError
from oec.execution.models import ExecutionResult, ExecutionStatus
from oec.sdk import Engine
from oec.skills.registry.registry import SkillRegistry

if sys.platform == "win32":
    # Non-UTF-8 Windows console codepages (e.g. cp1252) otherwise crash on any
    # skill title/description containing non-Latin-1 characters (e.g. Greek
    # letters in physics skill metadata) the moment Rich writes them out.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")

_STATUS_EXIT_CODES: dict[ExecutionStatus, int] = {
    ExecutionStatus.VERIFIED: 0,
    ExecutionStatus.VALIDATED: 0,
    ExecutionStatus.CONVERGED_WITH_WARNINGS: 0,
    ExecutionStatus.APPROXIMATE: 0,
    ExecutionStatus.INCONCLUSIVE: 2,
    ExecutionStatus.INVALID: 3,
    ExecutionStatus.FAILED: 4,
}
"""``ExecutionStatus`` -> process exit code (ADR 0014). Exit code ``1`` is
reserved for CLI-level errors that never produced an ``ExecutionResult``
at all (unknown skill id, malformed ``--input`` JSON, bad ``--skills-root``)."""

app = typer.Typer(no_args_is_help=True, add_completion=False)
skills_app = typer.Typer(no_args_is_help=True)
app.add_typer(skills_app, name="skills")
server_app = typer.Typer(no_args_is_help=True)
app.add_typer(server_app, name="server")
experiment_app = typer.Typer(no_args_is_help=True)
app.add_typer(experiment_app, name="experiment")

console = Console()
error_console = Console(stderr=True)

_debug = False

SkillsRootOption = Annotated[
    Path,
    typer.Option(
        "--skills-root",
        envvar="OEC_SKILLS_ROOT",
        help="Root directory to discover skills under.",
    ),
]
JsonOption = Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")]
VersionOption = Annotated[
    str | None, typer.Option("--version", help="Exact skill version to target.")
]


@app.callback()
def main(
    debug: Annotated[
        bool, typer.Option("--debug", help="Show full tracebacks instead of a short message.")
    ] = False,
) -> None:
    """Open Engineering Compute command-line interface."""
    global _debug
    _debug = debug


@app.command()
def version() -> None:
    """Print the installed OEC version."""
    console.print(__version__)


def _load_registry(skills_root: Path) -> tuple[SkillRegistry, list[str]]:
    registry = SkillRegistry()
    report = registry.register_all(skills_root)
    warnings = [
        f"{failure.path}: {failure.error.to_dict()['message']}" for failure in report.failures
    ]
    return registry, warnings


def _require_skills_root(skills_root: Path) -> None:
    """Fail fast for long-lived server commands with a missing skills root.

    ``discover_skill_dirs`` treats a missing root as "zero skills" by design
    (so one-shot commands like ``skills list`` degrade gracefully), but a
    server that silently starts with zero skills leaves every tool call
    failing downstream with no indication the root itself was wrong.
    """
    try:
        is_dir = skills_root.is_dir()
    except OSError:
        is_dir = False
    if not is_dir:
        error_console.print(
            f"[bold red]error[/bold red]: skills root {skills_root} does not exist or is not a "
            "directory (pass --skills-root or set OEC_SKILLS_ROOT)"
        )
        raise typer.Exit(code=1)


def _fail(exc: OECError) -> NoReturn:
    if _debug:
        raise exc
    error_console.print(f"[bold red]error[/bold red] ({exc.code}): {exc.message}")
    if exc.details:
        error_console.print(exc.details)
    raise typer.Exit(code=1)


@skills_app.command("list")
def skills_list(
    skills_root: SkillsRootOption = Path("skills"),
    domain: Annotated[str | None, typer.Option(help="Filter by domain.")] = None,
    tag: Annotated[
        list[str] | None, typer.Option(help="Filter by required tag (repeatable).")
    ] = None,
    include_retired: Annotated[bool, typer.Option(help="Include retired skills.")] = False,
    as_json: JsonOption = False,
) -> None:
    """List registered skills."""
    registry, warnings = _load_registry(skills_root)
    for warning in warnings:
        error_console.print(f"[yellow]warning[/yellow]: {warning}")

    manifests = registry.search(domain=domain, tags=tag, include_retired=include_retired)

    if as_json:
        console.print_json(
            data=[manifest.model_dump(mode="json", by_alias=True) for manifest in manifests]
        )
        return

    if not manifests:
        console.print("No skills found.")
        return

    table = Table("ID", "Version", "Status", "Domain", "Title")
    for manifest in manifests:
        table.add_row(
            manifest.id, manifest.version, manifest.status.value, manifest.domain, manifest.title
        )
    console.print(table)


@skills_app.command("inspect")
def skills_inspect(
    skill_id: str,
    version: VersionOption = None,
    skills_root: SkillsRootOption = Path("skills"),
    as_json: JsonOption = False,
) -> None:
    """Show full metadata for a single skill."""
    registry, _warnings = _load_registry(skills_root)
    try:
        skill = registry.get_skill(skill_id, version)
    except OECError as exc:
        _fail(exc)

    if as_json:
        console.print_json(data=skill.manifest.model_dump(mode="json", by_alias=True))
        return

    manifest = skill.manifest
    console.print(f"[bold]{manifest.id}[/bold] v{manifest.version} ({manifest.status.value})")
    console.print(manifest.title)
    if manifest.description:
        console.print(manifest.description)
    console.print(f"domain: {manifest.domain}")
    console.print(f"method: {manifest.method.id} v{manifest.method.version}")
    console.print(f"entrypoint: {manifest.entrypoint.module}.{manifest.entrypoint.function}")
    console.print(f"deterministic: {manifest.execution.deterministic}")
    if manifest.tags:
        console.print(f"tags: {', '.join(manifest.tags)}")
    console.print(f"path: {skill.path}")


@skills_app.command("validate")
def skills_validate(
    skill_id: str,
    version: VersionOption = None,
    skills_root: SkillsRootOption = Path("skills"),
) -> None:
    """Confirm a skill is registered and its manifest is valid."""
    registry, _warnings = _load_registry(skills_root)
    try:
        registry.validate(skill_id, version)
    except OECError as exc:
        _fail(exc)
    console.print(f"[green]OK[/green]: {skill_id} is valid")


@app.command("run")
def run_skill(
    skill_id: str,
    version: VersionOption = None,
    skills_root: SkillsRootOption = Path("skills"),
    input_file: Annotated[
        Path | None, typer.Option("--input-file", help="Read inputs from a JSON file.")
    ] = None,
    input_json: Annotated[
        str | None, typer.Option("--input", help="Inputs as a JSON object string.")
    ] = None,
    seed: Annotated[int | None, typer.Option(help="Seed to record in provenance.")] = None,
    trace_id: Annotated[str | None, typer.Option(help="Trace id to record in provenance.")] = None,
    requested_by: Annotated[
        str | None, typer.Option(help="Requester identity to record in provenance.")
    ] = None,
    as_json: JsonOption = False,
) -> None:
    """Execute a skill and print its result.

    Inputs come from exactly one of --input-file, --input, or stdin (in
    that precedence order) -- never guessed from which happens to be
    non-empty. Exit code reflects ExecutionStatus (ADR 0014): 0 for a
    usable result (VERIFIED/VALIDATED/CONVERGED_WITH_WARNINGS/
    APPROXIMATE), 2 for INCONCLUSIVE, 3 for INVALID, 4 for FAILED, and 1
    for a CLI-level error (unknown skill, malformed --input JSON) that
    never produced a result at all.
    """
    if input_file is not None and input_json is not None:
        error_console.print("[bold red]error[/bold red]: pass only one of --input-file/--input")
        raise typer.Exit(code=1)

    if input_file is not None:
        try:
            raw_inputs = input_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            error_console.print(f"[bold red]error[/bold red]: cannot read --input-file: {exc}")
            raise typer.Exit(code=1) from exc
    elif input_json is not None:
        raw_inputs = input_json
    else:
        raw_inputs = sys.stdin.read()

    try:
        inputs = json.loads(raw_inputs)
    except json.JSONDecodeError as exc:
        error_console.print(f"[bold red]error[/bold red]: malformed JSON input: {exc}")
        raise typer.Exit(code=1) from exc
    if not isinstance(inputs, dict):
        error_console.print("[bold red]error[/bold red]: input JSON must be an object")
        raise typer.Exit(code=1)

    try:
        engine = Engine(skills_root=skills_root)
        result = engine.run(
            skill_id,
            inputs,
            skill_version=version,
            seed=seed,
            trace_id=trace_id,
            requested_by=requested_by,
        )
    except OECError as exc:
        _fail(exc)

    if as_json:
        console.print_json(data=result.model_dump(mode="json"))
    else:
        _print_run_summary(result)

    raise typer.Exit(code=_STATUS_EXIT_CODES[result.status])


def _print_run_summary(result: ExecutionResult) -> None:
    status_color = "green" if _STATUS_EXIT_CODES[result.status] == 0 else "red"
    console.print(
        f"[bold {status_color}]{result.status.value}[/bold {status_color}] "
        f"{result.skill.id} v{result.skill.version}"
    )
    if result.result:
        console.print("result:")
        console.print_json(data=result.result)
    if result.diagnostics:
        console.print("diagnostics:")
        console.print_json(data=result.diagnostics)
    for warning in result.warnings:
        console.print(f"[yellow]warning[/yellow]: {warning}")


_EXPERIMENT_EXIT: dict[str, int] = {
    "COMPLETED": 0,
    "VALIDATION_FAILED": 2,
    "ABORTED": 3,
    "INVALID": 3,
    "FAILED": 4,
}


@experiment_app.command("run")
def experiment_run(
    skills_root: SkillsRootOption = Path("skills"),
    spec_file: Annotated[
        Path | None,
        typer.Option("--spec-file", help="ExperimentSpec JSON file."),
    ] = None,
    spec_json: Annotated[
        str | None,
        typer.Option("--spec", help="ExperimentSpec as a JSON object string."),
    ] = None,
    as_json: JsonOption = True,
) -> None:
    """Run a multi-step ExperimentSpec (W2 / ADR 0034).

    Exit codes: 0 COMPLETED, 2 VALIDATION_FAILED, 3 ABORTED/INVALID, 4 FAILED,
    1 CLI error (bad JSON / missing file).
    """
    from oec.experiment import ExperimentSpec
    from oec.experiment.record import ExperimentStatus

    if spec_file is not None and spec_json is not None:
        error_console.print("[bold red]error[/bold red]: pass only one of --spec-file/--spec")
        raise typer.Exit(code=1)
    if spec_file is None and spec_json is None:
        error_console.print("[bold red]error[/bold red]: provide --spec-file or --spec")
        raise typer.Exit(code=1)

    if spec_file is not None:
        try:
            raw = spec_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            error_console.print(f"[bold red]error[/bold red]: cannot read --spec-file: {exc}")
            raise typer.Exit(code=1) from exc
    else:
        raw = spec_json or ""

    try:
        payload = json.loads(raw)
        exp_spec = ExperimentSpec.model_validate(payload)
    except (json.JSONDecodeError, Exception) as exc:
        error_console.print(f"[bold red]error[/bold red]: invalid ExperimentSpec: {exc}")
        raise typer.Exit(code=1) from exc

    try:
        engine = Engine(skills_root=skills_root)
        record = engine.run_experiment(exp_spec)
    except OECError as exc:
        _fail(exc)

    if as_json:
        console.print_json(data=record.to_dict())
    else:
        color = "green" if record.status == ExperimentStatus.COMPLETED else "red"
        console.print(
            f"[bold {color}]{record.status.value}[/bold {color}] "
            f"experiment={record.spec.id} run_id={record.run_id} "
            f"steps={len(record.steps)} validation_passed={record.validation.passed}"
        )
        if record.metrics:
            console.print("metrics:")
            console.print_json(data=[m.model_dump(mode="json") for m in record.metrics])

    raise typer.Exit(code=_EXPERIMENT_EXIT.get(record.status.value, 4))


@server_app.command("api")
def server_api(
    skills_root: SkillsRootOption = Path("skills"),
    host: Annotated[str, typer.Option(help="Host/interface to bind.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port to bind.")] = 8000,
) -> None:
    """Run the REST API (ADR 0015) with uvicorn.

    Requires the ``api`` extra (``uv sync --extra api`` /
    ``pip install 'oec[api]'``) — ``fastapi``/``uvicorn`` are optional
    dependencies, not part of the base install.
    """
    _require_skills_root(skills_root)
    try:
        import uvicorn

        from oec.api.app import create_app
    except ImportError as exc:
        error_console.print(
            "[bold red]error[/bold red]: the REST API requires the 'api' extra "
            "(uv sync --extra api / pip install 'oec[api]')"
        )
        if _debug:
            raise
        raise typer.Exit(code=1) from exc

    uvicorn.run(create_app(skills_root=skills_root), host=host, port=port)


@server_app.command("mcp")
def server_mcp(skills_root: SkillsRootOption = Path("skills")) -> None:
    """Run the MCP server (ADR 0015) over stdio.

    Requires the ``mcp`` extra (``uv sync --extra mcp`` /
    ``pip install 'oec[mcp]'``) — the ``mcp`` package is an optional
    dependency, not part of the base install.
    """
    _require_skills_root(skills_root)
    try:
        from oec.mcp import run_stdio_server
    except ImportError as exc:
        error_console.print(
            "[bold red]error[/bold red]: the MCP server requires the 'mcp' extra "
            "(uv sync --extra mcp / pip install 'oec[mcp]')"
        )
        if _debug:
            raise
        raise typer.Exit(code=1) from exc

    run_stdio_server(skills_root=skills_root)


if __name__ == "__main__":
    app()
