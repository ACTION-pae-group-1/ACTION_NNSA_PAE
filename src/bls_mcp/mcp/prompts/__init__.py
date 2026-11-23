"""Explicit registration of individual MCP prompts."""

from fastmcp import FastMCP

from bls_mcp.mcp.prompts import design_escalation_basket


def register_prompts(mcp: FastMCP) -> None:
    """Register every prompt exactly once."""
    design_escalation_basket.register(mcp)
