"""S5 MCP catalog integration: raw skills and agent.foundation demos."""

from __future__ import annotations

from agents.foundation.specialist import FoundationSpecialist

from oec.mcp.server import build_tools
from oec.sdk import Engine


def test_mcp_discovers_s5_raw_skills_and_foundation_agent_demos() -> None:
    """Catalog discovery must not execute optional Transformers/Pillow dependencies."""
    engine = Engine(skills_root="skills")
    engine.warm()
    by_name = {tool.name: tool for tool in build_tools(engine)}

    for skill_id in ("foundation.vision_embed", "foundation.vlm_generate"):
        assert skill_id in by_name
        revision = by_name[skill_id].inputSchema["properties"]["revision"]
        assert revision["pattern"] == "^[0-9a-fA-F]{40}$"

    for label, expected_skill in (
        ("vision_embed", "foundation.vision_embed"),
        ("vlm_generate", "foundation.vlm_generate"),
    ):
        skill_id, inputs = FoundationSpecialist.demos[label]
        assert skill_id == expected_skill
        assert len(inputs["revision"]) == 40
