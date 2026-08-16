"""L12 — sequential FineTune demo (not a product, not a full RL factory)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from oec.execution.models import ExecutionResult
from oec.learning.contracts import (
    ArtifactRef,
    FineTuneBackendName,
    ModelRef,
    TrainingConfig,
    TrainingMethod,
)
from oec.learning.datasets import DatasetKind, LearningDataset
from oec.learning.environments import (
    ElectricalEngineeringEnvironment,
    MathematicsEnvironment,
    PhysicsEnvironment,
    RewardSpec,
    ToolUseEnvironment,
)
from oec.learning.errors import BackendNotAvailableError, LearningError
from oec.learning.experiments import LearningExperiment, LearningRunRecord, run_learning_experiment
from oec.learning.rl import Environment, Episode
from oec.learning.verifiers import execution_result_reward, execution_result_scores


class WorkerStage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    method: TrainingMethod | str
    backend: str


class WorkerPipeline(BaseModel):
    """Sequential FineTune stages with optional artifact chaining.

    This is a demo executor: FineTune backends run in order. An ``art`` stage
    is optional RL. Evaluation only runs when a stage returns verifier scores.
    It is not a complete SFT→RL→eval product.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    name: str = "scientific-python-worker"
    model: ModelRef
    dataset: LearningDataset
    stages: tuple[WorkerStage, ...] = (
        WorkerStage(name="sft", method=TrainingMethod.SFT, backend="huggingface"),
        WorkerStage(name="peft", method=TrainingMethod.LORA, backend="huggingface"),
    )
    environment_name: str = "python"
    reward: RewardSpec = Field(default_factory=RewardSpec)
    episodes: tuple[Episode, ...] = ()
    evaluations: tuple[ExecutionResult | dict[str, Any], ...] = ()

    def as_experiment(self, *, experiment_id: str) -> LearningExperiment:
        method = TrainingMethod.LORA
        return LearningExperiment(
            experiment_id=experiment_id,
            model=self.model,
            dataset=self.dataset,
            config=TrainingConfig(method=method, seed=self.dataset.seed),
            title=self.name,
        )

    def plan(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model_id": self.model.model_id,
            "dataset_hash": self.dataset.content_hash,
            "stages": [stage.model_dump(mode="json") for stage in self.stages],
            "environment": self.environment_name,
        }

    def run(self, *, experiment_id: str | None = None) -> dict[str, Any]:
        """Run declared stages. Status is derived from stage results."""
        self.dataset.verify_integrity()
        records: list[LearningRunRecord] = []
        rl_results: list[dict[str, Any]] = []
        prefix = experiment_id or self.name
        previous_artifact: ArtifactRef | None = None
        model = self.model
        for stage in self.stages:
            backend_key = stage.backend.strip().lower()
            if backend_key == "art":
                from oec.learning.backends.art import ARTBackend

                if not self.episodes:
                    raise LearningError(
                        "ART worker stage requires pipeline.episodes; empty train is not implied",
                        details={"stage": stage.name},
                    )
                env = _environment_for(self.environment_name)
                typed = tuple(
                    item if isinstance(item, Episode) else Episode.model_validate(item)
                    for item in self.episodes
                )
                rl = ARTBackend().train(env, typed)
                rl_results.append({"stage": stage.name, **rl.model_dump(mode="json")})
                continue
            if backend_key not in {item.value for item in FineTuneBackendName}:
                raise BackendNotAvailableError(
                    (
                        f"worker stage {stage.name!r} backend "
                        f"{stage.backend!r} is not a FineTune backend"
                    ),
                    details={"stage": stage.name, "backend": stage.backend},
                )
            method = (
                stage.method
                if isinstance(stage.method, TrainingMethod)
                else TrainingMethod(stage.method)
            )
            hyperparameters: dict[str, float | int | str] = {}
            if method is TrainingMethod.SFT:
                hyperparameters["sft_via_lora"] = "1"
            if previous_artifact is not None and previous_artifact.path:
                hyperparameters["adapter_path"] = previous_artifact.path
                model = ModelRef(
                    model_id=model.model_id,
                    family=model.family,
                    revision=model.revision,
                    metadata={
                        **model.metadata,
                        "adapter_path": previous_artifact.path,
                    },
                )
            record = run_learning_experiment(
                LearningExperiment(
                    experiment_id=f"{prefix}.{stage.name}",
                    model=model,
                    dataset=self.dataset,
                    config=TrainingConfig(
                        method=method,
                        backend=FineTuneBackendName(backend_key),
                        seed=self.dataset.seed,
                        hyperparameters=hyperparameters,
                    ),
                    title=f"{self.name}:{stage.name}",
                )
            )
            records.append(record)
            previous_artifact = record.result.artifact
        evaluation = _evaluate_stages(
            records,
            self.reward,
            self.environment_name,
            executions=self.evaluations,
        )
        fine_ok = bool(records) and all(item.result.status == "ok" for item in records)
        rl_ok = all(item.get("status") == "ok" for item in rl_results)
        if records and fine_ok and (not rl_results or rl_ok):
            status = "ok"
        elif records or rl_results:
            status = "degraded"
        else:
            status = "empty"
        return {
            "name": self.name,
            "status": status,
            "plan": self.plan(),
            "experiment_id": prefix,
            "records": [record.model_dump(mode="json") for record in records],
            "rl": rl_results,
            "evaluation": evaluation,
        }


