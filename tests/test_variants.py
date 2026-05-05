"""Unit tests for the three Cognito OIDCProxy variants.

These exercise `get_routes()` without hitting the network by mocking the
upstream OIDC discovery.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import AnyHttpUrl
from starlette.routing import Route


@pytest.fixture
def fake_oidc_config():
    """Build a minimal OIDCConfiguration the proxy is happy with."""
    from fastmcp.server.auth.oidc_proxy import OIDCConfiguration

    return OIDCConfiguration(
        issuer=AnyHttpUrl("https://example.issuer/ap-northeast-1_TEST"),
        authorization_endpoint=AnyHttpUrl("https://example.issuer/oauth2/authorize"),
        token_endpoint=AnyHttpUrl("https://example.issuer/oauth2/token"),
        jwks_uri=AnyHttpUrl("https://example.issuer/.well-known/jwks.json"),
        response_types_supported=["code"],
        subject_types_supported=["public"],
        id_token_signing_alg_values_supported=["RS256"],
    )


@pytest.fixture
def patch_discovery(fake_oidc_config):
    target = "fastmcp.server.auth.oidc_proxy.OIDCConfiguration.get_oidc_configuration"
    with patch(target, return_value=fake_oidc_config):
        yield


def _route_paths(routes):
    return {r.path for r in routes if isinstance(r, Route)}


def _discovery_flags(auth):
    """Re-run the metadata builder the same way OAuthProxy does and inspect it."""
    from mcp.server.auth.routes import build_metadata
    from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions

    cro = auth.client_registration_options or ClientRegistrationOptions()
    meta = build_metadata(
        auth.base_url,
        auth.service_documentation_url,
        cro,
        auth.revocation_options or RevocationOptions(),
    )
    if auth._cimd_manager is not None:
        meta.client_id_metadata_document_supported = True
    return {
        "registration_endpoint": meta.registration_endpoint,
        "client_id_metadata_document_supported": meta.client_id_metadata_document_supported,
    }


@pytest.mark.usefixtures("patch_discovery")
def test_cimd_only_exposes_cimd_not_dcr():
    from src.cognito_variants import CIMDOnlyCognito

    auth = CIMDOnlyCognito(
        user_pool_id="ap-northeast-1_TEST12345",
        aws_region="ap-northeast-1",
        client_id="c",
        client_secret="s",
        base_url="http://localhost:8001",
    )
    routes = auth.get_routes()
    paths = _route_paths(routes)
    assert "/register" not in paths
    flags = _discovery_flags(auth)
    assert flags["registration_endpoint"] is None
    assert flags["client_id_metadata_document_supported"] is True


@pytest.mark.usefixtures("patch_discovery")
def test_dcr_only_exposes_dcr_not_cimd():
    from src.cognito_variants import DCROnlyCognito

    auth = DCROnlyCognito(
        user_pool_id="ap-northeast-1_TEST12345",
        aws_region="ap-northeast-1",
        client_id="c",
        client_secret="s",
        base_url="http://localhost:8002",
    )
    routes = auth.get_routes()
    paths = _route_paths(routes)
    assert "/register" in paths
    flags = _discovery_flags(auth)
    assert flags["registration_endpoint"] is not None
    assert flags["client_id_metadata_document_supported"] is not True


@pytest.mark.usefixtures("patch_discovery")
def test_traditional_exposes_neither():
    from src.cognito_variants import TraditionalCognito

    auth = TraditionalCognito(
        user_pool_id="ap-northeast-1_TEST12345",
        aws_region="ap-northeast-1",
        client_id="c",
        client_secret="s",
        base_url="http://localhost:8003",
    )
    routes = auth.get_routes()
    paths = _route_paths(routes)
    assert "/register" not in paths
    flags = _discovery_flags(auth)
    assert flags["registration_endpoint"] is None
    assert flags["client_id_metadata_document_supported"] is not True


@pytest.mark.usefixtures("patch_discovery")
async def test_traditional_static_client_keeps_secret():
    from key_value.aio.stores.memory import MemoryStore
    from pydantic import AnyUrl

    from src.cognito_variants import TraditionalCognito

    auth = TraditionalCognito(
        user_pool_id="ap-northeast-1_TEST12345",
        aws_region="ap-northeast-1",
        client_id="c",
        client_secret="s",
        base_url="http://localhost:8003",
        allowed_client_redirect_uris=["http://localhost:*"],
        client_storage=MemoryStore(),
    )
    await auth.register_static_client(
        client_id="traditional-client",
        client_secret="traditional-secret",
        redirect_uris=[AnyUrl("http://localhost:8765/callback")],
        scope="openid email profile",
        client_name="Traditional Client",
    )

    client = await auth.get_client("traditional-client")
    assert client is not None
    assert client.client_secret == "traditional-secret"
    assert client.token_endpoint_auth_method == "client_secret_post"
