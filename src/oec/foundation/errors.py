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
