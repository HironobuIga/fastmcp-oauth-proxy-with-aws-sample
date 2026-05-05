# Agent Instructions

This file provides guidance to Claude Code and Codex when working with code in this repository.

## What this repo demonstrates

A side-by-side comparison of three MCP-client authentication patterns against a single AWS Cognito User Pool, all implemented on top of FastMCP's `OIDCProxy`:

| # | Server | Port | `enable_cimd` | DCR (`/register`) | How the MCP client gets its `client_id` |
|---|--------|------|---------------|-------------------|-----------------------------------------|
| 1 | `src/server_cimd.py`        | 8001 | True  | disabled | Public HTTPS Client ID Metadata Document |
| 2 | `src/server_dcr.py`         | 8002 | False | enabled  | MCP SDK's Dynamic Client Registration |
| 3 | `src/server_traditional.py` | 8003 | False | disabled | Pre-registered `client_id` / `client_secret` seeded at startup |

The Cognito User Pool itself is identical across all three; only the FastMCP-side proxy behavior differs.

## Common commands

```bash
# Install (includes infra + dev groups)
uv sync --all-groups

# Deploy Cognito and write outputs into .env
cd infrastructure && cdk bootstrap; cd ..                         # first time only; use npx cdk bootstrap if needed
./scripts/deploy_cognito.sh                                       # writes USER_POOL_ID, COGNITO_CLIENT_ID, etc. into .env

# Prepare sample-only local client metadata
./scripts/prepare_traditional_client.sh                            # writes TRADITIONAL_MCP_CLIENT_ID/SECRET into .env
./scripts/prepare_cimd_gist.sh                                     # writes CIMD_DOC_URL into .env (requires gh auth)

# Create / reset a Cognito test user (reads USER_POOL_ID + AWS_REGION from .env)
./scripts/create_test_user.sh -u you@example.com                  # add -f to overwrite an existing user

# Run one of the three sample servers
./scripts/run.sh cimd          # :8001
./scripts/run.sh dcr           # :8002
./scripts/run.sh traditional   # :8003

# Tests (asyncio_mode=auto via pyproject.toml; conftest.py injects fake Cognito env vars)
uv run pytest
uv run pytest tests/test_variants.py::test_dcr_only_exposes_dcr_not_cimd

# Exercise a running server with the test client
uv run python -m client.test_client --pattern {cimd|dcr|traditional}
```

The `traditional` pattern requires `TRADITIONAL_MCP_CLIENT_ID` / `TRADITIONAL_MCP_CLIENT_SECRET` in `.env`; use `scripts/prepare_traditional_client.sh`. The `cimd` pattern requires `CIMD_DOC_URL` pointing to a **public HTTPS** copy of rendered CIMD metadata; use `scripts/prepare_cimd_gist.sh` for the standard public Gist flow.

## Architecture: why `OIDCProxy` is subclassed directly

The three variants live in `src/cognito_variants.py`. The reason this layer exists at all:

- **`AWSCognitoProvider`** does not expose `enable_cimd` — it inherits the parent's default (`True`) with no override.
- **`OAuthProxy`** (parent of `OIDCProxy`) hard-codes `ClientRegistrationOptions(enabled=True)`. The only way to disable DCR is to mutate `self.client_registration_options.enabled = False` *before* `get_routes()` runs, because that single flag drives both `/register` route registration (in the MCP SDK) and the `registration_endpoint` field in the authorization-server metadata.

So we subclass one level higher (`OIDCProxy`) and compose:

- `_CognitoBase` — builds the Cognito OIDC discovery URL and forwards to `OIDCProxy`.
- `_DCRDisabled` — mixin that flips `client_registration_options.enabled = False` inside `get_routes()` and additionally filters out any `/register` route as a belt-and-braces guard against future FastMCP changes.
- `CIMDOnlyCognito` = `_DCRDisabled` + `_CognitoBase`, `enable_cimd=True`
- `DCROnlyCognito`  = `_CognitoBase`, `enable_cimd=False`
- `TraditionalCognito` = `_DCRDisabled` + `_CognitoBase`, `enable_cimd=False`

`tests/test_variants.py` mocks `OIDCConfiguration.get_oidc_configuration` so route + metadata assertions can run without network access — re-use this fixture pattern when adding more variants.

## What the discovery endpoint looks like per pattern

Hitting `/.well-known/oauth-authorization-server` is the single best diagnostic for "did my variant wire up correctly":

| Field | Pattern 1 (CIMD) | Pattern 2 (DCR) | Pattern 3 (Traditional) |
|-------|------------------|------------------|--------------------------|
| `registration_endpoint` | absent | present | absent |
| `client_id_metadata_document_supported` | `true` | absent | absent |

`client/test_client.py` prints these two fields before connecting, which is useful when debugging.

## Pattern 3 specifics

`server_traditional.py` is the only server that does work at startup beyond `mcp.run(...)`: it calls `auth.register_static_client(...)` so the disabled-DCR proxy still has a known client to authorize against. The registered client uses `client_secret_post`, so the sample verifies the pre-registered `TRADITIONAL_MCP_CLIENT_SECRET` during `/token`.

## Configuration & infrastructure

- Server/client env loading runs through `src/config.py` (`pydantic-settings`, reads `.env` from repo root). Shell scripts use `scripts/env.sh` to load only expected keys without executing `.env` as shell code. Tests bypass this by setting fake values in `tests/conftest.py`.
- The CDK stack (`infrastructure/cognito_stack.py`) hard-codes callback URLs for ports 8001–8003 and uses a `cognito_domain` prefixed with the AWS account ID. Changing ports requires editing both the stack and `SERVER_PORTS`.
- `scripts/deploy_cognito.sh` fetches the `ClientSecret` via `aws cognito-idp describe-user-pool-client` because CDK does not expose it as a `CfnOutput`.

## Caveats called out in the README

- `client_secret` lives in plaintext `.env` for sample purposes — production should pull from Secrets Manager.
- `allowed_client_redirect_uris` in `server_traditional.py` is `http://localhost:*`; tighten before deploying.
- Cognito callback URLs are HTTP localhost only; add HTTPS production URLs to the CDK stack before any non-local use.
