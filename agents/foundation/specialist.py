"""Foundation Models Specialist for governed public OEC skills (W6 + S1).

Covers ``foundation.*`` embed / generate / capabilities / peft_train.
``builtin_hash`` embeddings work without extras; transformers generate and
peft_train require ``oec[foundation]``.
"""

from __future__ import annotations

from agents.common import SkillSpecialist


class FoundationSpecialist(SkillSpecialist):
    name = "foundation_specialist"
    demos = {
        "embed": (
            "foundation.embed",
            {
                "texts": ["open engineering compute", "scientific skills"],
                "backend": "builtin_hash",
                "dim": 16,
                "seed": 0,
                "normalize": True,
            },
        ),
        "capabilities": ("foundation.capabilities", {}),
        # Requires oec[foundation] + model weights; fail-closed without extras.
        "generate": (
            "foundation.generate",
            {
                "prompt": "Hello",
                "model_id": "sshleifer/tiny-gpt2",
                "max_new_tokens": 8,
                "temperature": 0,
                "seed": 0,
            },
        ),
        # S1 (ADR 0041): LoRA train; requires oec[foundation], fail-closed without it.
        "peft_train": (
            "foundation.peft_train",
            {
                "model_id": "sshleifer/tiny-gpt2",
                "mode": "peft_lora",
                "texts": ["open engineering compute", "scientific skills"],
                "target_modules": ["c_attn"],
                "max_steps": 2,
                "seed": 0,
            },
        ),
    }
