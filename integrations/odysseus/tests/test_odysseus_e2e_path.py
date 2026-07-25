"""Fase 7 acceptance: the path Odysseus uses (MCP adapter over Engine)
must execute a real skill and return methodology + result + provenance.

Does not launch Odysseus itself — proves the OEC side of the contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from oec.mcp.server import build_tools, call_tool  # noqa: E402
from oec.sdk import Engine  # noqa: E402

_SKILLS_ROOT = Path("skills")


def test_mcp_list_skills_and_run_electrical_skill() -> None:
    engine = Engine(skills_root=_SKILLS_ROOT)
    engine.warm()
    tools = {t.name: t for t in build_tools(engine)}
    assert "list_skills" in tools
    assert "electrical.three_phase_power" in tools

    listing = call_tool(engine, "list_skills", {})
    assert listing.isError is False
    assert listing.content

    result = call_tool(
        engine,
        "electrical.three_phase_power",
        {
            "voltage_line_to_line": {"value": 380, "unit": "V"},
            "current_line": {"value": 10, "unit": "A"},
            "power_factor": 0.8,
            "power_factor_type": "lagging",
        },
    )
    assert result.isError is False
    payload = json.loads(result.content[0].text)
    assert payload["status"] == "VERIFIED"
    assert "active_power" in payload["result"]
    assert payload["skill"]["id"] == "electrical.three_phase_power"
    assert "method" in payload
    assert payload["run_id"]
    assert isinstance(payload.get("provenance"), dict)
