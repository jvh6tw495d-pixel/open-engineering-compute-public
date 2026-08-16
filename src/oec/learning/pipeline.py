"""L12 — Worker training pipeline (demo, not a product)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from oec.learning.contracts import ModelRef, TrainingConfig, TrainingMethod
from oec.learning.datasets import DatasetKind, LearningDataset
from oec.learning.environments import RewardSpec
from oec.learning.experiments import LearningExperiment


class WorkerStage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    method: TrainingMethod | str
    backend: str


class WorkerPipeline(BaseModel):
    """Declarative E2E plan: dataset → SFT/PEFT → optional RL → evaluate."""

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


def default_worker_dataset() -> LearningDataset:
    return LearningDataset(
        name="worker-demo",
        kind=DatasetKind.SFT,
        records=({"text": "solve x**2-2"}, {"text": "check units"}),
    )
