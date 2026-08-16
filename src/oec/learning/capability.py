"""L14/L15 — capability matrix and isolation helpers."""

from __future__ import annotations

import importlib.util
from typing import Any

OPTIONAL_PACKAGES: tuple[str, ...] = (
    "torch",
    "transformers",
    "peft",
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
            "status": "wired",
        },
        {
            "wave": "L6",
            "backend": "neural.distill",
            "methods": ["distill"],
            "extra": "oec[neural]",
            "available": probes["torch"],
            "status": "contract",
        },
        {
            "wave": "L7",
            "backend": "unsloth",
            "methods": ["lora", "qlora", "sft"],
            "extra": "unsloth",
            "available": probes["unsloth"],
            "status": "fail-closed-stub",
        },
        {
            "wave": "L8",
            "backend": "axolotl",
            "methods": ["sft", "lora"],
            "extra": "axolotl",
            "available": probes["axolotl"],
            "status": "fail-closed-stub",
        },
        {
            "wave": "L10",
            "backend": "art",
            "methods": ["grpo"],
            "extra": "art",
            "available": probes["art"],
            "status": "fail-closed-stub",
        },
    ]
