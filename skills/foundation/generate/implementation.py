"""foundation.generate — transformers causal LM (optional extra)."""

from __future__ import annotations

from typing import Any

from oec.foundation.contracts import FoundationModelSpec, GenerationSpec
from oec.foundation.errors import (
    AdapterNotFoundError,
    PeftNotAvailableError,
    TransformersNotAvailableError,
)
from oec.foundation.runtime import generate_text


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    adapter_path = inputs.get("adapter_path")
    spec = GenerationSpec(
        prompt=str(inputs["prompt"]),
        max_new_tokens=int(inputs.get("max_new_tokens", 16)),
        model=FoundationModelSpec(model_id=str(inputs.get("model_id", "sshleifer/tiny-gpt2"))),
        temperature=float(inputs.get("temperature", 0.0)),
        seed=int(inputs.get("seed", 0)),
        adapter_path=str(adapter_path) if adapter_path else None,
    )
    try:
        out = generate_text(spec)
    except (TransformersNotAvailableError, PeftNotAvailableError, AdapterNotFoundError) as exc:
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
