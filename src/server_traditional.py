"""Pattern 3: neither CIMD nor DCR — a pre-registered MCP client is seeded.

Pattern 3 simulates the "traditional" OAuth world where a human admin registers
a client out-of-band and hands the credentials to the developer. Because DCR is
disabled, we seed the MCP-facing client into the proxy's client storage at
startup. Credentials come from `TRADITIONAL_MCP_CLIENT_ID/SECRET` env vars so
they survive across runs.
"""

from __future__ import annotations

import asyncio
import logging

from fastmcp import FastMCP
from pydantic import AnyUrl

from .cognito_variants import TraditionalCognito
from .config import settings
from .tools import register_tools

logger = logging.getLogger(__name__)

TRADITIONAL_CALLBACK_PORT = 8765
_CALLBACK_URL = f"http://localhost:{TRADITIONAL_CALLBACK_PORT}/callback"


def build_server() -> tuple[FastMCP, TraditionalCognito, str, str]:
    client_id = settings.traditional_mcp_client_id
    client_secret = settings.traditional_mcp_client_secret
    if not client_id or not client_secret:
        raise RuntimeError(
            "TRADITIONAL_MCP_CLIENT_ID / TRADITIONAL_MCP_CLIENT_SECRET are required. "
            "Run ./scripts/prepare_traditional_client.sh before starting this server."
        )

    auth = TraditionalCognito(
        user_pool_id=settings.user_pool_id,
        aws_region=settings.aws_region,
        client_id=settings.cognito_client_id,
        client_secret=settings.cognito_client_secret,
        base_url=f"http://localhost:{settings.port_traditional}",
        allowed_client_redirect_uris=[_CALLBACK_URL],
    )
    mcp = FastMCP("cognito-traditional", auth=auth)
    register_tools(mcp)
    return mcp, auth, client_id, client_secret


async def _seed_preregistered_client(
    auth: TraditionalCognito, client_id: str, client_secret: str
) -> None:
    await auth.register_static_client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uris=[AnyUrl(_CALLBACK_URL)],
        scope="openid email profile",
        client_name="FastMCP Traditional Sample Client",
    )
    logger.info("Seeded pre-registered MCP client: %s", client_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp, auth, client_id, client_secret = build_server()
    asyncio.run(_seed_preregistered_client(auth, client_id, client_secret))
    print(
        f"[pattern 3] pre-registered MCP client_id = {client_id}\n"
        "[pattern 3] pre-registered MCP client_secret loaded from .env\n"
        f"[pattern 3] redirect_uri (must match test client) = {_CALLBACK_URL}\n"
        "Run ./scripts/prepare_traditional_client.sh to create or rotate the client.",
        flush=True,
    )
    mcp.run(transport="http", host="localhost", port=settings.port_traditional)


if __name__ == "__main__":
    main()
