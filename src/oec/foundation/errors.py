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
