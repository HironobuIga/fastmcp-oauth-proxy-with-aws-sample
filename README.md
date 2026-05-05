# FastMCP × AWS Cognito OAuthProxy sample

FastMCP の `OIDCProxy` を使い、同じ Amazon Cognito User Pool に対して MCP クライアント認証の 3 方式を試すためのサンプルです。Cognito 側は 1 つだけ作り、FastMCP 側の proxy 設定だけを変えて比較します。

| # | サーバ | Port | CIMD | DCR (`/register`) | MCP クライアントが使う client_id |
|---|--------|------|------|-------------------|----------------------------------|
| 1 | `src/server_cimd.py` | 8001 | 有効 | 無効 | Public HTTPS Client ID Metadata Document URL |
| 2 | `src/server_dcr.py` | 8002 | 無効 | 有効 | MCP SDK の Dynamic Client Registration |
| 3 | `src/server_traditional.py` | 8003 | 無効 | 無効 | 事前登録された client_id / client_secret |

このリポジトリはローカル検証用です。CDK で AWS リソースを作るため、検証後は `./scripts/destroy_cognito.sh` で削除してください。

## 前提

- Python 3.12
- `uv`
- AWS CLI と AWS 認証情報
- AWS CDK CLI (`npm i -g aws-cdk` または `npx cdk`)
- GitHub CLI (`gh`) は Pattern 1 の Gist 作成に必要

まず確認します。

```bash
./scripts/check_prereqs.sh
```

## クイックスタート

```bash
# 1. 依存関係
uv sync --all-groups

# 2. Cognito をデプロイ
cd infrastructure && cdk bootstrap; cd ..   # npx を使う場合は npx cdk bootstrap
./scripts/deploy_cognito.sh

# 3. Traditional 用の事前登録 client_id / client_secret を .env に作る
./scripts/prepare_traditional_client.sh

# 4. Cognito テストユーザーを作る（パスワードは対話プロンプトで入力）
./scripts/create_test_user.sh -u you@example.com

# 5. CIMD 用の public Gist を作り、CIMD_DOC_URL を .env に保存する
./scripts/prepare_cimd_gist.sh
```

3 つのサーバを別々のターミナルで起動します。

```bash
./scripts/run.sh cimd
./scripts/run.sh dcr
./scripts/run.sh traditional
```

各サーバの discovery metadata が期待どおりか確認します。

```bash
./scripts/check_server.sh cimd
./scripts/check_server.sh dcr
./scripts/check_server.sh traditional
```

期待値:

| Pattern | `registration_endpoint` | `client_id_metadata_document_supported` |
|---------|--------------------------|-----------------------------------------|
| CIMD | なし | `true` |
| DCR | あり | なし |
| Traditional | なし | なし |

最後に MCP クライアントで接続します。ブラウザで Cognito Hosted UI が開くので、作成したテストユーザーでログインしてください。

```bash
uv run python -m client.test_client --pattern cimd
uv run python -m client.test_client --pattern dcr
uv run python -m client.test_client --pattern traditional
```

成功すると `echo` と `whoami` の結果が表示されます。

Cognito User Pool の self-service sign-up は無効です。このサンプルでは、テストユーザーは `scripts/create_test_user.sh` で管理者作成します。

## Pattern 1: CIMD

CIMD では `client_id` が Client ID Metadata Document 自身の HTTPS URL になります。FastMCP は SSRF 防御のため localhost/private IP の URL を拒否し、さらに JSON 内の `client_id` が取得元 URL と一致することを検証します。

標準手順では `./scripts/prepare_cimd_gist.sh` が次を行います。

1. `client/client_metadata.example.json` を public GitHub Gist として作成
2. 安定した raw URL を `client_id` に入れた JSON を再生成
3. Gist を更新
4. `.env` に `CIMD_DOC_URL=...` を保存

手動でホストする場合は、公開 URL が決まった後に次のように JSON を生成してください。

```bash
export CIMD_DOC_URL='https://example.com/path/client_metadata.example.json'
uv run python scripts/render_cimd_metadata.py "$CIMD_DOC_URL" > /tmp/client_metadata.example.json
```

## Pattern 2: DCR

DCR は FastMCP `OAuthProxy` の既定の Dynamic Client Registration をそのまま使います。MCP クライアントが `/register` に登録し、FastMCP がクライアント情報を保存します。Cognito には 1 つの固定 app client だけを登録しておき、FastMCP が OAuth flow を proxy します。

## Pattern 3: Traditional

Traditional では DCR も CIMD も使いません。`./scripts/prepare_traditional_client.sh` が `.env` に作った `TRADITIONAL_MCP_CLIENT_ID` / `TRADITIONAL_MCP_CLIENT_SECRET` を、サーバ起動時に FastMCP の client storage へ登録します。

この方式では `/token` で `client_secret_post` が要求されます。つまりサンプル上でも「事前に配布された client_id / client_secret を使う」従来型の OAuth client 運用を確認できます。

## 後片付け

検証が終わったら Cognito stack を削除します。

```bash
./scripts/destroy_cognito.sh
```

確認なしで削除する場合:

```bash
./scripts/destroy_cognito.sh --force
```

`.env` は削除しません。不要なら手動で消してください。

## トラブルシュート

- `check_prereqs.sh` が AWS 認証で失敗する: `aws configure` または AWS SSO login を実行してください。
- `prepare_cimd_gist.sh` が失敗する: `gh auth login` を実行し、Gist 作成権限があるアカウントでログインしてください。
- CIMD で `invalid_client` になる: `CIMD_DOC_URL` の URL と JSON 内の `client_id` が完全一致しているか確認してください。
- Traditional で `OAuth server rejected the static client credentials` になる: `.env` の `TRADITIONAL_MCP_CLIENT_ID` / `TRADITIONAL_MCP_CLIENT_SECRET` と、起動中の `server_traditional` が同じ値を読んでいるか確認してください。
- ポートが使えない: `PORT_CIMD`、`PORT_DCR`、`PORT_TRADITIONAL` を `.env` で変える場合、`infrastructure/cognito_stack.py` の callback URLs も合わせて変えてから再デプロイしてください。

## 本番利用時の注意

- `.env` に保存している Cognito app client secret と Traditional client secret はサンプル用です。本番では Secrets Manager などから取得してください。
- Cognito callback URL は localhost HTTP に固定しています。公開環境では HTTPS callback URL を CDK stack に追加してください。
- `allowed_client_redirect_uris` はローカル検証向けです。本番では許可する redirect URI を絞ってください。
- FastMCP の token/client storage はローカルファイル既定です。本番では Redis や DynamoDB などの永続ストアを使ってください。

## 詳細

- セットアップ詳細: `docs/setup.md`
- 3 パターンの内部挙動: `docs/patterns.md`
- ライセンス: MIT
