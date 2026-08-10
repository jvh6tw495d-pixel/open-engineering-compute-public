"""Content fingerprints for evolutionary provenance (ADR 0031)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def problem_fingerprint(payload: dict[str, Any]) -> str:
    return stable_json_hash(payload)
