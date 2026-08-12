"""Hugging Face transformers adapter — optional extra ``oec[foundation]`` (W6)."""

from __future__ import annotations

import importlib.metadata

BACKEND_NAME = "transformers"


def probe() -> tuple[bool, str | None, str | None]:
    try:
        import transformers  # noqa: F401
    except ImportError as exc:
        return False, None, str(exc)
    try:
        version = importlib.metadata.version("transformers")
    except importlib.metadata.PackageNotFoundError:
        version = None
    return True, version, None
