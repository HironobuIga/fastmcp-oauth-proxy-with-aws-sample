# 3 パターンの内部挙動

このサンプルは Cognito User Pool と Cognito app client を 1 つだけ作り、FastMCP `OIDCProxy` の見せ方だけを変えます。Cognito は常に OAuth authorization code flow の上流 IdP です。

## 共通の流れ

1. FastMCP 起動時に `OIDCProxy` が Cognito OIDC discovery を読み込む。
2. MCP クライアントが `/.well-known/oauth-authorization-server` を取得する。
3. クライアントは FastMCP の `/authorize` に向かう。
4. FastMCP は Cognito Hosted UI に redirect する。
5. Cognito login 後、FastMCP の `/auth/callback` で code を token に交換する。
6. FastMCP は MCP クライアント用の token/code を発行する。

3 パターンの差は、MCP クライアントがどうやって `client_id` を得るかと、discovery metadata に何を出すかです。

## Pattern 1: CIMD only

- `enable_cimd=True`
- DCR は `_DCRDisabled` で無効化
- discovery:
  - `client_id_metadata_document_supported: true`
  - `registration_endpoint` なし
- MCP クライアントは public HTTPS metadata URL を `client_id` として使う。
- metadata JSON 内の `client_id` は、その JSON の公開 URL と一致している必要がある。
- `token_endpoint_auth_method: "none"` のため、サンプルではクライアント秘密鍵や JWKS は不要。

## Pattern 2: DCR only

- `enable_cimd=False`
- DCR は FastMCP `OAuthProxy` の既定どおり有効
- discovery:
  - `registration_endpoint: http://localhost:8002/register`
  - `client_id_metadata_document_supported` なし
- MCP クライアントは `/register` で client_id を取得する。
- 登録された redirect URI は FastMCP の local client storage に保存され、以後の `/authorize` で検証される。

## Pattern 3: Traditional client

- `enable_cimd=False`
- DCR は `_DCRDisabled` で無効化
- discovery:
  - `registration_endpoint` なし
  - `client_id_metadata_document_supported` なし
- MCP クライアントは事前配布された `client_id` / `client_secret` を使う。
- `src/server_traditional.py` は起動時に `TraditionalCognito.register_static_client(...)` を呼び、`client_secret_post` の client を FastMCP client storage に登録する。
- `/token` では MCP SDK の client authenticator が `client_secret` を検証する。

## discovery 差分

| フィールド | CIMD | DCR | Traditional |
|-----------|------|-----|-------------|
| `registration_endpoint` | なし | あり | なし |
| `client_id_metadata_document_supported` | `true` | なし | なし |
| `/register` route | 404 | 201 | 404 |

## なぜ `OIDCProxy` を直接 subclass しているか

- `AWSCognitoProvider` は `enable_cimd` を公開していない。
- FastMCP `OAuthProxy` は DCR 有効の `ClientRegistrationOptions` を作る。
- DCR を隠すには `get_routes()` 前に `client_registration_options.enabled = False` を反映する必要がある。
- このため `src/cognito_variants.py` では `OIDCProxy` を直接 subclass し、CIMD/DCR の組み合わせを 3 つに分けている。
