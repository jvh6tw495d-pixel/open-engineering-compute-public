"""REST API surface over :class:`oec.sdk.Engine` (ADR 0005, ADR 0015).

Thin adapter, per ADR 0005: this module does not select a numerical
method, apply validation rules, or reshape scientific content — every
endpoint wraps one shared, warmed ``Engine`` built once at startup and
returns its results close to verbatim. ``Engine.run()`` already
serializes every execution through a single lock (ADR 0015); this
layer adds no additional concurrency control of its own.

HTTP status codes carry only *transport*-level meaning (ADR 0015 §1):
``200`` with the full :class:`~oec.execution.models.ExecutionResult`
body whenever the pipeline actually produced one — including
``INVALID``/``FAILED``/``INCONCLUSIVE``, which are structured
scientific outcomes the caller reads from ``body.status``, not
transport failures. ``404``/``422`` are reserved for requests that
never reached the pipeline at all (unknown skill, a body that doesn't
even parse).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from oec import __version__
from oec.errors import OECError, SkillNotFoundError
from oec.execution.models import ExecutionResult
from oec.sdk import Engine


class RunRequest(BaseModel):
    """Body of ``POST /skills/{skill_id}/run``."""

    model_config = ConfigDict(extra="forbid")

    inputs: dict[str, Any] = Field(default_factory=dict)
    version: str | None = None
    seed: int | None = None
    trace_id: str | None = None
    requested_by: str | None = None


def _engine(request: Request) -> Engine:
    return request.app.state.engine  # type: ignore[no-any-return]


def create_app(skills_root: str | Path = "skills") -> FastAPI:
    """Build the REST API app, wiring one warmed ``Engine`` for its whole lifetime."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = Engine(skills_root=skills_root)
        engine.warm()
        app.state.engine = engine
        yield

    app = FastAPI(
        title="Open Engineering Compute API",
        version=__version__,
        lifespan=lifespan,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "oec_version": __version__}

    @app.get("/skills")
    def list_skills(
        request: Request,
        domain: str | None = None,
        tag: Annotated[list[str] | None, Query()] = None,
        include_retired: bool = False,
    ) -> list[dict[str, Any]]:
        manifests = _engine(request).registry.search(
            domain=domain, tags=tag, include_retired=include_retired
        )
        return [manifest.model_dump(mode="json", by_alias=True) for manifest in manifests]

    @app.get("/skills/{skill_id}")
    def get_skill(request: Request, skill_id: str, version: str | None = None) -> dict[str, Any]:
        try:
            skill = _engine(request).registry.get_skill(skill_id, version)
        except SkillNotFoundError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc
        return skill.manifest.model_dump(mode="json", by_alias=True)

    @app.post("/skills/{skill_id}/run", response_model=ExecutionResult)
    def run_skill(request: Request, skill_id: str, body: RunRequest) -> ExecutionResult:
        try:
            return _engine(request).run(
                skill_id,
                body.inputs,
                skill_version=body.version,
                seed=body.seed,
                trace_id=body.trace_id,
                requested_by=body.requested_by,
            )
        except SkillNotFoundError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc
        except OECError as exc:
            raise HTTPException(status_code=500, detail=exc.message) from exc

    return app
