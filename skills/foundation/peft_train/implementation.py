"""foundation.peft_train — LoRA/QLoRA/full fine-tune (S1, optional extra)."""

from __future__ import annotations

from typing import Any

from oec.foundation.contracts import (
    FoundationModelSpec,
    PEFTMethod,
    PEFTSpec,
    TrainingBudgetSpec,
    TrainingDatasetSpec,
)
from oec.foundation.errors import (
    BitsAndBytesNotAvailableError,
    FoundationError,
    PeftNotAvailableError,
    TransformersNotAvailableError,
)
from oec.foundation.runtime import peft_train

_MODE_TO_METHOD = {
    "peft_lora": PEFTMethod.LORA,
    "peft_qlora": PEFTMethod.QLORA,
    "full": PEFTMethod.NONE,
}


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    mode = str(inputs.get("mode", "peft_lora"))
    method = _MODE_TO_METHOD[mode]

    dataset_kwargs: dict[str, Any] = {}
    if inputs.get("texts") is not None:
        dataset_kwargs["texts"] = tuple(inputs["texts"])
    if inputs.get("dataset_path") is not None:
        dataset_kwargs["local_path"] = str(inputs["dataset_path"])

    spec = PEFTSpec(
        method=method,
        model=FoundationModelSpec(
            model_id=str(inputs.get("model_id", "sshleifer/tiny-gpt2")),
            revision=str(inputs["revision"]) if inputs.get("revision") else None,
        ),
        dataset=TrainingDatasetSpec(**dataset_kwargs),
        budget=TrainingBudgetSpec(
            max_steps=int(inputs.get("max_steps", 5)),
            max_seq_len=int(inputs.get("max_seq_len", 64)),
            batch_size=int(inputs.get("batch_size", 2)),
        ),
        r=int(inputs.get("r", 8)),
        lora_alpha=int(inputs.get("lora_alpha", 16)),
        lora_dropout=float(inputs.get("lora_dropout", 0.05)),
        target_modules=tuple(inputs.get("target_modules", ["q_proj", "v_proj"])),
        seed=int(inputs.get("seed", 0)),
    )

    try:
        out = peft_train(spec, artifact_root=inputs.get("artifact_root"))
    except (
        TransformersNotAvailableError,
        PeftNotAvailableError,
        BitsAndBytesNotAvailableError,
    ) as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "transformers",
                "mode": mode,
            },
        }
    except FoundationError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "message": exc.message, "mode": mode},
        }

    return {
        "result": out,
        "diagnostics": {
            "converged": True,
            "backend": out["backend"],
            "model_id": out["model_id"],
            "mode": mode,
            "steps_run": out["steps_run"],
            "final_loss": out["final_loss"],
            "artifact_kind": out["artifact"]["kind"],
        },
    }
