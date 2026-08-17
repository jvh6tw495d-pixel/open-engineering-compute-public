"""Environment / hardware snapshot for Learning experiments (L3)."""

from __future__ import annotations

import platform
import sys
from typing import Any


def capture_environment() -> dict[str, Any]:
    """Stdlib-only snapshot — no torch required."""
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "implementation": platform.python_implementation(),
    }


def capture_code_version() -> dict[str, str | None]:
    commit: str | None = None
    try:
        import subprocess

        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        ).strip()
    except Exception:
        commit = None
    return {"git_commit": commit}


_DEPENDENCY_PACKAGES: tuple[str, ...] = (
    "torch",
    "transformers",
    "peft",
    "unsloth",
    "axolotl",
    "art",
)


def capture_dependency_versions() -> dict[str, str | None]:
    """Installed versions of optional Learning backends. Does not import them."""
    from importlib.metadata import PackageNotFoundError, version

    versions: dict[str, str | None] = {}
    for name in _DEPENDENCY_PACKAGES:
        if name == "art":
            try:
                versions["art"] = version("openpipe-art")
            except PackageNotFoundError:
                versions["art"] = None
            continue
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    return versions


def capture_hardware() -> dict[str, Any]:
    """Optional CUDA probe — fail open to CPU metadata if torch absent."""
    info: dict[str, Any] = {"accelerator": "cpu", "cuda_available": False}
    try:
        import torch

        info["cuda_available"] = bool(torch.cuda.is_available())
        if info["cuda_available"]:
            info["accelerator"] = "cuda"
            info["cuda_device_count"] = int(torch.cuda.device_count())
            info["cuda_device_name"] = torch.cuda.get_device_name(0)
    except Exception:
        pass
    return info
