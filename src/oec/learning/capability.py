"""L14/L15 — capability matrix and isolation helpers."""

from __future__ import annotations

import importlib
import importlib.util
from typing import Any

from oec.learning.install_hints import ART_MISSING, AXOLOTL_MISSING, HF_MISSING, UNSLOTH_MISSING

OPTIONAL_PACKAGES: tuple[str, ...] = (
    "torch",
    "transformers",
    "peft",
    "datasets",
    "trl",
    "unsloth",
    "axolotl",
    "art",
)


def _art_is_openpipe() -> bool:
    """True only when the imported ``art`` module is OpenPipe ART, not ASCII-art."""
    if importlib.util.find_spec("art") is None:
        return False
    try:
        module = importlib.import_module("art")
    except Exception:
        return False
    return callable(getattr(module, "train_grpo", None))


def probe_optional() -> dict[str, bool]:
    probes = {name: importlib.util.find_spec(name) is not None for name in OPTIONAL_PACKAGES}
    probes["art"] = _art_is_openpipe()
    return probes


def capability_matrix() -> list[dict[str, Any]]:
    probes = probe_optional()
    return [
        {
            "wave": "L5",
            "backend": "huggingface",
            "methods": ["lora", "qlora", "full", "sft"],
            "extra": "oec[foundation]",
            "auto_install": False,
            "install": HF_MISSING,
            "available": probes["transformers"] and probes["peft"],
            "status": "operational",
        },
        {
            "wave": "L6",
            "backend": "neural.distill",
            "methods": ["distill"],
            "extra": "oec[neural]",
            "auto_install": False,
            "install": "Tabular distill requires oec[neural]: uv sync --extra neural",
            "available": probes["torch"],
            "status": "operational",
        },
        {
            "wave": "L7",
            "backend": "unsloth",
            "methods": ["lora", "qlora", "sft"],
            "extra": "external:isolated-venv:unsloth",
            "auto_install": False,
            "install": UNSLOTH_MISSING,
            "available": probes["unsloth"] and probes["datasets"] and probes["trl"],
            "status": "operational-when-installed",
        },
        {
            "wave": "L8",
            "backend": "axolotl",
            "methods": ["sft", "lora"],
            "extra": "external:wsl-or-linux:axolotl",
            "auto_install": False,
            "install": AXOLOTL_MISSING,
            "available": probes["axolotl"],
            "status": "operational-when-installed",
        },
        {
            "wave": "L9",
            "backend": "rl-contracts",
            "methods": ["trajectory", "episode"],
            "extra": None,
            "available": True,
            "status": "operational",
        },
        {
            "wave": "L10",
            "backend": "art",
            "methods": ["grpo"],
            "extra": "external:openpipe-art",
            "auto_install": False,
            "install": ART_MISSING,
            "available": probes["art"],
            "status": "operational-when-installed",
        },
        {
            "wave": "L11",
            "backend": "verifiers",
            "methods": ["reward"],
            "extra": None,
            "available": True,
            "status": "operational",
        },
        {
            "wave": "L12",
            "backend": "worker-pipeline",
            "methods": ["sft", "lora", "evaluate"],
            "extra": "oec[foundation]",
            "available": True,
            "status": "operational",
        },
        {
            "wave": "L13",
            "backend": "suite",
            "methods": ["compare", "probe"],
            "extra": None,
            "available": True,
            "status": "operational",
        },
        {
            "wave": "L14",
            "backend": "ci-learning-contracts",
            "methods": ["isolation", "smoke"],
            "extra": None,
            "available": True,
            "status": "operational",
        },
    ]
