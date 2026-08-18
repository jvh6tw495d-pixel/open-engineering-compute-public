"""Foundation-model contracts (W6 / ADR 0038).

Optional extra ``oec[foundation]`` (transformers). Core install stays free of HF.
"""

from __future__ import annotations

from oec.foundation.contracts import (
    ArtifactKind,
    EmbeddingBackend,
    EmbeddingSpec,
    FoundationModelSpec,
    GenerationBackend,
    GenerationSpec,
    PEFTMethod,
    PEFTSpec,
    TrainingArtifact,
    TrainingBudgetSpec,
    TrainingDatasetSpec,
    VllmGenerateSpec,
)
from oec.foundation.errors import (
    AdapterNotFoundError,
    BitsAndBytesNotAvailableError,
    FoundationError,
    PeftNotAvailableError,
    TransformersNotAvailableError,
    VllmUnreachableError,
)
from oec.foundation.runtime import (
    embed_texts,
    foundation_capabilities,
    generate_text,
    peft_train,
    probe_peft,
    probe_transformers,
)

__all__ = [
    "AdapterNotFoundError",
    "ArtifactKind",
    "BitsAndBytesNotAvailableError",
    "EmbeddingBackend",
    "EmbeddingSpec",
    "FoundationError",
    "FoundationModelSpec",
    "GenerationBackend",
    "GenerationSpec",
    "PEFTMethod",
    "PEFTSpec",
    "PeftNotAvailableError",
    "TrainingArtifact",
    "TrainingBudgetSpec",
    "TrainingDatasetSpec",
    "TransformersNotAvailableError",
    "VllmGenerateSpec",
    "VllmUnreachableError",
    "embed_texts",
    "foundation_capabilities",
    "generate_text",
    "peft_train",
    "probe_peft",
    "probe_transformers",
]
