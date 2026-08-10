"""Builds the audit-trail record stored in ``ExecutionResult.provenance``.

Covers: original units of normalized quantities (ADR 0003 / 0011), what the
sandbox actually enforced (ADR 0012), plus Phase A1 extensions (ADR 0017):
canonical ``input_hash`` and installed scientific ``backends`` versions.
"""

from __future__ import annotations

import functools
import hashlib
import json
import subprocess  # nosec B404 -- used only for a fixed, argument-free `git rev-parse HEAD`
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from oec import __version__ as oec_version

# Core engines declared in project dependencies. Listed when importable so
# provenance records the environment; skill.md names which entry points a
# method actually uses (ADR 0017).
_RUNTIME_BACKEND_PACKAGES: tuple[str, ...] = (
    "numpy",
    "scipy",
    "sympy",
    "pint",
    "pandas",
    "highspy",  # optional extra oec[optimization]; listed when installed
    "torch",  # optional extra oec[neural]; listed when installed (ADR 0031)
    "pymoo",  # optional extra oec[evolutionary]; listed when installed (ADR 0031)
)


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


class BackendRef(BaseModel):
    """An installed scientific engine available to the OEC runtime."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str


class ProvenanceRecord(BaseModel):
    """The full audit-trail record for one execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    oec_version: str
    git_commit: str | None
    trace_id: str
    requested_by: str | None
    seed: int | None
    sandbox: SandboxReport
    units: dict[str, QuantityProvenance] = Field(default_factory=dict)
    input_hash: str
    backends: list[BackendRef] = Field(default_factory=list)


def hash_inputs(inputs: dict[str, Any]) -> str:
    """SHA-256 of canonical JSON for ``inputs`` (stable across key order)."""
    payload = json.dumps(inputs, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def installed_backends() -> list[BackendRef]:
    """Versions of core scientific packages present in this environment."""
    found: list[BackendRef] = []
    for name in _RUNTIME_BACKEND_PACKAGES:
        try:
            found.append(BackendRef(name=name, version=pkg_version(name)))
        except PackageNotFoundError:
            continue
    return found


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
    inputs: dict[str, Any] | None = None,
    units: dict[str, QuantityProvenance] | None = None,
    backends: list[BackendRef] | None = None,
) -> dict[str, Any]:
    """Build the ``ExecutionResult.provenance`` dict for one execution.

    ``inputs`` should be the caller's original inputs (pre-normalization)
    so ``input_hash`` matches what the client sent (ADR 0017).
    """
    record = ProvenanceRecord(
        oec_version=oec_version,
        git_commit=_current_git_commit(),
        trace_id=trace_id,
        requested_by=requested_by,
        seed=seed,
        sandbox=sandbox,
        units=units or {},
        input_hash=hash_inputs(inputs or {}),
        backends=backends if backends is not None else installed_backends(),
    )
    return record.model_dump(mode="json")
