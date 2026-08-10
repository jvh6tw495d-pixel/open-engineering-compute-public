"""Content fingerprints for neural provenance (ADR 0031)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json_hash(payload: Any) -> str:
    """SHA-256 of canonical JSON (sorted keys, no whitespace variance)."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def dataset_fingerprint(x: list[list[float]], y: list[float]) -> str:
    return stable_json_hash({"x": x, "y": y})


def model_spec_fingerprint(spec: dict[str, Any]) -> str:
    return stable_json_hash(spec)
