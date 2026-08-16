"""L7 optional Unsloth SFT/LoRA adapter (integration-unverified)."""

from __future__ import annotations

import importlib

from oec.learning.contracts import FineTuneBackendName, ModelRef, TrainingConfig, TrainingResult
from oec.learning.datasets import LearningDataset, texts_from_sft
from oec.learning.errors import BackendNotAvailableError

_NOT_WIRED = "adapter not wired to this unsloth version"


def _require_module(name: str) -> object:
    try:
        return importlib.import_module(name)
    except Exception as exc:
        raise BackendNotAvailableError(
            f"{name} is required for the Unsloth adapter",
            details={"backend": "unsloth", "missing": name, "error_type": type(exc).__name__},
        ) from exc


class UnslothBackend:
    name = FineTuneBackendName.UNSLOTH

    def finetune(
        self, model: ModelRef, dataset: LearningDataset, config: TrainingConfig
    ) -> TrainingResult:
        unsloth = _require_module("unsloth")
        fast_language_model = getattr(unsloth, "FastLanguageModel", None)
        if fast_language_model is None:
            raise BackendNotAvailableError(
                _NOT_WIRED,
                details={"backend": "unsloth", "missing": "FastLanguageModel"},
            )
        _require_module("datasets")
        _require_module("transformers")
        _require_module("trl")

        try:
            from datasets import Dataset
            from transformers import TrainingArguments
            from trl import SFTTrainer

            texts = texts_from_sft(dataset)
            loaded_model, tokenizer = fast_language_model.from_pretrained(
                model_name=model.model_id,
                max_seq_length=config.max_seq_len,
                load_in_4bit=bool(config.hyperparameters.get("load_in_4bit", True)),
            )
            lora_model = fast_language_model.get_peft_model(
                loaded_model,
                r=int(config.hyperparameters.get("lora_r", 16)),
                target_modules=(
                    "q_proj",
                    "k_proj",
                    "v_proj",
                    "o_proj",
                    "gate_proj",
                    "up_proj",
                    "down_proj",
                ),
                lora_alpha=int(config.hyperparameters.get("lora_alpha", 16)),
                lora_dropout=0,
                bias="none",
                use_gradient_checkpointing="unsloth",
                random_state=config.seed,
            )
            trainer = SFTTrainer(
                model=lora_model,
                tokenizer=tokenizer,
                train_dataset=Dataset.from_list([{"text": text} for text in texts]),
                dataset_text_field="text",
                max_seq_length=config.max_seq_len,
                args=TrainingArguments(
                    output_dir=str(config.hyperparameters.get("output_dir", "unsloth-output")),
                    per_device_train_batch_size=config.batch_size,
                    max_steps=config.max_steps,
                    seed=config.seed,
                    report_to="none",
                ),
            )
            outcome = trainer.train()
            loss = getattr(outcome, "training_loss", None)
            return TrainingResult(
                status="ok",
                backend=self.name,
                method=config.method,
                model=model,
                metrics={"loss": float(loss)} if isinstance(loss, (int, float)) else {},
                message="unsloth FastLanguageModel SFT/LoRA",
                details={"adapter": "FastLanguageModel", "dataset_records": len(texts)},
            )
        except BackendNotAvailableError:
            raise
        except Exception as exc:
            if config.hyperparameters.get("allow_hf_fallback") == "1":
                from oec.learning.backends.huggingface import HuggingFaceBackend

                extras = dict(config.hyperparameters)
                if config.method.value == "sft":
                    extras["sft_via_lora"] = "1"
                fallback = config.model_copy(
                    update={"backend": FineTuneBackendName.HUGGINGFACE, "hyperparameters": extras}
                )
                return HuggingFaceBackend().finetune(model, dataset, fallback)
            raise BackendNotAvailableError(
                _NOT_WIRED,
                details={"backend": "unsloth", "error_type": type(exc).__name__},
            ) from exc
