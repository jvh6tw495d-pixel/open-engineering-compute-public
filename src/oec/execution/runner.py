"""Runs *inside* the sandboxed subprocess (see ADR 0012). Never imported
by the parent process — only ever invoked as ``python -m oec.execution.runner``.

This is the *only* place in the codebase that imports a skill's
Python implementation. Protocol:

- stdin: one JSON object ``{"skill_path": str, "module": str,
  "function": str, "inputs": object}``.
- stdout (exit 0): one JSON object ``{"result": object, "diagnostics":
  object}`` — the skill's entrypoint must return exactly this shape
  (both keys required; use ``{}`` for an unused one). No hidden
  defaults (plan section 11.1): a skill that returns anything else is a
  contract violation, not silently coerced.
- stderr + exit 1: an unhandled exception's traceback, on any failure
  (missing module, missing function, exception raised, malformed
  return value).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Any


class RunnerContractError(Exception):
    """The skill's entrypoint didn't follow the runner's return-value contract."""


def _load_entrypoint(skill_path: Path, module: str, function: str) -> Any:
    module_file = skill_path / f"{module}.py"
    if not module_file.is_file():
        raise ImportError(f"entrypoint module not found: {module_file}")
    spec = importlib.util.spec_from_file_location(f"oec_skill_{module}", module_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load entrypoint module from {module_file}")
    loaded_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded_module)
    return getattr(loaded_module, function)


def _run(payload: dict[str, Any]) -> dict[str, Any]:
    skill_path = Path(payload["skill_path"])
    entrypoint = _load_entrypoint(skill_path, payload["module"], payload["function"])
    output = entrypoint(payload["inputs"])

    if not isinstance(output, dict) or not {"result", "diagnostics"} >= output.keys():
        raise RunnerContractError(
            "skill entrypoint must return {'result': ..., 'diagnostics': ...} "
            f"(and no other keys); got {output!r}"
        )
    return {"result": output.get("result", {}), "diagnostics": output.get("diagnostics", {})}


def main() -> int:
    payload = json.loads(sys.stdin.read())
    outcome = _run(payload)
    json.dump(outcome, sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
