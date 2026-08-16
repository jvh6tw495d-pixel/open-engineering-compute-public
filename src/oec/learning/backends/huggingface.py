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
from oec.learning.install_hints import HF_MISSING

_LLAMA_TARGETS = ("q_proj", "v_proj")
_GPT2_TARGETS = ("c_attn", "c_proj")
_OK_RUNTIME = frozenset({"ok", "success", "completed"})
_LLAMA_MARKERS = ("llama", "mistral", "qwen", "phi", "gemma", "tinyllama")


def _target_modules(model: ModelRef, config: TrainingConfig) -> tuple[str, ...]:
    raw = config.hyperparameters.get("target_modules")
    if isinstance(raw, str) and raw.strip():
        parts = tuple(item.strip() for item in raw.split(",") if item.strip())
        if parts:
            return parts
    model_id = model.model_id.lower()
    if "gpt2" in model_id or "gpt-2" in model_id:
        return _GPT2_TARGETS
    if any(marker in model_id for marker in _LLAMA_MARKERS):
        return _LLAMA_TARGETS
    raise BackendNotAvailableError(
        "huggingface target_modules must be set for unknown model families",
        details={"model_id": model.model_id},
    )


class HuggingFaceBackend:
    """Reference FineTune backend. Delegates to ``oec.foundation.peft_train``."""

    name = FineTuneBackendName.HUGGINGFACE

    def finetune(
        self,
        model: ModelRef,
        dataset: LearningDataset,
        config: TrainingConfig,
    ) -> TrainingResult:
        mapped_from: str | None = None
        method = config.method
        if method is TrainingMethod.SFT:
            if str(config.hyperparameters.get("sft_via_lora")) != "1":
                raise BackendNotAvailableError(
                    "huggingface SFT requires hyperparameters sft_via_lora=1 "
                    "(explicit LoRA mapping); otherwise use method=lora",
                    details={"method": method.value},
                )
            mapped_from = "sft"
        elif method not in {
            TrainingMethod.LORA,
            TrainingMethod.QLORA,
            TrainingMethod.FULL,
        }:
            raise BackendNotAvailableError(
                f"huggingface backend does not implement {method.value}",
                details={"method": method.value},
            )

        try:
            from oec.foundation.contracts import (
                FoundationModelSpec,
                PEFTMethod,
                PEFTSpec,
                TrainingBudgetSpec,
                TrainingDatasetSpec,
            )
            from oec.foundation.errors import (
                AdapterNotFoundError,
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
        method_map_value = method_map[method]
        texts = texts_from_sft(dataset)
        adapter_path = config.hyperparameters.get("adapter_path")
        adapter = adapter_path if isinstance(adapter_path, str) and adapter_path else None
        if adapter:
            from pathlib import Path as AdapterPath

            adapter_dir = AdapterPath(adapter)
            if not adapter_dir.is_dir():
                raise BackendNotAvailableError(
                    "adapter_path is not a local directory",
                    details={"adapter_path": adapter},
                )
            expected = config.hyperparameters.get("adapter_sha256")
            if isinstance(expected, str) and expected:
                from oec.foundation.runtime import _sha256_dir

                actual = _sha256_dir(adapter_dir)
                if actual != expected:
                    raise BackendNotAvailableError(
                        "adapter sha256 does not match chained artifact",
                        details={"expected": expected, "got": actual},
                    )
        targets = _target_modules(model, config)
        spec = PEFTSpec(
            method=method_map_value,
            model=FoundationModelSpec(model_id=model.model_id, revision=model.revision),
            dataset=TrainingDatasetSpec(texts=texts),
            budget=TrainingBudgetSpec(
                max_steps=min(config.max_steps, 500),
                max_seq_len=min(config.max_seq_len, 1024),
                batch_size=min(config.batch_size, 32),
            ),
            target_modules=targets,
            seed=config.seed,
            adapter_path=adapter,
        )
        try:
            raw: dict[str, Any] = peft_train(spec)
        except (
            AdapterNotFoundError,
            TransformersNotAvailableError,
            PeftNotAvailableError,
            BitsAndBytesNotAvailableError,
        ) as exc:
            raise BackendNotAvailableError(
                f"{exc} {HF_MISSING}",
                details={"backend": "huggingface", "error_type": type(exc).__name__},
            ) from exc

        raw_status = str(raw.get("status") or "ok").lower()
        raw_artifact = raw.get("artifact")
        artifact = raw_artifact if isinstance(raw_artifact, dict) else {}
        path = artifact.get("path") if isinstance(artifact.get("path"), str) else None
        digest = artifact.get("sha256") if isinstance(artifact.get("sha256"), str) else None
        art = None
        if path or digest:
            art = ArtifactRef(
                kind=str(artifact.get("kind") or "adapter"),
                path=path,
                sha256=digest,
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
        if raw_status not in _OK_RUNTIME:
            status = "error"
        elif art is None:
            status = "incomplete"
        else:
            status = "ok"
        details: dict[str, Any] = {
            "backend_merit": "transformers+peft",
            "target_modules": list(targets),
            "runtime_status": raw_status,
        }
        if mapped_from is not None:
            details["method_mapped_from"] = mapped_from
        if adapter:
            details["base_adapter_path"] = adapter
            details["continued_from_adapter"] = True
        return TrainingResult(
            status=status,
            backend=FineTuneBackendName.HUGGINGFACE,
            method=config.method,
            model=model,
            artifact=art,
            metrics=metrics,
            message="huggingface peft_train",
            details=details,
        )
