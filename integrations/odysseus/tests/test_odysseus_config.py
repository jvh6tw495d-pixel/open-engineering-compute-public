"""Smoke checks for Odysseus integration artifacts (handbook §15.1).

These tests do **not** start Odysseus. They guarantee the example
configs stay parseable and that the OEC MCP entrypoint the configs
point at remains importable — so a broken rename cannot silently
orphan the integration.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_local_mcp_example_is_valid_json_with_oec_server() -> None:
    data = json.loads((_ROOT / "local-mcp.example.json").read_text(encoding="utf-8"))
    oec = data["mcpServers"]["oec"]
    assert oec["command"] == "uv"
    assert "server" in oec["args"]
    assert "mcp" in oec["args"]
    assert "--skills-root" in oec["args"]


def test_remote_mcp_example_is_valid_json() -> None:
    data = json.loads((_ROOT / "remote-mcp.example.json").read_text(encoding="utf-8"))
    assert "oec-remote" in data["mcpServers"]
    assert "url" in data["mcpServers"]["oec-remote"]


def test_docker_compose_example_mentions_oec_api() -> None:
    text = (_ROOT / "docker-compose.example.yml").read_text(encoding="utf-8")
    assert "oec-api" in text
    assert "oec server api" in text


def test_readme_documents_success_criteria() -> None:
    text = (_ROOT / "README.md").read_text(encoding="utf-8")
    for needle in ("list_skills", "oec server mcp", "ExecutionResult"):
        assert needle in text


def test_mcp_entrypoint_still_importable() -> None:
    """The config's contract: oec.mcp.run_stdio_server must exist."""
    pytest.importorskip("mcp")
    from oec.mcp import run_stdio_server

    assert callable(run_stdio_server)
