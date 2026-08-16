"""L7 optional Unsloth SFT/LoRA adapter."""

from __future__ import annotations

import importlib

from oec.learning.contracts import FineTuneBackendName, ModelRef, TrainingConfig, TrainingResult
from oec.learning.datasets import LearningDataset
from oec.learning.errors import BackendNotAvailableError

_NOT_WIRED = "adapter not wired to this unsloth version"


class UnslothBackend:
    name = FineTuneBackendName.UNSLOTH

    def finetune(
        self, model: ModelRef, dataset: LearningDataset, config: TrainingConfig
    ) -> TrainingResult:
        try:
            unsloth = importlib.import_module("unsloth")
        except Exception as exc:
            raise BackendNotAvailableError(
                "unsloth is not installed; L7 adapter is fail-closed",
                details={"backend": "unsloth", "error_type": type(exc).__name__},
            ) from exc

        # Public FastLanguageModel SFT/LoRA example path.  No version-specific
        # private APIs are guessed; the HF route is an explicit escape hatch.
        try:
            fast_language_model = vars(unsloth)["FastLanguageModel"]
            from datasets import Dataset
            from transformers import TrainingArguments  # type: ignore[import-not-found]
            from trl import SFTTrainer  # type: ignore[import-not-found]

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
                train_dataset=Dataset.from_list(list(dataset.records)),
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
                details={"adapter": "FastLanguageModel", "dataset_records": len(dataset.records)},
            )
        except Exception as exc:
            if config.hyperparameters.get("allow_hf_fallback") == "1":
                from oec.learning.backends.huggingface import HuggingFaceBackend

                return HuggingFaceBackend().finetune(model, dataset, config)
            raise BackendNotAvailableError(
                _NOT_WIRED,
                details={"backend": "unsloth", "error_type": type(exc).__name__},
            ) from exc
