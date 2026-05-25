"""Shared MCP tools exposed by all three sample servers."""

from __future__ import annotations

import asyncio

import httpx
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from .config import settings

# Cognito access tokens omit identity claims like `email`, so we resolve them
# via the OIDC userinfo endpoint (discovered from the OpenID configuration).
# The endpoint URL is cached for the lifetime of the process.
_userinfo_endpoint: str | None = None
_userinfo_lock = asyncio.Lock()


async def _resolve_userinfo_endpoint() -> str:
    global _userinfo_endpoint
    if _userinfo_endpoint is not None:
        return _userinfo_endpoint
    async with _userinfo_lock:
        if _userinfo_endpoint is None:
            async with httpx.AsyncClient(timeout=5.0) as http:
                r = await http.get(settings.cognito_oidc_config_url)
                r.raise_for_status()
                _userinfo_endpoint = r.json()["userinfo_endpoint"]
    return _userinfo_endpoint


async def _fetch_userinfo(access_token: str) -> dict:
    url = await _resolve_userinfo_endpoint()
    async with httpx.AsyncClient(timeout=5.0) as http:
        r = await http.get(
            url, headers={"Authorization": f"Bearer {access_token}"}
        )
        r.raise_for_status()
        return r.json()


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool
    async def whoami() -> dict:
        """Return the subject + email of the authenticated Cognito user."""
        token = get_access_token()
        claims = token.claims if token else {}
        email = claims.get("email")
        if token is not None and email is None:
            try:
                userinfo = await _fetch_userinfo(token.token)
                email = userinfo.get("email")
            except httpx.HTTPError:
                # Userinfo failures shouldn't break the tool — leave email None.
                pass
        return {
            "sub": claims.get("sub"),
            "email": email,
            "username": claims.get("username") or claims.get("cognito:username"),
            "scopes": token.scopes if token else [],
        }

    @mcp.tool
    def echo(message: str) -> str:
        """Echo a message back — useful as a smoke test for each pattern."""
        return message
