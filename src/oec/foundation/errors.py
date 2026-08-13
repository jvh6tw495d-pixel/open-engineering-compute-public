"""Foundation-model errors (W6)."""

from __future__ import annotations

from typing import Any

from oec.errors import OECError


class FoundationError(OECError):
    """Base error for foundation-model surface."""

    default_code = "foundation_error"


class TransformersNotAvailableError(FoundationError):
    """Raised when ``oec[foundation]`` / transformers is required but missing."""

    default_code = "transformers_not_available"

    def __init__(
        self,
        message: str = (
            "Hugging Face transformers is not installed. "
            "Install with: pip install 'oec[foundation]'"
        ),
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details or {})


class PeftNotAvailableError(FoundationError):
    """Raised when ``peft`` (LoRA/QLoRA) is required but missing."""

    default_code = "peft_not_available"

    def __init__(
        self,
        message: str = ("peft is not installed. Install with: pip install 'oec[foundation]'"),
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details or {})


class BitsAndBytesNotAvailableError(FoundationError):
    """Raised when ``bitsandbytes`` is required for QLoRA but missing."""

    default_code = "bitsandbytes_not_available"

    def __init__(
        self,
        message: str = (
            "bitsandbytes is not installed; QLoRA requires it. "
            "Install with: pip install bitsandbytes"
        ),
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details or {})


class AdapterNotFoundError(FoundationError):
    """Raised when a requested adapter/checkpoint path does not exist.

    Fail-closed: never silently fall back to the base model without an
    adapter (ADR 0041 §3).
    """

    default_code = "adapter_not_found"

    def __init__(
        self,
        message: str = "adapter/checkpoint path not found",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details or {})


class PillowNotAvailableError(FoundationError):
    """Raised when Pillow is required for image decode but missing."""

    default_code = "pillow_not_available"

    def __init__(
        self,
        message: str = (
            "Pillow is not installed. Image decode requires the foundation extra: "
            "pip install 'oec[foundation]'"
        ),
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details or {})


class InvalidImageSourceError(FoundationError):
    """Raised when an image source fails validation or decode."""

    default_code = "invalid_image_source"

    def __init__(
        self,
        message: str = "invalid image source",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details or {})


class ModelRevisionRequiredError(FoundationError):
    """Raised when a remote HF model is requested without an immutable revision."""

    default_code = "model_revision_required"

    def __init__(
        self,
        message: str = (
            "remote Hugging Face model requires an immutable revision "
            "(or an existing local model path for local-only mode)"
        ),
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details or {})


class UnsupportedVisionModelError(FoundationError):
    """Raised when the loaded model class is not a supported vision/VLM path.

    Fail-closed: never silently substitute a text-only / base LM.
    """

    default_code = "unsupported_vision_model"

    def __init__(
        self,
        message: str = "model is not a supported vision or VLM class",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details or {})
