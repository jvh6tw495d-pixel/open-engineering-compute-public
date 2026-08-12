"""foundation.capabilities — probe transformers availability (no download)."""

from __future__ import annotations

from typing import Any

from oec.foundation.runtime import foundation_capabilities


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    del inputs
    return {"result": foundation_capabilities(), "diagnostics": {}}
