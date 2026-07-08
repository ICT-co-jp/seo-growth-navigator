# ictgrowthhacker-mcp — GA4 / GSC 接続用ローカルMCPサーバ

ictGrowthHacker プロジェクトで使う、Google Analytics 4 と Google Search Console
に接続するためのローカル Model Context Protocol (MCP) サーバです。
Claude（Desktop / Code）から GA4・GSC のデータを直接クエリし、リライト候補・
CTR改善候補・内部リンク強化候補・再訪設計などの編集判断に直結する関数群を提供します。

## 設計方針(セキュリティ)

- 認証は **OAuth 2.0 デスクトップアプリ + リフレッシュトークン** 方式。
  サービスアカウント鍵は使用しない(組織ポリシー `iam.disableServiceAccountKeyCreation` 前提)。
- 秘密情報(`client_secret` の中身、リフレッシュトークン)はディスクに平文を残さず、
  **OS 標準の資格情報ストア(`keyring`)** に格納します。
  - Windows: 資格情報マネージャー (DPAPI 暗号化)
  - macOS: Keychain
  - Linux: Secret Service (gnome-keyring 等)
- `.env` には識別子のみ書きます(プロパティID、サイトURL、GCPプロジェクトID等)。

## 提供関数

**GA4:**

- `ga4_run_report` — 任意ディメンション/指標
- `ga4_top_pages` — 期間内PV上位ページ
- `ga4_landing_pages` — ランディング別の流入と回遊指標
- `ga4_traffic_sources` — チャネル別流入
- `ga4_returning_users` — 新規/再訪比率

**Search Console:**

- `gsc_search_analytics` — 任意ディメンションで集計
- `gsc_top_queries` — クリック上位クエリ
- `gsc_page_queries` — 指定URLのクエリ別CTR・順位
- `gsc_low_ctr_pages` — 表示は多いがCTRが低い改善候補
- `gsc_position_window` — 平均掲載順位 4-15位など改善余地のあるページ

**その他:**

- `health_check` — 設定値と疎通の軽量確認

---

## セットアップ手順

ゼロから MCP サーバを起動するまでの完全な手順です。所要時間は10〜15分程度。

### 0. 前提

- Python 3.11 以上(`py -3.11 --version` で確認)
- Google アカウントが対象の GA4 プロパティと Search Console プロパティに**閲覧権限以上**で追加されていること

### 1. GCP で OAuth クライアントを発行する

