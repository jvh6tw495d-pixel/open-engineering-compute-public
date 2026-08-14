"""foundation.embed — closed embedding backends (W6)."""

from __future__ import annotations

from typing import Any

from oec.foundation.contracts import EmbeddingBackend, EmbeddingSpec, FoundationModelSpec
from oec.foundation.errors import TransformersNotAvailableError
from oec.foundation.runtime import embed_texts


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    backend = EmbeddingBackend(str(inputs.get("backend", "builtin_hash")))
    model = None
    if inputs.get("model_id"):
        model = FoundationModelSpec(
            model_id=str(inputs["model_id"]),
            revision=str(inputs["revision"]) if inputs.get("revision") else None,
        )
    spec = EmbeddingSpec(
        backend=backend,
        texts=list(inputs["texts"]),
        dim=int(inputs.get("dim", 32)),
        model=model,
        normalize=bool(inputs.get("normalize", True)),
        seed=int(inputs.get("seed", 0)),
    )
    try:
        out = embed_texts(spec)
    except TransformersNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "transformers",
            },
        }
    return {
        "result": out,
        "diagnostics": {
            "backend": out["backend"],
            "dim": out["dim"],
            "n": out["n"],
            "merit_owner": out.get("merit_owner"),
        },
    }
