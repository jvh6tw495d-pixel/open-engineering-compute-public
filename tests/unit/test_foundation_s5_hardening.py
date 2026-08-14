"""S5 security/regression tests for pinned VLM models and bounded image decode."""

from __future__ import annotations

import base64
import struct
import zlib

import pytest
from pydantic import ValidationError

from oec.foundation.contracts import (
    MAX_IMAGE_DIMENSION,
    FoundationModelSpec,
    VisionEmbeddingSpec,
    VisionImageInput,
)
from oec.foundation.errors import InvalidImageSourceError
from oec.foundation.runtime import load_vision_image, pretrained_load_kwargs

_PINNED_SHA = "5812e510083bb2d23fa43778a39ac065d205ed4d"


def _minimal_png_with_dimensions(width: int, height: int) -> bytes:
    """A tiny compressed PNG container whose IHDR claims large dimensions."""
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data
    ihdr += struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    return signature + ihdr + iend


@pytest.mark.parametrize("revision", ["main", "v1.2.3", "5812e510"])
def test_remote_vision_model_rejects_non_commit_revision(revision: str) -> None:
    with pytest.raises(ValidationError, match="40-hex commit SHA"):
        VisionEmbeddingSpec(
            images=[VisionImageInput(image_base64="eA==")],
            model=FoundationModelSpec(model_id="openai/clip-vit-base-patch32", revision=revision),
        )


def test_remote_vision_model_passes_full_commit_to_all_pretrained_loads() -> None:
    kwargs = pretrained_load_kwargs(
        FoundationModelSpec(model_id="openai/clip-vit-base-patch32", revision=_PINNED_SHA)
    )
    assert kwargs == {"trust_remote_code": False, "revision": _PINNED_SHA}


def test_compressed_png_with_oversized_metadata_is_rejected_before_pixel_load() -> None:
    pytest.importorskip("PIL")
    raw = _minimal_png_with_dimensions(MAX_IMAGE_DIMENSION + 1, 1)
    assert len(raw) < 1024

    with pytest.raises(InvalidImageSourceError) as caught:
        load_vision_image(VisionImageInput(image_base64=base64.b64encode(raw).decode("ascii")))

    assert caught.value.details["width"] == MAX_IMAGE_DIMENSION + 1
    assert caught.value.details["stage"] == "metadata"


def test_metadata_validation_happens_before_image_load_or_convert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    class OversizedImage:
        size = (MAX_IMAGE_DIMENSION + 1, 1)
        n_frames = 1

        def __enter__(self) -> OversizedImage:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def load(self) -> None:
            raise AssertionError("pixel load must not run for rejected metadata")

        def convert(self, _: str) -> object:
            raise AssertionError("conversion must not run for rejected metadata")

    monkeypatch.setattr(Image, "open", lambda _: OversizedImage())
    with pytest.raises(InvalidImageSourceError, match="dimensions"):
        load_vision_image(VisionImageInput(image_base64="eA=="))
