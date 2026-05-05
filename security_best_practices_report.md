# Security Best Practices Report

## Executive Summary

This repository is a local, public sample for trying FastMCP OAuthProxy with Amazon Cognito. The security review found no critical issues. The original findings have been remediated in the current working tree, with the sample now defaulting to admin-created Cognito users, safer password examples, non-executing `.env` parsing in shell scripts, reduced secret output, and frozen dependency installation in CI.

Scope reviewed:

- Python/FastMCP server code under `src/`
- CLI test client under `client/`
- Guided shell scripts under `scripts/`
- AWS CDK Cognito stack under `infrastructure/`
- README and setup docs

References used:

- Local skill reference: `python-fastapi-web-server-security.md`, used as the closest ASGI/Starlette/Pydantic web-server baseline.
- AWS documentation: [Security best practices for Amazon Cognito user pools](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-security-best-practices.html)
- AWS documentation: [Using Amazon Cognito user pools security features](https://docs.aws.amazon.com/cognito/latest/developerguide/managing-security.html)

## Remediation Status

### SBP-1: Disable unused Cognito self-service sign-up

Status: Addressed.

Location:

- `infrastructure/cognito_stack.py:16`

Change:

```python
self_sign_up_enabled=False,
```

Rationale:

The guided sample flow creates test users with `scripts/create_test_user.sh`, so public self-service sign-up is unnecessary. Disabling it reduces public account-creation abuse risk for users who leave the sample stack running.

### SBP-2: Avoid password arguments in user-facing docs

Status: Addressed.

Locations:

- `README.md:40-41`
- `docs/setup.md:63-73`
- `scripts/create_test_user.sh:6-14`
- `scripts/create_test_user.sh:68-89`

Changes:

- README and setup docs now use the hidden interactive password prompt:

```bash
./scripts/create_test_user.sh -u you@example.com
```

- The script comments warn that `-p` is for throwaway automation only.
- `admin-set-user-password` now uses a temporary `--cli-input-json` file so the password is not passed to the AWS CLI as a command-line argument.

Residual note:

If users explicitly pass `-p` or `PASSWORD=...`, the secret can still be captured by shell history or process environment. The documented path avoids that.

### SBP-3: Stop executing `.env` as shell code

Status: Addressed.

Locations:

- `scripts/env.sh`
- `scripts/check_prereqs.sh:6-59`
- `scripts/check_server.sh:6-39`
- `scripts/create_test_user.sh:18-31`
- `scripts/destroy_cognito.sh:6-18`

Change:

Shell scripts now call `load_env_file`, which reads only explicitly allowed variable names from `.env` instead of `source`-ing the file.

Rationale:

This keeps `.env` as configuration data and avoids arbitrary shell execution if the file is edited incorrectly or copied from an untrusted source.

### SBP-4: Reduce Traditional client secret stdout exposure

Status: Addressed.

Locations:

- `src/server_traditional.py:29-73`
- `scripts/prepare_traditional_client.sh:30-57`

Changes:

- `server_traditional.py` now requires `TRADITIONAL_MCP_CLIENT_ID` and `TRADITIONAL_MCP_CLIENT_SECRET` to be present and no longer generates or prints a secret at startup.
- `prepare_traditional_client.sh` writes the secret to `.env` but prints only a masked value.

Residual note:

The secret still lives in local `.env` for sample purposes. The README continues to call out Secrets Manager or equivalent storage for production.

### SBP-5: Enforce frozen dependency sync in CI

Status: Addressed.

Location:

- `.github/workflows/ci.yml:19-23`

Change:

```yaml
run: uv sync --frozen --all-groups
```

Rationale:

CI now fails if `pyproject.toml` and `uv.lock` drift, keeping dependency changes intentional and reviewable.

## Positive Security Notes

- The FastMCP servers bind to `localhost`, not `0.0.0.0`, which matches the local-only sample intent.
- CIMD rendering validates HTTPS URLs with a non-root path in `scripts/render_cimd_metadata.py`.
- The Traditional flow uses `client_secret_post` in `src/cognito_variants.py`, so it exercises a real pre-registered secret check.
- The Cognito app client sets `prevent_user_existence_errors=True` in `infrastructure/cognito_stack.py`.
- The README explicitly warns that `.env` secrets, localhost HTTP callback URLs, and local FastMCP storage are sample-only and should be replaced for production.
