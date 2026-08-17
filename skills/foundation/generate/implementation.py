"""foundation.generate — transformers causal LM (optional extra)."""

from __future__ import annotations

from typing import Any

from oec.foundation.contracts import FoundationModelSpec, GenerationSpec
from oec.foundation.errors import (
    AdapterNotFoundError,
    FoundationError,
    PeftNotAvailableError,
    TransformersNotAvailableError,
)
from oec.foundation.runtime import generate_text


def _remote_revision_from_inputs(inputs: dict[str, Any], model_id: str) -> str | None:
    if inputs.get("revision"):
        return str(inputs["revision"])
    if model_id == "sshleifer/tiny-gpt2":
        return "5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be"
    return None


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    adapter_path = inputs.get("adapter_path")
    model_id = str(inputs.get("model_id", "sshleifer/tiny-gpt2"))
    spec = GenerationSpec(
        prompt=str(inputs["prompt"]),
        max_new_tokens=int(inputs.get("max_new_tokens", 16)),
        model=FoundationModelSpec(
            model_id=model_id,
            revision=_remote_revision_from_inputs(inputs, model_id),
        ),
        temperature=float(inputs.get("temperature", 0.0)),
        seed=int(inputs.get("seed", 0)),
        adapter_path=str(adapter_path) if adapter_path else None,
        adapter_sha256=str(inputs["adapter_sha256"]) if inputs.get("adapter_sha256") else None,
    )
    try:
        out = generate_text(spec)
    except (
        TransformersNotAvailableError,
        PeftNotAvailableError,
        AdapterNotFoundError,
        FoundationError,
    ) as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "transformers",
            },
        }
    except Exception as exc:  # model download / runtime errors
        return {
            "result": {"error": {"type": type(exc).__name__, "message": str(exc)}},
            "diagnostics": {
                "converged": False,
                "message": str(exc),
                "backend": "transformers",
            },
        }
    return {
        "result": out,
        "diagnostics": {
            "converged": True,
            "backend": out["backend"],
            "model_id": out["model_id"],
            "merit_owner": out.get("merit_owner"),
        },
    }
