"""Foundation runtime — builtin utilities + optional transformers (W6).

``builtin_hash`` embeddings are **OEC-owned** deterministic vectors for
reproducible experiments without network/model downloads. They are **not**
a language-model merit claim.

``transformers`` paths require ``oec[foundation]`` and fail closed when absent.
"""

from __future__ import annotations

import hashlib
import math
import struct
from typing import Any

from oec.foundation.contracts import (
    EmbeddingBackend,
    EmbeddingSpec,
    GenerationBackend,
    GenerationSpec,
)
from oec.foundation.errors import FoundationError, TransformersNotAvailableError


def probe_transformers() -> tuple[bool, str | None, str | None]:
    try:
        import transformers  # noqa: F401
    except ImportError as exc:
        return False, None, str(exc)
    try:
        import importlib.metadata

        version = importlib.metadata.version("transformers")
    except Exception:
        version = None
    return True, version, None


def foundation_capabilities() -> dict[str, Any]:
    avail, version, reason = probe_transformers()
    return {
        "transformers_available": avail,
        "transformers_version": version,
        "reason": reason,
        "embedding_backends": [b.value for b in EmbeddingBackend],
        "generation_backends": [b.value for b in GenerationBackend],
        "notes": [
            "builtin_hash is OEC-owned deterministic embedding, not an LLM",
            "transformers methods require oec[foundation] and may download models",
        ],
    }


def _hash_vector(text: str, *, dim: int, seed: int, normalize: bool) -> list[float]:
    """Deterministic pseudo-embedding from SHA-256 expanded to ``dim`` floats."""
    vec: list[float] = []
    counter = 0
    while len(vec) < dim:
        h = hashlib.sha256(f"{seed}:{counter}:{text}".encode()).digest()
        for i in range(0, len(h) - 3, 4):
            # map uint32 → [-1, 1]
            u = struct.unpack_from(">I", h, i)[0]
            vec.append((u / 0xFFFFFFFF) * 2.0 - 1.0)
            if len(vec) >= dim:
                break
        counter += 1
    if normalize:
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        vec = [v / norm for v in vec]
    return vec[:dim]


def embed_texts(spec: EmbeddingSpec) -> dict[str, Any]:
    if not spec.texts:
        raise FoundationError("texts must be non-empty")
    if spec.backend == EmbeddingBackend.BUILTIN_HASH:
        vectors = [
            _hash_vector(t, dim=spec.dim, seed=spec.seed, normalize=spec.normalize)
            for t in spec.texts
        ]
        return {
            "backend": "builtin_hash",
            "backend_version": None,
            "model_id": None,
            "dim": spec.dim,
            "n": len(vectors),
            "vectors": vectors,
            "normalized": spec.normalize,
            "seed": spec.seed,
            "merit_owner": "oec",
            "message": "deterministic hash embedding (not a foundation model)",
        }

    if spec.backend == EmbeddingBackend.TRANSFORMERS:
        avail, version, reason = probe_transformers()
        if not avail:
            raise TransformersNotAvailableError(details={"reason": reason})
        # Minimal path: mean-pool last hidden states via AutoModel
        model_id = spec.model.model_id if spec.model is not None else "sshleifer/tiny-gpt2"
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise TransformersNotAvailableError(details={"reason": str(exc)}) from exc

        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModel.from_pretrained(model_id)
        model.eval()
        tf_vectors: list[list[float]] = []
        with torch.no_grad():
            for text in spec.texts:
                enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
                out = model(**enc)
                hidden = out.last_hidden_state  # [1, T, H]
                pooled = hidden.mean(dim=1).squeeze(0)
                vec = pooled.tolist()
                if spec.normalize:
                    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
                    vec = [v / norm for v in vec]
                # truncate/pad to requested dim for contract stability
                if len(vec) < spec.dim:
                    vec = vec + [0.0] * (spec.dim - len(vec))
                tf_vectors.append(vec[: spec.dim])
        return {
            "backend": "transformers",
            "backend_version": version,
            "model_id": model_id,
            "dim": spec.dim,
            "n": len(tf_vectors),
            "vectors": tf_vectors,
            "normalized": spec.normalize,
            "seed": spec.seed,
            "merit_owner": "transformers",
            "message": "mean-pool AutoModel embeddings",
        }

    raise FoundationError(f"unsupported embedding backend {spec.backend!r}")


def generate_text(spec: GenerationSpec) -> dict[str, Any]:
    if spec.backend != GenerationBackend.TRANSFORMERS:
        raise FoundationError(f"unsupported generation backend {spec.backend!r}")
    avail, version, reason = probe_transformers()
    if not avail:
        raise TransformersNotAvailableError(details={"reason": reason})
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    except ImportError as exc:
        raise TransformersNotAvailableError(details={"reason": str(exc)}) from exc

    model_id = spec.model.model_id
    set_seed(int(spec.seed))
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id)
    model.eval()
    inputs = tokenizer(spec.prompt, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=int(spec.max_new_tokens),
            do_sample=spec.temperature > 0,
            temperature=max(float(spec.temperature), 1e-5) if spec.temperature > 0 else None,
        )
    text = tokenizer.decode(out[0], skip_special_tokens=True)
    return {
        "backend": "transformers",
        "backend_version": version,
        "model_id": model_id,
        "prompt": spec.prompt,
        "text": text,
        "max_new_tokens": spec.max_new_tokens,
        "seed": spec.seed,
        "merit_owner": "transformers",
        "message": "causal LM generation",
    }
