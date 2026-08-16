"""Foundation Models Specialist for governed public OEC skills (W6 + S1 + S5).

Covers ``foundation.*`` embed / generate / capabilities / peft_train /
vision_embed / vlm_generate. ``builtin_hash`` embeddings work without
extras; transformers generate, peft_train, vision_embed and vlm_generate
require ``oec[foundation]`` and fail closed without it.
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
                "revision": "5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be",
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
                "revision": "5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be",
                "mode": "peft_lora",
                "texts": ["open engineering compute", "scientific skills"],
                "target_modules": ["c_attn"],
                "max_steps": 2,
                "seed": 0,
            },
        ),
        # S5 (ADR 0040 D3): CLIP image embedding; requires oec[foundation],
        # fail-closed without it. Pinned revision — no mutable model label.
        "vision_embed": (
            "foundation.vision_embed",
            {
                "images": [
                    {
                        "image_base64": (
                            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//"
                            "8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
                        )
                    }
                ],
                "model_id": "openai/clip-vit-base-patch32",
                "revision": "5812e510083bb2d23fa43778a39ac065d205ed4d",
                "dim": 16,
                "seed": 0,
            },
        ),
        # S5 (ADR 0040 D3): BLIP captioning; requires oec[foundation],
        # fail-closed without it. Pinned revision — no mutable model label.
        "vlm_generate": (
            "foundation.vlm_generate",
            {
                "prompt": "describe this image",
                "image": {
                    "image_base64": (
                        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//"
                        "8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
                    )
                },
                "model_id": "Salesforce/blip-image-captioning-base",
                "revision": "82a37760796d32b1411fe092ab5d4e227313294b",
                "max_new_tokens": 8,
                "seed": 0,
            },
        ),
    }
