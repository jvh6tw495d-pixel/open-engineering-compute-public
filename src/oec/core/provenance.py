"""Unified provenance record for scientific runs (v2.0 kernel)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from oec.core.types import BackendRef


class ProvenanceRecord(BaseModel):
    """Formal provenance envelope (extends ADR 0017 facts)."""

    model_config = ConfigDict(frozen=True, extra="allow")

    input_hash: str | None = None
    oec_version: str | None = None
    git_commit: str | None = None
    trace_id: str | None = None
    backends: list[BackendRef] = Field(default_factory=list)
    # Extra keys (sandbox flags, units, …) allowed via extra="allow"

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> ProvenanceRecord:
        if not raw:
            return cls()
        backends: list[BackendRef] = []
        for item in raw.get("backends") or []:
            if isinstance(item, dict) and item.get("name"):
                backends.append(
                    BackendRef(
                        name=str(item["name"]),
                        version=None if item.get("version") is None else str(item["version"]),
                    )
                )
        # Known fields
        data = {
            "input_hash": raw.get("input_hash"),
            "oec_version": raw.get("oec_version"),
            "git_commit": raw.get("git_commit"),
            "trace_id": raw.get("trace_id"),
            "backends": backends,
        }
        # Pass through other keys
        for k, v in raw.items():
            if k not in data and k != "backends":
                data[k] = v
        return cls.model_validate(data)
