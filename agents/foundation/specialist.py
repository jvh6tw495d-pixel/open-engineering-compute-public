"""Foundation Models Specialist for governed public OEC skills (W6).

Covers ``foundation.*`` embed / generate / capabilities. ``builtin_hash``
embeddings work without extras; transformers generate requires ``oec[foundation]``.
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
    }
