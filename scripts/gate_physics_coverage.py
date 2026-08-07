"""Release-scoped coverage gate for ``oec.physics`` (OEC 2.6.0+).

The repo-wide pyproject gate was historically un-enforceable: legacy modules
outside this release's scope (api/cli/kernel/optimization, etc.) keep the
global ``src/oec`` tree just under the 90% bar, so an enforced
``fail_under=90`` would fail a normal ``pytest`` with no actionable scope.

This gate restores a hard quality bar where it matters for the Physics
Foundation deliverable: **the ``oec.physics`` package only**. It runs the full
test suite (unit + golden + skills) and enforces >= ``GATE`` percent line AND
branch coverage over ``oec.physics``. This is the command the release DoD
cites for "physics coverage >= 90%".

Usage:
    python scripts/gate_physics_coverage.py [--gate 90]

Exit codes:
    0  GO  — oec.physics coverage meets the gate
    1  NO-GO — coverage below the gate (also printed by coverage itself)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():  # fall back to the interpreter running this file
    PYTHON = Path(sys.executable)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=float, default=90.0, help="minimum physics coverage %%")
    args = parser.parse_args()

    ini = ROOT / "scripts" / "_gate_physics.ini"
    ini.write_text(
        f"[run]\n"
        f"source = oec.physics\n"
        f"branch = true\n"
        f"\n"
        f"[report]\n"
        f"fail_under = {args.gate}\n"
        f"show_missing = true\n"
        f"skip_empty = true\n",
        encoding="utf-8",
    )

    cmd = [
        str(PYTHON),
        "-m",
        "coverage",
        "run",
        "--rcfile",
        str(ini),
        "-m",
        "pytest",
        "tests/unit",
        "tests/golden",
        "skills",
        # Neutralize the repo-wide addopts: it injects `--cov=oec --cov-report`
        # which hands coverage to pytest-cov and would overwrite the data
        # collected by `coverage run`. Re-apply the essential flags explicitly.
        "-o",
        "addopts=--import-mode=importlib -m 'not slow'",
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    print("RUN:", " ".join(cmd))
    run = subprocess.run(cmd, cwd=ROOT)
    if run.returncode != 0:
        print(f"NO-GO: test suite failed (exit {run.returncode})", file=sys.stderr)
        return run.returncode

    report = subprocess.run(
        [str(PYTHON), "-m", "coverage", "report", "--rcfile", str(ini)],
        cwd=ROOT,
    )
    ini.unlink(missing_ok=True)

    print(f"\nGATE oec.physics >= {args.gate}% -> exit {report.returncode}")
    return report.returncode


if __name__ == "__main__":
    sys.exit(main())
