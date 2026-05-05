"""Three OIDCProxy variants that toggle CIMD and DCR independently.

Why a custom subclass instead of `AWSCognitoProvider`:
    `AWSCognitoProvider` does not expose `enable_cimd`, and FastMCP's OAuthProxy
    hard-codes `ClientRegistrationOptions(enabled=True)`. To showcase the three
    patterns (CIMD-only / DCR-only / neither) we subclass `OIDCProxy` — one
    level up from `AWSCognitoProvider` — and toggle:

        * CIMD: passed through the `enable_cimd` parameter
        * DCR : override `self.client_registration_options.enabled` just before
                `get_routes()` runs. That single flag drives both the
                `/register` route registration (MCP SDK) and the
                `registration_endpoint` field in the authorization server
                metadata.
"""

from __future__ import annotations

from fastmcp.server.auth.oauth_proxy.models import ProxyDCRClient
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from mcp.server.auth.settings import ClientRegistrationOptions
from pydantic import AnyUrl
from starlette.routing import Route

from .config import cognito_oidc_config_url


class _CognitoBase(OIDCProxy):
    """Compose the Cognito OIDC discovery URL and delegate to OIDCProxy."""

    def __init__(
        self,
        *,
        user_pool_id: str,
        aws_region: str,
        client_id: str,
        client_secret: str,
        base_url: str,
        **kwargs,
    ) -> None:
        super().__init__(
            config_url=cognito_oidc_config_url(user_pool_id, aws_region),
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            redirect_path="/auth/callback",
            **kwargs,
        )


class _DCRDisabled:
    """Mixin that turns off Dynamic Client Registration.

    Flipping `self.client_registration_options.enabled = False` before the
    routes are built makes the MCP SDK skip the `/register` route AND causes
    both metadata builders (SDK default + OAuthProxy's CIMD-aware override)
    to omit `registration_endpoint`. The extra filter at the end is belt-and-
    braces in case a future FastMCP release wires `/register` differently.
    """

    def get_routes(self, mcp_path=None):  # type: ignore[override]
        if self.client_registration_options is None:
            self.client_registration_options = ClientRegistrationOptions(enabled=False)
        else:
            self.client_registration_options.enabled = False
        routes = super().get_routes(mcp_path)  # type: ignore[misc]
        return [
            r for r in routes
            if not (isinstance(r, Route) and r.path == "/register")
        ]


class CIMDOnlyCognito(_DCRDisabled, _CognitoBase):
    """Pattern 1: CIMD enabled, DCR hidden from metadata and disabled."""

    def __init__(self, **kwargs) -> None:
        super().__init__(enable_cimd=True, **kwargs)


class DCROnlyCognito(_CognitoBase):
    """Pattern 2: CIMD disabled, DCR enabled (FastMCP default behavior)."""

    def __init__(self, **kwargs) -> None:
        super().__init__(enable_cimd=False, **kwargs)


class TraditionalCognito(_DCRDisabled, _CognitoBase):
    """Pattern 3: Neither CIMD nor DCR — pre-registered client only."""

    def __init__(self, **kwargs) -> None:
        super().__init__(enable_cimd=False, **kwargs)

    async def register_static_client(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uris: list[AnyUrl],
        scope: str,
        client_name: str,
    ) -> None:
        """Seed a pre-registered MCP client without DCR normalization."""
        if not client_id:
            raise ValueError("client_id is required")
        if not client_secret:
            raise ValueError("client_secret is required")

        client = ProxyDCRClient(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=redirect_uris,
            grant_types=["authorization_code", "refresh_token"],
            scope=scope,
            token_endpoint_auth_method="client_secret_post",
            allowed_redirect_uri_patterns=self._allowed_client_redirect_uris,
            client_name=client_name,
        )
        await self._client_store.put(key=client_id, value=client)
