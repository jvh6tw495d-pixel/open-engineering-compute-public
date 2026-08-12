"""Foundation runtime — builtin utilities + optional transformers (W6).

``builtin_hash`` embeddings are **OEC-owned** deterministic vectors for
reproducible experiments without network/model downloads. They are **not**
a language-model merit claim.

``transformers`` paths require ``oec[foundation]`` and fail closed when absent.
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
from pathlib import Path
from typing import Any

from oec.foundation.contracts import (
    ArtifactKind,
    EmbeddingBackend,
    EmbeddingSpec,
    GenerationBackend,
    GenerationSpec,
    PEFTMethod,
    PEFTSpec,
    TrainingDatasetSpec,
)
from oec.foundation.errors import (
    AdapterNotFoundError,
    BitsAndBytesNotAvailableError,
    FoundationError,
    PeftNotAvailableError,
    TransformersNotAvailableError,
)


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


def probe_peft() -> tuple[bool, str | None, str | None]:
    try:
        import peft  # noqa: F401
    except ImportError as exc:
        return False, None, str(exc)
    try:
        import importlib.metadata

        version = importlib.metadata.version("peft")
    except Exception:
        version = None
    return True, version, None


def foundation_capabilities() -> dict[str, Any]:
    avail, version, reason = probe_transformers()
    peft_avail, peft_version, peft_reason = probe_peft()
    return {
        "transformers_available": avail,
        "transformers_version": version,
        "reason": reason,
        "peft_available": peft_avail,
        "peft_version": peft_version,
        "peft_reason": peft_reason,
        "embedding_backends": [b.value for b in EmbeddingBackend],
        "generation_backends": [b.value for b in GenerationBackend],
        "training_methods": [m.value for m in PEFTMethod],
        "notes": [
            "builtin_hash is OEC-owned deterministic embedding, not an LLM",
            "transformers methods require oec[foundation] and may download models",
            "peft_train lora/qlora require peft; qlora additionally requires bitsandbytes",
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

    adapter_info: dict[str, Any] | None = None
    if spec.adapter_path:
        adapter_dir = Path(spec.adapter_path)
        if not adapter_dir.is_dir():
            raise AdapterNotFoundError(details={"adapter_path": str(adapter_dir)})
        try:
            from peft import PeftModel
        except ImportError as exc:
            raise PeftNotAvailableError(details={"reason": str(exc)}) from exc
        model = PeftModel.from_pretrained(model, str(adapter_dir))
        adapter_info = {"path": str(adapter_dir.resolve())}

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
        "adapter": adapter_info,
        "merit_owner": "transformers",
        "message": "causal LM generation",
    }


def _prepare_training_texts(dataset: TrainingDatasetSpec) -> list[str]:
    if dataset.texts is not None:
        return list(dataset.texts)
    path = Path(dataset.local_path)  # type: ignore[arg-type]
    if not path.is_file():
        raise FoundationError(f"dataset local_path not found: {path}")
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise FoundationError(f"dataset local_path has no non-empty lines: {path}")
    return lines


def _default_peft_artifact_root() -> Path:
    env = os.environ.get("OEC_ARTIFACT_ROOT")
    root = Path(env) if env else Path.cwd() / ".oec" / "artifacts"
    return root / "foundation_peft"


def _sha256_dir(path: Path) -> str:
    """Deterministic hash of a saved model directory (sorted relative paths)."""
    digest = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(file.relative_to(path).as_posix().encode("utf-8"))
        digest.update(file.read_bytes())
    return digest.hexdigest()


def peft_train(spec: PEFTSpec, *, artifact_root: str | Path | None = None) -> dict[str, Any]:
    """Train a LoRA/QLoRA adapter or run a full fine-tune (ADR 0041 S1).

    Always saves the resulting adapter/checkpoint to disk and returns a
    machine-readable :class:`~oec.foundation.contracts.TrainingArtifact`-shaped
    descriptor with a content hash — never an in-memory-only result that
    can't be reloaded with provenance.
    """
    avail, version, reason = probe_transformers()
    if not avail:
        raise TransformersNotAvailableError(details={"reason": reason})
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    except ImportError as exc:
        raise TransformersNotAvailableError(details={"reason": str(exc)}) from exc

    texts = _prepare_training_texts(spec.dataset)
    model_id = spec.model.model_id
    set_seed(int(spec.seed))
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_id)

    kind = ArtifactKind.CHECKPOINT
    if spec.method in (PEFTMethod.LORA, PEFTMethod.QLORA):
        try:
            from peft import LoraConfig, get_peft_model
        except ImportError as exc:
            raise PeftNotAvailableError(details={"reason": str(exc)}) from exc
        if spec.method == PEFTMethod.QLORA:
            try:
                import bitsandbytes  # type: ignore[import-not-found]  # noqa: F401
            except ImportError as exc:
                raise BitsAndBytesNotAvailableError(details={"reason": str(exc)}) from exc
        lora_config = LoraConfig(
            r=spec.r,
            lora_alpha=spec.lora_alpha,
            lora_dropout=spec.lora_dropout,
            target_modules=list(spec.target_modules),
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lora_config)
        kind = ArtifactKind.ADAPTER

    model.train()
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=5e-4)
    batch_size = spec.budget.batch_size
    max_seq_len = spec.budget.max_seq_len
    n_texts = len(texts)
    losses: list[float] = []
    step = 0
    while step < spec.budget.max_steps:
        batch_texts = [texts[(step * batch_size + i) % n_texts] for i in range(batch_size)]
        encoded = tokenizer(
            batch_texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_seq_len,
        )
        labels = encoded["input_ids"].clone()
        labels[encoded["attention_mask"] == 0] = -100
        outputs = model(**encoded, labels=labels)
        loss = outputs.loss
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().item()))
        step += 1

    root = Path(artifact_root) if artifact_root is not None else _default_peft_artifact_root()
    run_dir = root / f"{model_id.replace('/', '_')}_{spec.method.value}_{spec.seed}_s{step}"
    run_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(run_dir)

    return {
        "backend": "transformers",
        "backend_version": version,
        "model_id": model_id,
        "method": spec.method.value,
        "artifact": {
            "schema_version": "0.1.0",
            "kind": kind.value,
            "path": str(run_dir.resolve()),
            "sha256": _sha256_dir(run_dir),
            "base_model_id": model_id,
            "revision": spec.model.revision,
        },
        "steps_run": step,
        "final_loss": losses[-1] if losses else None,
        "loss_history": losses,
        "seed": spec.seed,
        "merit_owner": "peft" if kind == ArtifactKind.ADAPTER else "transformers",
        "message": (
            "LoRA/QLoRA adapter trained"
            if kind == ArtifactKind.ADAPTER
            else "full fine-tune checkpoint saved"
        ),
    }
