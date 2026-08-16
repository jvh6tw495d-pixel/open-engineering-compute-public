"""Hugging Face reference backend (L5) — lazy, fail-closed, no public HF types."""

from __future__ import annotations

from typing import Any

from oec.learning.contracts import (
    ArtifactRef,
    FineTuneBackendName,
    ModelRef,
    TrainingConfig,
    TrainingMethod,
    TrainingResult,
)
from oec.learning.datasets import LearningDataset, texts_from_sft
from oec.learning.errors import BackendNotAvailableError


class HuggingFaceBackend:
    """Reference FineTune backend. Delegates to ``oec.foundation.peft_train``."""

    name = FineTuneBackendName.HUGGINGFACE

    def finetune(
        self,
        model: ModelRef,
        dataset: LearningDataset,
        config: TrainingConfig,
    ) -> TrainingResult:
        try:
            from oec.foundation.contracts import (
                FoundationModelSpec,
                PEFTMethod,
                PEFTSpec,
                TrainingBudgetSpec,
                TrainingDatasetSpec,
            )
            from oec.foundation.errors import (
                BitsAndBytesNotAvailableError,
                PeftNotAvailableError,
                TransformersNotAvailableError,
            )
            from oec.foundation.runtime import peft_train
        except Exception as exc:  # pragma: no cover - import graph always present
            raise BackendNotAvailableError(str(exc)) from exc

        method_map = {
            TrainingMethod.LORA: PEFTMethod.LORA,
            TrainingMethod.QLORA: PEFTMethod.QLORA,
            TrainingMethod.FULL: PEFTMethod.NONE,
            TrainingMethod.SFT: PEFTMethod.LORA,
        }
        if config.method not in method_map:
            raise BackendNotAvailableError(
                f"huggingface backend does not implement {config.method.value}",
                details={"method": config.method.value},
            )
        texts = texts_from_sft(dataset)
        spec = PEFTSpec(
            method=method_map[config.method],
            model=FoundationModelSpec(model_id=model.model_id, revision=model.revision),
            dataset=TrainingDatasetSpec(texts=texts),
            budget=TrainingBudgetSpec(
                max_steps=min(config.max_steps, 500),
                max_seq_len=min(config.max_seq_len, 1024),
                batch_size=min(config.batch_size, 32),
            ),
            target_modules=("c_attn", "c_proj"),
            seed=config.seed,
        )
        try:
            raw: dict[str, Any] = peft_train(spec)
        except (
            TransformersNotAvailableError,
            PeftNotAvailableError,
            BitsAndBytesNotAvailableError,
        ) as exc:
            raise BackendNotAvailableError(
                str(exc),
                details={"backend": "huggingface", "error_type": type(exc).__name__},
            ) from exc

        raw_artifact = raw.get("artifact")
        artifact: dict[str, Any] = raw_artifact if isinstance(raw_artifact, dict) else {}
        art = ArtifactRef(
            kind=str(artifact.get("kind") or "adapter"),
            path=artifact.get("path") if isinstance(artifact.get("path"), str) else None,
            sha256=artifact.get("sha256") if isinstance(artifact.get("sha256"), str) else None,
            base_model_id=model.model_id,
            revision=model.revision,
        )
        metrics: dict[str, float] = {}
        if isinstance(raw.get("final_loss"), (int, float)):
            metrics["loss"] = float(raw["final_loss"])
        history = raw.get("loss_history")
        if not metrics and isinstance(history, list) and history:
            last = history[-1]
            if isinstance(last, (int, float)):
                metrics["loss"] = float(last)
        return TrainingResult(
            status="ok",
            backend=FineTuneBackendName.HUGGINGFACE,
            method=config.method,
            model=model,
            artifact=art,
            metrics=metrics,
            message="huggingface peft_train",
            details={"backend_merit": "transformers+peft"},
        )
