"""L14/L15 — capability matrix and isolation helpers."""

from __future__ import annotations

import importlib.util
from typing import Any

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


def probe_optional() -> dict[str, bool]:
    return {name: importlib.util.find_spec(name) is not None for name in OPTIONAL_PACKAGES}


def capability_matrix() -> list[dict[str, Any]]:
    probes = probe_optional()
    return [
        {
            "wave": "L5",
            "backend": "huggingface",
            "methods": ["lora", "qlora", "full", "sft"],
            "extra": "oec[foundation]",
            "available": probes["transformers"] and probes["peft"],
            "status": "operational",
        },
        {
            "wave": "L6",
            "backend": "neural.distill",
            "methods": ["distill"],
            "extra": "oec[neural]",
            "available": probes["torch"],
            "status": "operational",
        },
        {
            "wave": "L7",
            "backend": "unsloth",
            "methods": ["lora", "qlora", "sft"],
            "extra": "external:unsloth+datasets+trl",
            "available": probes["unsloth"] and probes["datasets"] and probes["trl"],
            "status": "operational-when-installed",
        },
        {
            "wave": "L8",
            "backend": "axolotl",
            "methods": ["sft", "lora"],
            "extra": "external:axolotl",
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
            "extra": "external:art",
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
