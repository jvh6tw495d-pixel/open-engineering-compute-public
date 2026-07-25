"""OEC command-line interface — a thin adapter over the Skill Registry.

Per ADR 0005 (thin interface adapters), this module holds no scientific or
validation logic of its own: it only translates CLI arguments into
`SkillRegistry` calls and formats the result as JSON or human-readable
text. Only ``version`` and the ``skills`` subcommands (list/inspect/
validate) exist so far — ``run``/``validate`` for executions arrive with
the Execution Service in Sprint 03, and ``server api``/``server mcp``
arrive in Sprint 07.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.table import Table

from oec import __version__
from oec.errors import OECError
from oec.skills.registry.registry import SkillRegistry

app = typer.Typer(no_args_is_help=True, add_completion=False)
skills_app = typer.Typer(no_args_is_help=True)
app.add_typer(skills_app, name="skills")

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


if __name__ == "__main__":
    app()
