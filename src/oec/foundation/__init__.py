"""Foundation-model contracts (W6 / ADR 0038).

Optional extra ``oec[foundation]`` (transformers). Core install stays free of HF.
"""

from __future__ import annotations

from oec.foundation.contracts import (
    EmbeddingBackend,
    EmbeddingSpec,
    FoundationModelSpec,
    GenerationBackend,
    GenerationSpec,
    PEFTMethod,
    PEFTSpec,
)
from oec.foundation.errors import FoundationError, TransformersNotAvailableError
from oec.foundation.runtime import (
    embed_texts,
    foundation_capabilities,
    generate_text,
    probe_transformers,
)

__all__ = [
    "EmbeddingBackend",
    "EmbeddingSpec",
    "FoundationError",
    "FoundationModelSpec",
    "GenerationBackend",
    "GenerationSpec",
    "PEFTMethod",
    "PEFTSpec",
    "TransformersNotAvailableError",
    "embed_texts",
    "foundation_capabilities",
    "generate_text",
    "probe_transformers",
]
