"""Parent-side wrapper: launches ``oec.execution.runner`` in a subprocess.

Implements ADR 0012's sandboxing decision. The timeout here is real —
``subprocess.run(..., timeout=...)`` unconditionally kills the child on
both Windows and POSIX. Network and filesystem isolation are **not**
enforced by this module; see ADR 0012 for why, and
:class:`~oec.execution.provenance.SandboxReport` for how that gap stays
visible in every result instead of being silently implied.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 -- used only to launch oec.execution.runner with a fixed argv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_MAX_ERROR_OUTPUT = 4000
_PROCESS_STARTUP_GRACE_SECONDS = 3.0


@dataclass(frozen=True)
class SandboxRunResult:
    """The outcome of running a skill's entrypoint in the sandbox."""

    timed_out: bool
    failed: bool
    result: dict[str, Any]
    diagnostics: dict[str, Any]
    error_output: str


def run_in_sandbox(
    *,
    skill_path: Path,
    module: str,
    function: str,
    inputs: dict[str, Any],
    timeout_seconds: float,
) -> SandboxRunResult:
    """Run a skill's entrypoint in a subprocess, enforcing ``timeout_seconds``.

    ``timeout_seconds`` is the skill's execution budget, not the process
    creation/import overhead. A small fixed grace keeps cold-start variance
    from turning valid short-running skills into flaky timeouts on slower
    Windows consoles while still enforcing a tight upper bound.
    """
    payload = json.dumps(
        {
            "skill_path": str(skill_path),
            "module": module,
            "function": function,
            "inputs": inputs,
        }
    )
    try:
        completed = subprocess.run(  # nosec B603 -- fixed argv (sys.executable + -m), no shell
            [sys.executable, "-m", "oec.execution.runner"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + _PROCESS_STARTUP_GRACE_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return SandboxRunResult(
            timed_out=True, failed=True, result={}, diagnostics={}, error_output=""
        )

    if completed.returncode != 0:
        return SandboxRunResult(
            timed_out=False,
            failed=True,
            result={},
            diagnostics={},
            error_output=completed.stderr[-_MAX_ERROR_OUTPUT:],
        )

    try:
        outcome = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return SandboxRunResult(
            timed_out=False,
            failed=True,
            result={},
            diagnostics={},
            error_output=(
                f"runner produced non-JSON stdout: {completed.stdout[:_MAX_ERROR_OUTPUT]!r}"
            ),
        )

    return SandboxRunResult(
        timed_out=False,
        failed=False,
        result=outcome.get("result", {}),
        diagnostics=outcome.get("diagnostics", {}),
        error_output="",
    )
