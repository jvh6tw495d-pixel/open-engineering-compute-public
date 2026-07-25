"""MCP server adapter — thin interface over ``oec.sdk.Engine`` (ADR 0015)."""

from oec.mcp.server import build_server, run_stdio_server

__all__ = ["build_server", "run_stdio_server"]