1. [Google Cloud Console](https://console.cloud.google.com/) にログインし、対象プロジェクトを選択(無ければ新規作成)。
2. 「APIとサービス」→「ライブラリ」で以下を**有効化**:
   - `Google Analytics Data API`
   - `Google Search Console API`
3. 「APIとサービス」→「OAuth 同意画面」を開き、初回ならアプリ名・サポートメールを入れて保存。
   - User type は **外部**(個人 Google アカウントで認可する場合)。
   - テストユーザーに、認可するGoogleアカウントを追加。
4. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuth クライアントID」。
   - アプリケーションの種類: **デスクトップアプリ**
   - 名前は任意(例: `ictgrowthhacker-mcp-desktop`)
5. 作成後、右側の **JSONをダウンロード** をクリックして `client_secret_xxx.json` を保存しておく。
6. 画面上部に表示される **GCPプロジェクトID** を控えておく(後で `.env` に書く)。

### 2. .env を作成する

`mcp_server/.env.example` を `.env` にコピーして識別子を埋めます。

```cmd
cd C:\path\to\ictGrowthHacker\mcp_server
copy .env.example .env
```

`.env` を編集して以下を埋めます:

- `GA4_PROPERTY_ID` — GA4 管理画面 > プロパティ設定 の「プロパティID」(数字のみ)
- `GSC_SITE_URL` — Search Console に登録した形式そのまま
  - ドメインプロパティ: `sc-domain:example.com`
  - URLプレフィックス: `https://example.com/`
- `ICTGROWTHHACKER_QUOTA_PROJECT` — 1で控えた GCP プロジェクトID(任意だが推奨)

> ⚠ **重要**: `client_secret_xxx.json` の中身や OAuth リフレッシュトークンを `.env` に**書いてはいけません**。
> これらは次の手順で keyring に直接取り込みます。

### 3. .venv 構築とロック済み依存パッケージのインストール

Windows:

```cmd
run_server.bat
```

mac/Linux:

```bash
./run_server.sh
```

初回起動時に `.venv` 作成→`requirements.lock` から固定版をインストール→サーバ起動 が走ります。
以後は `requirements.lock` の SHA-256 が変わった時だけ再インストールします。
このタイミングでは keyring に何も入っていないので **エラーで落ちますが正常です**(次の手順で解決)。
`Ctrl+C` でいったん終了してください。

### 4. client_secret を keyring に取り込む

ダウンロードした JSON を keyring に格納します。

Windows(管理者権限不要):

```cmd
.venv\Scripts\python.exe secrets_setup.py import-client "%USERPROFILE%\Downloads\client_secret_xxx.json"
```

mac/Linux:

```bash
.venv/bin/python secrets_setup.py import-client ~/Downloads/client_secret_xxx.json
```

成功したら **元のJSONファイルは削除** してください(ディスク上に平文を残さないため)。

確認:

```cmd
.venv\Scripts\python.exe secrets_setup.py status
```

`client_secrets : present` と表示されればOK。

### 5. ブラウザで OAuth 認可する

```cmd
.venv\Scripts\python.exe auth_login.py
```

ブラウザが自動で開きます。

1. 対象の Google アカウントでサインイン
2. 「このアプリは Google で確認されていません」と表示されたら「詳細」→「(アプリ名)に移動」
3. GA4/GSC への閲覧権限スコープを許可

「認可に成功しました」と表示されたらブラウザタブを閉じます。
リフレッシュトークンが keyring に保存されました。

確認:

```cmd
.venv\Scripts\python.exe secrets_setup.py status
```

`oauth_token : present` と表示されればOK。

### 6. Claude Desktop / Claude Code に登録する

#### Claude Desktop の場合

`claude_desktop_config.json` を編集します。

**場所:**

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

**追記する内容(Windows例):**

```json
{
  "mcpServers": {
    "ictgrowthhacker-analytics": {
      "command": "C:\\path\\to\\ictGrowthHacker\\mcp_server\\run_server.bat"
    }
  }
}
```

**mac/Linux 例:**

```json
{
  "mcpServers": {
    "ictgrowthhacker-analytics": {
      "command": "/path/to/ictGrowthHacker/mcp_server/run_server.sh"
    }
  }
}
```

Claude Desktop を完全終了(タスクトレイから終了)→再起動。

#### Claude Code の場合

`claude mcp add` コマンドで登録します。

```bash
claude mcp add ictgrowthhacker-analytics -- C:\path\to\ictGrowthHacker\mcp_server\run_server.bat
```

### 7. 動作確認

Claude のチャットで:

```
health_check を呼んでください
```

レスポンスに以下が含まれれば成功:

```json
{
  "ga4_ok": true,
  "gsc_ok": true,
  "client_secrets_in_keyring": true,
  "oauth_token_in_keyring": true
}
```

---

## 動作確認の最短経路(初日)

セットアップ完了後、Claude から以下を順に実行すると「既存資産の伸びしろ」発見ができます。

1. `health_check` で疎通OK
2. `ga4_top_pages(limit=30)` 直近28日のPV上位30
3. `gsc_low_ctr_pages(min_impressions=500, max_ctr=0.02)` リライト対象
4. `gsc_position_window(min_position=4, max_position=15)` 1ページ目浮上候補
5. `ga4_landing_pages(limit=30)` 入口ページ別の回遊力比較

## トラブルシュート

| 症状 | 対処 |
|------|------|
| `keyring に oauth_token がありません` | `auth_login.py` 未実行。手順5を実行 |
| `OAuthトークンが無効です` | リフレッシュトークン失効。`secrets_setup.py delete-token` → 再度 `auth_login.py` |
| `403 PERMISSION_DENIED` | 認可した Google アカウントが GA4 / GSC に追加されていない |
| `quota project ... not enabled` | `ICTGROWTHHACKER_QUOTA_PROJECT` を OAuth クライアント発行プロジェクトIDに揃え、対象APIが有効化されているか確認 |
| `siteUrl` 不一致 | ドメインプロパティは `sc-domain:example.com` のように `sc-domain:` プレフィックス必須 |
| Claude から呼んでも応答が空 | Claude Desktop は stdio をログに出さないので、`ICTGROWTHHACKER_MCP_DEBUG=1` を環境変数で付けて手元から `run_server.bat` を直接実行し、stderr のスタックトレースを確認 |

## シークレット運用

- 認可をやり直したい: `secrets_setup.py delete-token` → `auth_login.py`
- 別プロジェクトの OAuth クライアントに切り替える: `secrets_setup.py delete-client` → `secrets_setup.py import-client <新しいjson>` → `auth_login.py`
- 現在の保存状況確認: `secrets_setup.py status`
- 複数の対象サイトを切り替えて使う: `.env` の `ICTGROWTHHACKER_KEYRING_SERVICE` を変えると keyring 内で別領域として管理できる

## ファイル構成

```
mcp_server/
├── server.py            MCPサーバ本体（GA4/GSC関数とFastMCP定義）
├── auth_login.py        初回OAuth認可スクリプト
├── secrets_setup.py     keyring取り込みCLI（import-client / status / delete-*）
├── secrets_store.py     keyringラッパ（service名・get/put/delete）
├── sitemap_to_csv.py    補助: サイトマップから URL一覧 CSV を生成
├── run_server.bat       Windows起動スクリプト（.venv構築 + 起動）
├── run_server.sh        mac/Linux起動スクリプト
├── requirements.txt     直接依存パッケージ（固定版）
├── requirements.lock    起動時に使うロック済み依存パッケージ
├── .env.example         .env のサンプル
└── .env                 識別子のみ。secret は書かない。gitignore済
```
