# セットアップ詳細

README のクイックスタートを補足する詳細手順です。

## 1. 事前確認

```bash
./scripts/check_prereqs.sh
```

このスクリプトは `uv`、AWS CLI 認証、CDK CLI、Python 3.12、GitHub CLI、使用予定ポートを確認します。`gh` は Pattern 1 の Gist 作成だけに必要です。

## 2. 依存関係

```bash
uv sync --all-groups
```

`infra` dependency group に CDK Python libraries、`dev` dependency group に pytest を入れています。

## 3. Cognito stack

初回だけ CDK bootstrap が必要です。

```bash
cd infrastructure
cdk bootstrap
cd ..
```

global install していない場合は `npx cdk bootstrap` を使ってください。

stack をデプロイします。

```bash
./scripts/deploy_cognito.sh
```

このスクリプトは次を行います。

1. `cdk deploy FastmcpCognitoSampleStack`
2. CloudFormation outputs から User Pool ID / Client ID / Hosted UI domain を取得
3. `aws cognito-idp describe-user-pool-client` で ClientSecret を取得
4. `.env` に `AWS_REGION`、`USER_POOL_ID`、`COGNITO_CLIENT_ID`、`COGNITO_CLIENT_SECRET` を upsert

## 4. Traditional client

Pattern 3 は MCP クライアントの `client_id` / `client_secret` を事前配布する方式です。

```bash
./scripts/prepare_traditional_client.sh
```

未設定の場合だけ `.env` に次を保存します。

- `TRADITIONAL_MCP_CLIENT_ID`
- `TRADITIONAL_MCP_CLIENT_SECRET`

`src/server_traditional.py` は起動時にこの値を FastMCP の client storage に登録し、`/token` では `client_secret_post` を検証します。

## 5. テストユーザー

Cognito User Pool の self-service sign-up は無効です。テストユーザーはこのスクリプトで管理者作成します。

```bash
./scripts/create_test_user.sh -u you@example.com
```

既存ユーザーのパスワードを再設定する場合:

```bash
./scripts/create_test_user.sh -u you@example.com -f
```

`-p` でパスワードを渡すと shell history や process arguments に残り得ます。通常は対話プロンプトで入力してください。

## 6. CIMD Gist

CIMD では metadata document の公開 HTTPS URL が `client_id` です。FastMCP は localhost/private IP を拒否し、JSON 内の `client_id` と取得元 URL の一致も確認します。

標準手順:

```bash
./scripts/prepare_cimd_gist.sh
```

このスクリプトは public GitHub Gist を作成し、Gist の raw URL を `client_id` に入れた JSON へ更新し、`.env` に `CIMD_DOC_URL` を保存します。

手動で別の HTTPS ホストを使う場合:

```bash
export CIMD_DOC_URL='https://example.com/path/client_metadata.example.json'
uv run python scripts/render_cimd_metadata.py "$CIMD_DOC_URL" > /tmp/client_metadata.example.json
```

生成した `/tmp/client_metadata.example.json` をその URL で配信してください。

## 7. サーバ確認

3 つのサーバを別々のターミナルで起動します。

```bash
./scripts/run.sh cimd
./scripts/run.sh dcr
./scripts/run.sh traditional
```

別ターミナルで metadata を検査します。

```bash
./scripts/check_server.sh cimd
./scripts/check_server.sh dcr
./scripts/check_server.sh traditional
```

## 8. 後片付け

```bash
./scripts/destroy_cognito.sh
```

CI や自動化で確認なしに削除したい場合は `--force` を使います。

```bash
./scripts/destroy_cognito.sh --force
```

## 本番運用との差分

- secret は `.env` ではなく Secrets Manager などから取得してください。
- Cognito callback URL は localhost HTTP ではなく HTTPS URL を追加してください。
- `allowed_client_redirect_uris` は検証用に緩めています。本番では許可範囲を絞ってください。
- FastMCP の token/client storage は Redis / DynamoDB などの永続ストアに差し替えてください。
