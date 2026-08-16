"""Foundation runtime — builtin utilities + optional transformers (W6 / S5).

``builtin_hash`` embeddings are **OEC-owned** deterministic vectors for
reproducible experiments without network/model downloads. They are **not**
a language-model merit claim.

``transformers`` paths require ``oec[foundation]`` and fail closed when absent.
S5 vision / VLM paths additionally require Pillow for image decode and pin
remote models with an immutable ``revision`` (or local-only paths).
"""

from __future__ import annotations

import base64
import hashlib
import io
import math
import os
import struct
from pathlib import Path
from typing import Any

from oec.foundation.contracts import (
    ALLOWED_IMAGE_EXTENSIONS,
    MAX_IMAGE_BYTES,
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_FRAMES,
    MAX_IMAGE_PIXELS,
    ArtifactKind,
    EmbeddingBackend,
    EmbeddingSpec,
    FoundationModelSpec,
    GenerationBackend,
    GenerationSpec,
    PEFTMethod,
    PEFTSpec,
    TrainingDatasetSpec,
    VisionBackend,
    VisionEmbeddingSpec,
    VisionImageInput,
    VLMGenerationSpec,
    require_pinned_or_local_model,
)
from oec.foundation.errors import (
    AdapterNotFoundError,
    BitsAndBytesNotAvailableError,
    FoundationError,
    InvalidImageSourceError,
    ModelRevisionRequiredError,
    PeftNotAvailableError,
    PillowNotAvailableError,
    TransformersNotAvailableError,
    UnsupportedVisionModelError,
)