def payload_from_execution(result: Any) -> dict[str, Any]:
    """Map an OEC ExecutionResult (or dict) to verifier payload. No LLM."""
    if isinstance(result, dict):
        return dict(result)
    status = getattr(result, "status", None)
    status_value = str(getattr(status, "value", status) or "")
    validation = getattr(result, "validation", None) or {}
    diagnostics = getattr(result, "diagnostics", None) or {}
    payload: dict[str, Any] = {
        "status": status_value,
        "duration_ms": getattr(result, "duration_ms", None),
    }
    if isinstance(validation, dict):
        if "units_ok" in validation:
            payload["units_ok"] = validation["units_ok"]
        if "constraints_ok" in validation:
            payload["constraints_ok"] = validation["constraints_ok"]
        elif "constraint_ok" in validation:
            payload["constraint_ok"] = validation["constraint_ok"]
    if isinstance(diagnostics, dict) and "tokens" in diagnostics:
        payload["tokens"] = diagnostics["tokens"]
    return payload


def _evaluate_stages(
    records: list[LearningRunRecord],
    spec: RewardSpec,
    environment_name: str,
    executions: tuple[Any, ...] = (),
) -> dict[str, Any]:
    for item in reversed(executions):
        payload = payload_from_execution(item)
        scores = execution_result_scores(payload)
        return {
            "status": "ok",
            "environment": environment_name,
            "scores": scores,
            "reward": execution_result_reward(payload, spec),
            "source": "execution_result",
        }
    for record in reversed(records):
        staged = record.result.details.get("execution")
        if isinstance(staged, dict):
            scores = execution_result_scores(staged)
            return {
                "status": "ok",
                "environment": environment_name,
                "scores": scores,
                "reward": execution_result_reward(staged, spec),
                "source_run_id": record.run_id,
            }
    return {
        "status": "skipped",
        "environment": environment_name,
        "reason": "no ExecutionResult or verifier scores from stages",
    }


def _environment_for(name: str) -> Environment:
    key = name.strip().lower()
    if key in {"physics"}:
        return PhysicsEnvironment()
    if key in {"electrical_engineering", "ee"}:
        return ElectricalEngineeringEnvironment()
    if key in {"tool_use", "python", "tools"}:
        return ToolUseEnvironment()
    return MathematicsEnvironment()


def default_worker_dataset() -> LearningDataset:
    return LearningDataset(
        name="worker-demo",
        kind=DatasetKind.SFT,
        records=({"text": "solve x**2-2"}, {"text": "check units"}),
    )
