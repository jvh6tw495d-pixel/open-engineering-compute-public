"""foundation.vllm_generate — remote OpenAI-compatible client (ADR 0046)."""

from __future__ import annotations

from typing import Any

from oec.foundation.contracts import VllmGenerateSpec
from oec.foundation.errors import VllmUnreachableError
from oec.foundation.vllm import run_vllm_generate


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        spec = VllmGenerateSpec(
            base_url=str(inputs["base_url"]),
            model_id=str(inputs["model_id"]),
            prompt=str(inputs["prompt"]),
            max_new_tokens=int(inputs.get("max_new_tokens", 32)),
            temperature=float(inputs.get("temperature", 0.0)),
            seed=inputs.get("seed"),
        )
        payload = run_vllm_generate(spec)
    except (VllmUnreachableError, ValueError) as exc:
        message = getattr(exc, "message", str(exc))
        error = exc.to_dict() if isinstance(exc, VllmUnreachableError) else {"message": message}
        return {
            "result": {"error": error},
            "diagnostics": {
                "converged": False,
                "message": message,
                "backend": "vllm",
            },
        }
    return {
        "result": payload,
        "diagnostics": {
            "converged": True,
            "backend": "vllm",
            "model_id": payload.get("model_id"),
        },
    }
