"""Pattern 1: CIMD-only FastMCP server backed by AWS Cognito."""

from __future__ import annotations

from fastmcp import FastMCP

from .cognito_variants import CIMDOnlyCognito
from .config import settings
from .tools import register_tools


def build_server() -> FastMCP:
    auth = CIMDOnlyCognito(
        user_pool_id=settings.user_pool_id,
        aws_region=settings.aws_region,
        client_id=settings.cognito_client_id,
        client_secret=settings.cognito_client_secret,
        base_url=f"http://localhost:{settings.port_cimd}",
    )
    mcp = FastMCP("cognito-cimd-only", auth=auth)
    register_tools(mcp)
    return mcp


def main() -> None:
    mcp = build_server()
    mcp.run(transport="http", host="localhost", port=settings.port_cimd)


if __name__ == "__main__":
    main()
