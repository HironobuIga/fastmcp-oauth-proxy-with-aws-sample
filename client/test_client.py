"""MCP test client that exercises the three Cognito auth patterns.

Usage::

    uv run python -m client.test_client --pattern cimd
    uv run python -m client.test_client --pattern dcr
    uv run python -m client.test_client --pattern traditional

For ``--pattern cimd`` the env var ``CIMD_DOC_URL`` must point to the HTTPS URL
serving the rendered metadata document. FastMCP's CIMD validator rejects
localhost/private IPs and requires the document's ``client_id`` to match that
public URL, so run ``scripts/render_cimd_metadata.py`` after choosing the URL.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import httpx
from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.auth import OAuth

from src.config import settings

load_dotenv()


def _pattern_port(pattern: str) -> int:
    return {
        "cimd": settings.port_cimd,
        "dcr": settings.port_dcr,
        "traditional": settings.port_traditional,
    }[pattern]


def _server_url(pattern: str) -> str:
    return f"http://localhost:{_pattern_port(pattern)}/mcp/"


async def _show_discovery(pattern: str) -> dict:
    base = f"http://localhost:{_pattern_port(pattern)}"
    async with httpx.AsyncClient() as http:
        r = await http.get(f"{base}/.well-known/oauth-authorization-server")
        r.raise_for_status()
        meta = r.json()
    print(f"\n=== discovery metadata ({pattern}) ===")
    print(
        json.dumps(
            {
                "registration_endpoint": meta.get("registration_endpoint"),
                "client_id_metadata_document_supported": meta.get(
                    "client_id_metadata_document_supported"
                ),
            },
            indent=2,
        )
    )
    return meta


def _build_oauth(pattern: str, server_url: str) -> OAuth:
    if pattern == "cimd":
        cimd_url = os.environ.get("CIMD_DOC_URL")
        if not cimd_url:
            sys.exit(
                "CIMD_DOC_URL is not set. Run ./scripts/prepare_cimd_gist.sh "
                "or render client/client_metadata.example.json with "
                "scripts/render_cimd_metadata.py and host it at a public HTTPS URL."
            )
        return OAuth(mcp_url=server_url, client_metadata_url=cimd_url)
    if pattern == "dcr":
        return OAuth(mcp_url=server_url)
    if pattern == "traditional":
        from src.server_traditional import TRADITIONAL_CALLBACK_PORT

        client_id = settings.traditional_mcp_client_id
        client_secret = settings.traditional_mcp_client_secret
        if not client_id or not client_secret:
            sys.exit(
                "TRADITIONAL_MCP_CLIENT_ID / _SECRET are not set. Start "
                "src.server_traditional once; it prints the seeded MCP client "
                "credentials. Put them into .env."
            )
        return OAuth(
            mcp_url=server_url,
            client_id=client_id,
            client_secret=client_secret,
            callback_port=TRADITIONAL_CALLBACK_PORT,
        )
    raise ValueError(f"unknown pattern: {pattern}")


async def run(pattern: str) -> None:
    await _show_discovery(pattern)
    server_url = _server_url(pattern)
    oauth = _build_oauth(pattern, server_url)

    print(f"\n=== connecting to {server_url} with pattern={pattern} ===")
    async with Client(server_url, auth=oauth) as mcp:
        tools = await mcp.list_tools()
        print("tools:", [t.name for t in tools])

        echo = await mcp.call_tool("echo", {"message": f"hello from {pattern}"})
        print("echo →", echo.data)

        me = await mcp.call_tool("whoami", {})
        print("whoami →", json.dumps(me.data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pattern", choices=["cimd", "dcr", "traditional"], required=True
    )
    args = parser.parse_args()
    asyncio.run(run(args.pattern))


if __name__ == "__main__":
    main()
