"""Shared MCP tools exposed by all three sample servers."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool
    def whoami() -> dict:
        """Return the subject + email of the authenticated Cognito user."""
        token = get_access_token()
        claims = token.claims if token else {}
        return {
            "sub": claims.get("sub"),
            "email": claims.get("email"),
            "username": claims.get("username") or claims.get("cognito:username"),
            "scopes": token.scopes if token else [],
        }

    @mcp.tool
    def echo(message: str) -> str:
        """Echo a message back — useful as a smoke test for each pattern."""
        return message
