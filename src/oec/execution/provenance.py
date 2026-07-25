"""Builds the audit-trail record stored in ``ExecutionResult.provenance``.

Frozen ahead of the Execution Service that populates it, so the shape is
agreed before either half of Sprint 03 (Claude Code's execution pipeline,
Grok's validator layers) needs to read or write it. Covers exactly what
the plan promises and no more: the original unit of a normalized
quantity (ADR 0003 / 0011) and what the sandbox actually enforced for
this run (ADR 0012) — not a generic audit-log dumping ground.
"""

from __future__ import annotations

import functools
import subprocess  # nosec B404 -- used only for a fixed, argument-free `git rev-parse HEAD`
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from oec import __version__ as oec_version


class SandboxReport(BaseModel):
    """What the Execution Service actually enforced for one run.

    Never assume ``ExecutionPolicy``'s declared ``network_access``/
    ``filesystem_access`` were honored just because a skill declared
    them — this reports what really happened (plan instruction 11:
    don't claim validation without evidence).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    timeout_enforced: bool
    network_isolation_enforced: bool
    filesystem_isolation_enforced: bool
    memory_limit_enforced: bool


class QuantityProvenance(BaseModel):
    """The unit an input/result field was submitted in, before normalization."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    original_unit: str
    normalized_unit: str


class ProvenanceRecord(BaseModel):
    """The full audit-trail record for one execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    oec_version: str
    git_commit: str | None
    trace_id: str
    requested_by: str | None
    seed: int | None
    sandbox: SandboxReport
    units: dict[str, QuantityProvenance] = {}


@functools.lru_cache(maxsize=1)
def _current_git_commit() -> str | None:
    """The OEC repository's own commit hash, cached for the process lifetime.

    Returns ``None`` outside a git repository or if git isn't available
    -- this is provenance metadata, not something an execution should
    ever fail over.
    """
    try:
        result = subprocess.run(  # nosec B603 B607 -- fixed argv, no shell, no user input
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def build_provenance(
    *,
    trace_id: str,
    requested_by: str | None,
    seed: int | None,
    sandbox: SandboxReport,
    units: dict[str, QuantityProvenance] | None = None,
) -> dict[str, Any]:
    """Build the ``ExecutionResult.provenance`` dict for one execution."""
    record = ProvenanceRecord(
        oec_version=oec_version,
        git_commit=_current_git_commit(),
        trace_id=trace_id,
        requested_by=requested_by,
        seed=seed,
        sandbox=sandbox,
        units=units or {},
    )
    return record.model_dump(mode="json")