# Closed allow-lists for S5 — never silently accept text-only stand-ins.
_VISION_EMBED_MODEL_TYPES: frozenset[str] = frozenset({"clip", "chinese_clip", "siglip"})
_VLM_GENERATE_MODEL_TYPES: frozenset[str] = frozenset(
    {
        "blip",
        "blip-2",
        "blip_2",
        "git",
        "instructblip",
        "idefics",
        "idefics2",
        "idefics3",
        "llava",
        "paligemma",
        "vision-encoder-decoder",
    }
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


def probe_pillow() -> tuple[bool, str | None, str | None]:
    try:
        import PIL  # noqa: F401
    except ImportError as exc:
        return False, None, str(exc)
    try:
        import importlib.metadata

        version = importlib.metadata.version("pillow")
    except Exception:
        version = None
    return True, version, None


def foundation_capabilities() -> dict[str, Any]:
    avail, version, reason = probe_transformers()
    peft_avail, peft_version, peft_reason = probe_peft()
    pillow_avail, pillow_version, pillow_reason = probe_pillow()
    return {
        "transformers_available": avail,
        "transformers_version": version,
        "reason": reason,
        "peft_available": peft_avail,
        "peft_version": peft_version,
        "peft_reason": peft_reason,
        "pillow_available": pillow_avail,
        "pillow_version": pillow_version,
        "pillow_reason": pillow_reason,
        "embedding_backends": [b.value for b in EmbeddingBackend],
        "generation_backends": [b.value for b in GenerationBackend],
        "vision_embed_backends": [VisionBackend.TRANSFORMERS.value],
        "vlm_generate_backends": [VisionBackend.TRANSFORMERS.value],
        "training_methods": [m.value for m in PEFTMethod],
        "notes": [
            "builtin_hash is OEC-owned deterministic embedding, not an LLM",
            "transformers methods require oec[foundation] and may download models",
            "peft_train lora/qlora require peft; qlora additionally requires bitsandbytes",
            "vision_embed / vlm_generate require transformers + pillow; "
            "remote models need revision",
        ],
    }


def pretrained_load_kwargs(model: FoundationModelSpec) -> dict[str, Any]:
    """Build fail-closed kwargs for every Transformers ``from_pretrained`` call.

    ``trust_remote_code`` is always disabled. Every remote Hub load receives an
    immutable 40-hex commit revision; local paths remain the explicit local-only
    mode and may omit a revision.
    """
    try:
        require_pinned_or_local_model(model)
    except ValueError as exc:
        raise ModelRevisionRequiredError(
            str(exc), details={"model_id": model.model_id, "revision": model.revision}
        ) from exc

    kwargs: dict[str, Any] = {"trust_remote_code": False}
    if model.revision is not None and str(model.revision).strip():
        kwargs["revision"] = str(model.revision).strip()
    return kwargs


def from_pretrained_governed(factory: Any, model_id: str, load_kwargs: dict[str, Any]) -> Any:
    """Hub/local load with an explicit ``revision=`` keyword for Bandit B615.

    Remote models always carry a 40-hex revision from
    :func:`pretrained_load_kwargs`. Local paths may omit it.
    """
    revision = load_kwargs.get("revision")
    other = {key: value for key, value in load_kwargs.items() if key != "revision"}
    return factory.from_pretrained(model_id, revision=revision, **other)


def _validate_image_metadata(image: Any) -> None:
    """Reject oversized or animated inputs before pixel decoding/conversion."""
    width, height = image.size
    pixels = width * height
    frames = int(getattr(image, "n_frames", 1))
    details = {
        "stage": "metadata",
        "width": width,
        "height": height,
        "pixels": pixels,
        "frames": frames,
        "max_dimension": MAX_IMAGE_DIMENSION,
        "max_pixels": MAX_IMAGE_PIXELS,
        "max_frames": MAX_IMAGE_FRAMES,
    }
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise InvalidImageSourceError("image dimensions exceed configured limit", details=details)
    if pixels > MAX_IMAGE_PIXELS:
        raise InvalidImageSourceError("image pixel count exceeds configured limit", details=details)
    if frames > MAX_IMAGE_FRAMES:
        raise InvalidImageSourceError("image frame count exceeds configured limit", details=details)


def _decode_opened_image(image: Any) -> Any:
    _validate_image_metadata(image)
    image.load()
    return image.convert("RGB")


def load_vision_image(source: VisionImageInput) -> Any:
    """Decode one bounded local/base64 image without URL fetches.

    Pillow's decompression-bomb warning/error is promoted to the public,
    structured ``InvalidImageSourceError`` contract before any full decode.
    """
    avail, _version, reason = probe_pillow()
    if not avail:
        raise PillowNotAvailableError(details={"reason": reason})
    try:
        from PIL import Image
    except ImportError as exc:
        raise PillowNotAvailableError(details={"reason": str(exc)}) from exc

    import warnings

    def open_and_decode(input_: Any) -> Any:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(input_) as image:
                    return _decode_opened_image(image)
        except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
            raise InvalidImageSourceError(
                "Pillow rejected image as a decompression bomb",
                details={"stage": "metadata", "reason": str(exc)},
            ) from exc
        except InvalidImageSourceError:
            raise
        except Exception as exc:
            raise InvalidImageSourceError(
                "failed to decode image bytes", details={"reason": str(exc)}
            ) from exc

    if source.image_path is not None:
        path = Path(source.image_path)
        if not path.is_file():
            raise InvalidImageSourceError(
                "image_path is not an existing file", details={"image_path": str(path)}
            )
        suffix = path.suffix.lower()
        if suffix not in ALLOWED_IMAGE_EXTENSIONS:
            raise InvalidImageSourceError(
                f"disallowed image extension {suffix!r}",
                details={"image_path": str(path), "suffix": suffix},
            )
        size = path.stat().st_size
        if size > MAX_IMAGE_BYTES:
            raise InvalidImageSourceError(
                f"image exceeds max size of {MAX_IMAGE_BYTES} bytes",
                details={"image_path": str(path), "size": size},
            )
        return open_and_decode(path)

    assert source.image_base64 is not None
    try:
        raw = base64.b64decode(source.image_base64, validate=True)
    except Exception as exc:
        raise InvalidImageSourceError(
            "image_base64 is not valid base64", details={"reason": str(exc)}
        ) from exc
    if len(raw) > MAX_IMAGE_BYTES:
        raise InvalidImageSourceError(
            f"image exceeds max size of {MAX_IMAGE_BYTES} bytes", details={"size": len(raw)}
        )
    return open_and_decode(io.BytesIO(raw))


def _require_transformers() -> tuple[str | None, None]:
    avail, version, reason = probe_transformers()
    if not avail:
        raise TransformersNotAvailableError(details={"reason": reason})
    return version, None


def vision_embed(spec: VisionEmbeddingSpec) -> dict[str, Any]:
    """Embed images with a closed Transformers vision model (CLIP family).

    Fail-closed: missing extra, missing Pillow, unsupported architecture, or
    unloadable processor/model. Never substitutes a text-only embedder.
    """
    if spec.backend != VisionBackend.TRANSFORMERS:
        raise FoundationError(f"unsupported vision embedding backend {spec.backend!r}")
    version, _ = _require_transformers()
    load_kwargs = pretrained_load_kwargs(spec.model)
    model_id = spec.model.model_id

    try:
        from transformers import AutoConfig, CLIPModel, CLIPProcessor
    except ImportError as exc:
        raise TransformersNotAvailableError(details={"reason": str(exc)}) from exc

    try:
        config = from_pretrained_governed(AutoConfig, model_id, load_kwargs)
    except Exception as exc:
        raise UnsupportedVisionModelError(
            "failed to load vision model config",
            details={"model_id": model_id, "reason": str(exc)},
        ) from exc

    model_type = str(getattr(config, "model_type", "") or "").lower()
    if model_type not in _VISION_EMBED_MODEL_TYPES:
        raise UnsupportedVisionModelError(
            f"model_type {model_type!r} is not a supported vision embedding architecture",
            details={
                "model_id": model_id,
                "model_type": model_type,
                "allowed": sorted(_VISION_EMBED_MODEL_TYPES),
            },
        )

    images = [load_vision_image(src) for src in spec.images]

    try:
        processor: Any = from_pretrained_governed(CLIPProcessor, model_id, load_kwargs)
        model: Any = from_pretrained_governed(CLIPModel, model_id, load_kwargs)
    except Exception as exc:
        raise UnsupportedVisionModelError(
            "failed to load CLIP model/processor (no text-only fallback)",
            details={"model_id": model_id, "reason": str(exc)},
        ) from exc

    model.eval()
    try:
        import torch
    except ImportError as exc:
        raise TransformersNotAvailableError(details={"reason": str(exc)}) from exc

    vectors: list[list[float]] = []
    with torch.no_grad():
        for image in images:
            inputs = processor(images=image, return_tensors="pt")
            feats = model.get_image_features(**inputs)
            # Transformers 4.x returns a tensor here; Transformers 5.x returns
            # BaseModelOutputWithPooling. In both supported forms the pooled
            # image feature is the vector exposed to the skill contract.
            if not hasattr(feats, "squeeze"):
                feats = feats.pooler_output
            vec = feats.squeeze(0).tolist()
            if isinstance(vec[0], list):  # unlikely nested
                vec = vec[0]
            if spec.normalize:
                norm = math.sqrt(sum(float(v) * float(v) for v in vec)) or 1.0
                vec = [float(v) / norm for v in vec]
            else:
                vec = [float(v) for v in vec]
            if len(vec) < spec.dim:
                vec = vec + [0.0] * (spec.dim - len(vec))
            vectors.append(vec[: spec.dim])

    return {
        "backend": "transformers",
        "backend_version": version,
        "model_id": model_id,
        "revision": load_kwargs.get("revision"),
        "dim": spec.dim,
        "n": len(vectors),
        "vectors": vectors,
        "normalized": spec.normalize,
        "seed": spec.seed,
        "merit_owner": "transformers",
        "message": "CLIP image embedding (no text-only fallback)",
        "trust_remote_code": False,
    }


def vlm_generate(spec: VLMGenerationSpec) -> dict[str, Any]:
    """Vision-language generation via Transformers Vision2Seq path only.

    Fail-closed: never falls back to ``AutoModelForCausalLM`` / text-only.
    """
    if spec.backend != VisionBackend.TRANSFORMERS:
        raise FoundationError(f"unsupported VLM generation backend {spec.backend!r}")
    version, _ = _require_transformers()
    load_kwargs = pretrained_load_kwargs(spec.model)
    model_id = spec.model.model_id

    try:
        import transformers
        from transformers import AutoConfig, AutoProcessor, set_seed
    except ImportError as exc:
        raise TransformersNotAvailableError(details={"reason": str(exc)}) from exc

    try:
        config = from_pretrained_governed(AutoConfig, model_id, load_kwargs)
    except Exception as exc:
        raise UnsupportedVisionModelError(
            "failed to load VLM model config",
            details={"model_id": model_id, "reason": str(exc)},
        ) from exc

    model_type = str(getattr(config, "model_type", "") or "").lower()
    # Some Vision2Seq models report nested types; allow exact + known families.
    if model_type not in _VLM_GENERATE_MODEL_TYPES and not any(
        model_type.startswith(prefix) for prefix in ("blip", "idefics", "llava", "git")
    ):
        raise UnsupportedVisionModelError(
            f"model_type {model_type!r} is not a supported VLM architecture",
            details={
                "model_id": model_id,
                "model_type": model_type,
                "allowed": sorted(_VLM_GENERATE_MODEL_TYPES),
            },
        )

    image = load_vision_image(spec.image)

    try:
        processor_factory: Any = AutoProcessor
        processor: Any = from_pretrained_governed(processor_factory, model_id, load_kwargs)
        transformers_module: Any = transformers
        vision_model_factory: Any = transformers_module.AutoModelForVision2Seq
        model: Any = from_pretrained_governed(vision_model_factory, model_id, load_kwargs)
    except Exception as exc:
        raise UnsupportedVisionModelError(
            "failed to load Vision2Seq model/processor (no text-only fallback)",
            details={"model_id": model_id, "reason": str(exc)},
        ) from exc

    set_seed(int(spec.seed))
    model.eval()
    try:
        import torch
    except ImportError as exc:
        raise TransformersNotAvailableError(details={"reason": str(exc)}) from exc

    try:
        inputs = processor(images=image, text=spec.prompt, return_tensors="pt")
    except TypeError:
        # Some processors use `text` vs prompt keyword differences — fail closed
        # rather than guessing a text-only path.
        try:
            inputs = processor(image, spec.prompt, return_tensors="pt")
        except Exception as exc:
            raise UnsupportedVisionModelError(
                "processor rejected image+text inputs",
                details={"model_id": model_id, "reason": str(exc)},
            ) from exc
    except Exception as exc:
        raise UnsupportedVisionModelError(
            "processor rejected image+text inputs",
            details={"model_id": model_id, "reason": str(exc)},
        ) from exc

    gen_kwargs: dict[str, Any] = {"max_new_tokens": int(spec.max_new_tokens)}
    if spec.temperature > 0:
        gen_kwargs["do_sample"] = True
        gen_kwargs["temperature"] = float(spec.temperature)
    else:
        gen_kwargs["do_sample"] = False

    with torch.no_grad():
        out = model.generate(**inputs, **gen_kwargs)

    try:
        text = processor.batch_decode(out, skip_special_tokens=True)[0]
    except Exception:
        text = str(out)

    return {
        "backend": "transformers",
        "backend_version": version,
        "model_id": model_id,
        "revision": load_kwargs.get("revision"),
        "prompt": spec.prompt,
        "text": text,
        "max_new_tokens": spec.max_new_tokens,
        "seed": spec.seed,
        "merit_owner": "transformers",
        "message": "vision-language generation (Vision2Seq only)",
        "trust_remote_code": False,
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
        # Minimal path: mean-pool last hidden states via AutoModel.
        model_ref = spec.model or FoundationModelSpec(
            model_id="sshleifer/tiny-gpt2",
            revision="5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be",
        )
        model_id = model_ref.model_id
        load_kwargs = pretrained_load_kwargs(model_ref)
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise TransformersNotAvailableError(details={"reason": str(exc)}) from exc

        tokenizer = from_pretrained_governed(AutoTokenizer, model_id, load_kwargs)
        model = from_pretrained_governed(AutoModel, model_id, load_kwargs)
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
    load_kwargs = pretrained_load_kwargs(spec.model)
    set_seed(int(spec.seed))
    tokenizer = from_pretrained_governed(AutoTokenizer, model_id, load_kwargs)
    model: Any = from_pretrained_governed(AutoModelForCausalLM, model_id, load_kwargs)

    adapter_info: dict[str, Any] | None = None
    if spec.adapter_path:
        adapter_dir = Path(spec.adapter_path)
        if not adapter_dir.is_dir():
            raise AdapterNotFoundError(details={"adapter_path": str(adapter_dir)})
        try:
            from peft import PeftModel
        except ImportError as exc:
            raise PeftNotAvailableError(details={"reason": str(exc)}) from exc
        model = PeftModel.from_pretrained(model, str(adapter_dir))  # nosec B615 — local adapter dir
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
    load_kwargs = pretrained_load_kwargs(spec.model)
    set_seed(int(spec.seed))
    tokenizer = from_pretrained_governed(AutoTokenizer, model_id, load_kwargs)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model: Any = from_pretrained_governed(AutoModelForCausalLM, model_id, load_kwargs)

    kind = ArtifactKind.CHECKPOINT
    if spec.adapter_path:
        if spec.method is PEFTMethod.NONE:
            raise ValueError("adapter_path cannot be combined with full fine-tune")
        adapter_dir = Path(spec.adapter_path)
        if not adapter_dir.is_dir():
            raise AdapterNotFoundError(details={"adapter_path": str(adapter_dir)})
        try:
            from peft import PeftModel
        except ImportError as exc:
            raise PeftNotAvailableError(details={"reason": str(exc)}) from exc
        model = PeftModel.from_pretrained(model, str(adapter_dir))  # nosec B615
        kind = ArtifactKind.ADAPTER
    elif spec.method in (PEFTMethod.LORA, PEFTMethod.QLORA):
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
