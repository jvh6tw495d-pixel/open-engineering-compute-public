"""W6 foundation contracts + builtin embed (no transformers required)."""

from __future__ import annotations

import pytest

from oec.foundation.contracts import EmbeddingBackend, EmbeddingSpec
from oec.foundation.errors import TransformersNotAvailableError
from oec.foundation.runtime import embed_texts, foundation_capabilities, probe_transformers


def test_builtin_hash_embedding_reproducible() -> None:
    spec = EmbeddingSpec(
        backend=EmbeddingBackend.BUILTIN_HASH,
        texts=["alpha", "beta"],
        dim=16,
        seed=7,
        normalize=True,
    )
    a = embed_texts(spec)
    b = embed_texts(spec)
    assert a["vectors"] == b["vectors"]
    assert a["n"] == 2
    assert len(a["vectors"][0]) == 16
    assert a["merit_owner"] == "oec"


def test_capabilities_probe() -> None:
    caps = foundation_capabilities()
    assert "builtin_hash" in caps["embedding_backends"]
    assert "transformers_available" in caps


def test_transformers_backend_fail_closed_when_missing() -> None:
    avail, _, _ = probe_transformers()
    if avail:
        pytest.skip("transformers installed")
    with pytest.raises(TransformersNotAvailableError):
        embed_texts(
            EmbeddingSpec(
                backend=EmbeddingBackend.TRANSFORMERS,
                texts=["x"],
                dim=8,
            )
        )
