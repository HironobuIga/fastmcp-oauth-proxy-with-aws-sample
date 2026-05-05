"""Load environment settings for all three FastMCP Cognito sample servers."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent


def cognito_oidc_config_url(user_pool_id: str, aws_region: str) -> str:
    return (
        f"https://cognito-idp.{aws_region}.amazonaws.com/"
        f"{user_pool_id}/.well-known/openid-configuration"
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    aws_region: str = Field(alias="AWS_REGION")
    user_pool_id: str = Field(alias="USER_POOL_ID")
    cognito_client_id: str = Field(alias="COGNITO_CLIENT_ID")
    cognito_client_secret: str = Field(alias="COGNITO_CLIENT_SECRET")

    port_cimd: int = Field(default=8001, alias="PORT_CIMD")
    port_dcr: int = Field(default=8002, alias="PORT_DCR")
    port_traditional: int = Field(default=8003, alias="PORT_TRADITIONAL")

    traditional_mcp_client_id: str | None = Field(
        default=None, alias="TRADITIONAL_MCP_CLIENT_ID"
    )
    traditional_mcp_client_secret: str | None = Field(
        default=None, alias="TRADITIONAL_MCP_CLIENT_SECRET"
    )

    @property
    def cognito_issuer(self) -> str:
        return (
            f"https://cognito-idp.{self.aws_region}.amazonaws.com/{self.user_pool_id}"
        )

    @property
    def cognito_oidc_config_url(self) -> str:
        return cognito_oidc_config_url(self.user_pool_id, self.aws_region)


settings = Settings()
