"""S5 VLM MVP contracts — fail-closed image + revision rules (no model download)."""

from __future__ import annotations

import base64
import struct
import zlib

import pytest
from pydantic import ValidationError

from oec.foundation.contracts import (
    FoundationModelSpec,
    VisionEmbeddingSpec,
    VisionImageInput,
    VLMGenerationSpec,
)
from oec.foundation.errors import (
    InvalidImageSourceError,
    ModelRevisionRequiredError,
    PillowNotAvailableError,
    TransformersNotAvailableError,
    UnsupportedVisionModelError,
)
from oec.foundation.runtime import (
    foundation_capabilities,
    load_vision_image,
    probe_pillow,
    vision_embed,
    vlm_generate,
)


def _tiny_png_bytes() -> bytes:
    """1×1 opaque PNG (valid raster, no Pillow required to construct)."""

    # IHDR + IDAT + IEND for 1x1 RGB
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    # filter byte 0 + RGB white
    raw = b"\x00\xff\xff\xff"
    idat = zlib.compress(raw)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _tiny_png_b64() -> str:
    return base64.b64encode(_tiny_png_bytes()).decode("ascii")


def test_vision_image_requires_exactly_one_source() -> None:
    with pytest.raises(ValidationError):
        VisionImageInput()
    with pytest.raises(ValidationError):
        VisionImageInput(image_base64=_tiny_png_b64(), image_path="x.png")
    ok = VisionImageInput(image_base64=_tiny_png_b64())
    assert ok.image_base64 is not None
    ok_path = VisionImageInput(image_path="sample.png")
    assert ok_path.image_path == "sample.png"


def test_vision_image_rejects_url_path() -> None:
    with pytest.raises(ValidationError):
        VisionImageInput(image_path="https://example.com/a.png")
    with pytest.raises(ValidationError):
        VisionImageInput(image_path="http://example.com/a.png")


def test_vision_image_rejects_disallowed_extension() -> None:
    with pytest.raises(ValidationError):
        VisionImageInput(image_path="weights.bin")
    with pytest.raises(ValidationError):
        VisionImageInput(image_path="model.safetensors")


def test_remote_model_requires_revision_on_vision_embed() -> None:
    with pytest.raises(ValidationError):
        VisionEmbeddingSpec(
            images=[VisionImageInput(image_base64=_tiny_png_b64())],
            model=FoundationModelSpec(model_id="openai/clip-vit-base-patch32"),
        )


def test_remote_model_requires_revision_on_vlm_generate() -> None:
    with pytest.raises(ValidationError):
        VLMGenerationSpec(
            prompt="what is this?",
            image=VisionImageInput(image_base64=_tiny_png_b64()),
            model=FoundationModelSpec(model_id="Salesforce/blip-image-captioning-base"),
        )


def test_vision_specs_accept_pinned_revision() -> None:
    emb = VisionEmbeddingSpec(
        images=[VisionImageInput(image_base64=_tiny_png_b64())],
        model=FoundationModelSpec(
            model_id="openai/clip-vit-base-patch32",
            revision="5812e510083bb2d23fa43778a39ac065d205ed4d",
        ),
    )
    assert emb.model.revision == "5812e510083bb2d23fa43778a39ac065d205ed4d"
    gen = VLMGenerationSpec(
        prompt="caption",
        image=VisionImageInput(image_base64=_tiny_png_b64()),
        model=FoundationModelSpec(
            model_id="Salesforce/blip-image-captioning-base",
            revision="abcdef0123456789abcdef0123456789abcdef01",
        ),
    )
    assert gen.model.revision == "abcdef0123456789abcdef0123456789abcdef01"


def test_vision_specs_reject_trust_remote_code_true() -> None:
    with pytest.raises(ValidationError):
        VisionEmbeddingSpec(
            images=[VisionImageInput(image_base64=_tiny_png_b64())],
            model=FoundationModelSpec(
                model_id="openai/clip-vit-base-patch32",
                revision="5812e510083bb2d23fa43778a39ac065d205ed4d",
                trust_remote_code=True,
            ),
        )


def test_capabilities_lists_vision_domains() -> None:
    caps = foundation_capabilities()
    assert "vision_embed_backends" in caps
    assert "vlm_generate_backends" in caps
    assert "transformers" in caps["vision_embed_backends"]
    assert "pillow_available" in caps


def test_vision_embed_fail_closed_without_transformers() -> None:
    from oec.foundation.runtime import probe_transformers

    avail, _, _ = probe_transformers()
    if avail:
        pytest.skip("transformers installed")
    with pytest.raises(TransformersNotAvailableError):
        vision_embed(
            VisionEmbeddingSpec(
                images=[VisionImageInput(image_base64=_tiny_png_b64())],
                model=FoundationModelSpec(
                    model_id="openai/clip-vit-base-patch32",
                    revision="5812e510083bb2d23fa43778a39ac065d205ed4d",
                ),
            )
        )


def test_vlm_generate_fail_closed_without_transformers() -> None:
    from oec.foundation.runtime import probe_transformers

    avail, _, _ = probe_transformers()
    if avail:
        pytest.skip("transformers installed")
    with pytest.raises(TransformersNotAvailableError):
        vlm_generate(
            VLMGenerationSpec(
                prompt="describe",
                image=VisionImageInput(image_base64=_tiny_png_b64()),
                model=FoundationModelSpec(
                    model_id="Salesforce/blip-image-captioning-base",
                    revision="main",
                ),
            )
        )


def test_load_image_fail_closed_without_pillow() -> None:
    avail, _, _ = probe_pillow()
    if avail:
        pytest.skip("pillow installed")
    with pytest.raises(PillowNotAvailableError):
        load_vision_image(VisionImageInput(image_base64=_tiny_png_b64()))


def test_error_codes_stable() -> None:
    assert InvalidImageSourceError().code == "invalid_image_source"
    assert ModelRevisionRequiredError().code == "model_revision_required"
    assert PillowNotAvailableError().code == "pillow_not_available"
    assert UnsupportedVisionModelError().code == "unsupported_vision_model"
