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

Routes live under ``/v1`` per the master handbook §13.3 (``/health`` is
the one deliberate exception — an unversioned liveness check is the
common convention, and the handbook itself lists it bare). A holistic
review at the end of Sprint 07 flagged the missing prefix as worth
fixing before any real adopter exists, since changing paths afterward
is a breaking change this project would rather not make.
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
from oec.execution.factory import build_validators
from oec.execution.models import ExecutionResult
from oec.execution.service import run_input_validators
from oec.sdk import Engine
from oec.validation.base import Severity


class RunRequest(BaseModel):
    """Body of ``POST /v1/skills/{skill_id}/run``."""

    model_config = ConfigDict(extra="forbid")

    inputs: dict[str, Any] = Field(default_factory=dict)
    version: str | None = None
    seed: int | None = None
    trace_id: str | None = None
    requested_by: str | None = None


class ValidateRequest(BaseModel):
    """Body of ``POST /v1/skills/{skill_id}/validate``."""

    model_config = ConfigDict(extra="forbid")

    inputs: dict[str, Any] = Field(default_factory=dict)
    version: str | None = None


class ExperimentRunRequest(BaseModel):
    """Body of ``POST /v1/experiments/run`` (W2.4)."""

    model_config = ConfigDict(extra="forbid")

    # Full ExperimentSpec as JSON object (or nested under "spec")
    spec: dict[str, Any] | None = None
    # Allow top-level ExperimentSpec fields for convenience
    id: str | None = None
    seed: int | None = None
    steps: list[dict[str, Any]] | None = None
    metrics: list[dict[str, Any]] | None = None
    validation: dict[str, Any] | None = None
    requested_by: str | None = None
    trace_id: str | None = None
    artifact_root: str | None = None
    persist_artifacts: bool | None = None


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

    @app.get("/v1/skills")
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

    @app.get("/v1/skills/{skill_id}")
    def get_skill(request: Request, skill_id: str, version: str | None = None) -> dict[str, Any]:
        try:
            skill = _engine(request).registry.get_skill(skill_id, version)
        except SkillNotFoundError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc
        return skill.manifest.model_dump(mode="json", by_alias=True)

    @app.post("/v1/skills/{skill_id}/validate")
    def validate_skill_inputs(
        request: Request, skill_id: str, body: ValidateRequest
    ) -> dict[str, Any]:
        """Run only the input-validation layers, without executing the skill.

        Reuses :func:`~oec.execution.service.run_input_validators` --
        the exact same validator list and crash-handling ``execute()``
        would use -- so "would this be INVALID" here always agrees with
        what a real ``run`` would classify (ADR 0005: no re-implemented
        validation rules).
        """
        try:
            skill = _engine(request).registry.get_skill(skill_id, body.version)
        except SkillNotFoundError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc

        input_validators, _ = build_validators(skill)
        outcomes = run_input_validators(input_validators, skill, dict(body.inputs))
        valid = not any(outcome.severity is Severity.ERROR for outcome in outcomes)
        return {
            "valid": valid,
            "outcomes": [outcome.model_dump(mode="json") for outcome in outcomes],
        }

    @app.post("/v1/skills/{skill_id}/run", response_model=ExecutionResult)
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

    @app.post("/v1/experiments/run")
    def run_experiment_endpoint(request: Request, body: ExperimentRunRequest) -> dict[str, Any]:
        """Run a multi-step ExperimentSpec (W2.4 / ADR 0034).

        Returns the full ``ExperimentRecord`` JSON. Scientific step outcomes
        live inside ``steps[].execution.status``; top-level ``status`` is
        ``ExperimentStatus`` (COMPLETED / VALIDATION_FAILED / …).
        """
        from oec.experiment.specs import ExperimentSpec

        if body.spec is not None:
            raw_spec: dict[str, Any] = dict(body.spec)
        else:
            raw_spec = {}
            if body.id is not None:
                raw_spec["id"] = body.id
            if body.seed is not None:
                raw_spec["seed"] = body.seed
            if body.steps is not None:
                raw_spec["steps"] = body.steps
            if body.metrics is not None:
                raw_spec["metrics"] = body.metrics
            if body.validation is not None:
                raw_spec["validation"] = body.validation

        try:
            exp_spec = ExperimentSpec.model_validate(raw_spec)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"invalid ExperimentSpec: {exc}") from exc

        try:
            record = _engine(request).run_experiment(
                exp_spec,
                requested_by=body.requested_by,
                trace_id=body.trace_id,
                artifact_root=body.artifact_root,
                persist_artifacts=body.persist_artifacts,
            )
        except SkillNotFoundError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc
        except OECError as exc:
            raise HTTPException(status_code=500, detail=exc.message) from exc

        payload: dict[str, Any] = record.to_dict()
        return payload

    return app
