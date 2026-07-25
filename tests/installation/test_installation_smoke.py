"""Installation smoke test (deferred since Sprint 00; ADR 0014 folds it
into Sprint 06's `oec run` work — there was nothing meaningful to smoke
test about installation until a real execution command existed).

Every other test in this suite runs against the source tree via
``uv run pytest`` (or imports ``oec`` directly from ``src/``) — none of
them prove that ``pip install oec`` actually produces a working ``oec``
command with all its runtime dependencies correctly declared. This
test builds the real wheel, installs it into a throwaway venv, and
invokes the *installed* console script as a subprocess, the way an
actual user would.

Slow (spawns ``uv build``/``uv venv``/``uv pip install``, each its own
subprocess, then a fresh Python interpreter for every ``oec`` call) --
deselected by default (``pyproject.toml``'s ``addopts`` sets
``-m "not slow"``); run explicitly with ``uv run pytest -m slow --no-cov``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TIMEOUT_SECONDS = 180


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 -- fixed argv built from trusted constants/fixture paths
        args,
        cwd=cwd or _REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=_TIMEOUT_SECONDS,
    )


@pytest.fixture(scope="module")
def installed_oec(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the real wheel and install it into a throwaway venv.

    Returns the path to the *installed* ``oec`` console script (not
    ``uv run oec`` against the source tree).
    """
    dist_dir = tmp_path_factory.mktemp("dist")
    _run("uv", "build", "--out-dir", str(dist_dir))
    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one built wheel, found {wheels}"

    venv_dir = tmp_path_factory.mktemp("venv")
    _run("uv", "venv", str(venv_dir))
    _run("uv", "pip", "install", "--python", str(venv_dir), str(wheels[0]))

    oec_script = venv_dir / ("Scripts/oec.exe" if sys.platform == "win32" else "bin/oec")
    assert oec_script.is_file(), f"installed 'oec' console script not found at {oec_script}"
    return oec_script


def test_installed_oec_version(installed_oec: Path) -> None:
    result = _run(str(installed_oec), "version")
    assert result.returncode == 0
    assert result.stdout.strip()


def test_installed_oec_skills_list(installed_oec: Path) -> None:
    result = _run(
        str(installed_oec),
        "skills",
        "list",
        "--skills-root",
        str(_REPO_ROOT / "skills"),
        "--json",
    )
    assert result.returncode == 0
    manifests = json.loads(result.stdout)
    assert any(m["id"] == "mathematics.solve_root" for m in manifests)


def test_installed_oec_run(installed_oec: Path) -> None:
    result = _run(
        str(installed_oec),
        "run",
        "mathematics.solve_root",
        "--skills-root",
        str(_REPO_ROOT / "skills"),
        "--input",
        '{"expression": "x**2 - 2", "bracket": [0, 2]}',
        "--json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "VALIDATED"
    assert payload["result"]["method"] == "brentq"
