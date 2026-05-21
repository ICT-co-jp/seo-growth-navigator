# GA4 / Search Console MCP サーバ

Google Analytics 4 と Google Search Console のデータを、Claude Desktop から自然言語で
取り出せるようにする **ローカル MCP サーバ** です。

- リライト候補や CTR 改善候補を Claude に聞くだけで返ってくる
- レポート画面や API のことを覚えなくて良い
- データは Google アカウントの権限の範囲でしか取得されません
- セットアップに **コマンドライン操作は不要**(`.env` をメモ帳で編集するだけ)

> 認証情報(`.env` の中身)は共有・公開はしないでください。

---

## できること

| 関数名 | 何が分かるか |
|---|---|
| `ga4_run_report` | 任意のディメンション/指標で集計(汎用) |
| `ga4_top_pages` | 期間内の PV 上位ページ |
| `ga4_landing_pages` | ランディングページ別の流入と回遊指標 |
| `ga4_traffic_sources` | チャネル別の流入 |
| `ga4_returning_users` | 新規ユーザー / 再訪ユーザーの比率 |
| `gsc_search_analytics` | 任意ディメンションで集計(汎用) |
| `gsc_top_queries` | クリック上位の検索クエリ |
| `gsc_page_queries` | 指定 URL のクエリ別 CTR・順位 |
| `gsc_low_ctr_pages` | 表示は多いが CTR が低い改善候補 |
| `gsc_position_window` | 平均掲載順位 4〜15 位の浮上候補ページ |
| `health_check` | 設定値と疎通確認 |

---

## 動作要件

- Windows 10 / 11、または macOS
- **Python 3.11 以上** がインストール済み
  - Windows: https://www.python.org/downloads/windows/ から入手
  - Mac: `python3 --version` で 3.11 以上ならそのまま使えます
- Claude Desktop アプリ (https://claude.ai/download)
- 操作したい GA4 プロパティと Search Console プロパティへの閲覧権限がある Google アカウント

> Python のコマンドを自分で叩く必要はありません。インストールだけしておけば OK です。

---

## セットアップ手順

全体の流れは以下の通りです。**5〜15 分** ほどで完了します。

1. Google Cloud で「OAuth 認証情報」を 1 つ作成する
2. Google OAuth Playground でリフレッシュトークンを取得する
3. `.env` ファイルに 5 つの値を貼り付ける
4. Claude Desktop に MCP サーバを登録する

---

### ステップ 1. Google Cloud で OAuth クライアントを作成する

GA4 / Search Console の API を使う「鍵」を作ります。

1. https://console.cloud.google.com/ にログインする。
2. 画面上部のプロジェクト選択メニューから、任意のプロジェクトを選ぶ
   (無ければ「新しいプロジェクト」を作る)。
3. 検索バーに「**ライブラリ**」と入れ、以下 2 つの API を「有効にする」:
   - **Google Analytics Data API**
   - **Google Search Console API**
4. 検索バーに「**OAuth 同意画面**」と入れて開き、まだ作っていなければ
   ユーザータイプ「**外部**」で作成。アプリ名は何でも構いません。
   - テストユーザーに、自分の Google アカウントを追加してください。
5. 検索バーに「**認証情報**」と入れて開き、上部の
   「**+ 認証情報を作成**」 → 「**OAuth クライアント ID**」を選ぶ。
6. アプリケーションの種類: **「ウェブ アプリケーション」** を選択。
7. 「**承認済みのリダイレクト URI**」に以下を 1 行追加:
   ```
   https://developers.google.com/oauthplayground
   ```
8. 「作成」を押すと、**クライアント ID** と **クライアント シークレット** が
   表示されます。両方コピーして手元のメモに保存してください。

> ⚠️ クライアントシークレットは外部に漏らさないでください。
> 万が一漏れた場合は、認証情報の画面から「削除」して作り直してください。

---

### ステップ 2. Google OAuth Playground でリフレッシュトークンを取得する

Google が公式に提供している Web ツールを使います。ブラウザだけで完結します。

1. https://developers.google.com/oauthplayground/ をブラウザで開く。
2. 画面右上の歯車アイコン ⚙ をクリックして「**OAuth 2.0 configuration**」を開く。
3. 「**Use your own OAuth credentials**」のチェックを **ON** にする。
4. ステップ 1 で取得した **OAuth Client ID** と **OAuth Client secret** を貼り付け、
   歯車を閉じる。
5. 左側の「Step 1: Select & authorize APIs」の入力欄に、以下を **1 つずつ** 貼って
   「Authorize APIs」ボタンを押す前にスコープリストに追加:
   ```
   https://www.googleapis.com/auth/analytics.readonly
   https://www.googleapis.com/auth/webmasters.readonly
   ```
   (左側の API ツリーから「Google Analytics Data API v1 → ...readonly」と
    「Search Console API → ...readonly」を選んでも構いません)
6. 「**Authorize APIs**」ボタンを押す → Google のログイン画面でアカウント選択
   → 「許可」を押す。
7. Playground 画面に戻ったら「**Exchange authorization code for tokens**」を押す。
8. 右側に表示される「**Refresh token**」(例: `1//0g...`)をコピーする。

> このリフレッシュトークンは「鍵」のように使うので、ここでメモしておきます。
> 後から見直しはできません(再取得は可能)。

---

### ステップ 3. `.env` ファイルを作成して値を貼り付ける

1. `mcp_server` フォルダ内の **`.env.example`** をコピーし、
   コピーしたファイル名を **`.env`** に変更する。
   - Windows エクスプローラーで「.env.example」を右クリック → コピー → 貼り付け
     → 名前を `.env` に変更。
   - 「拡張子が変わります」と聞かれたら「はい」。
2. メモ帳(または好きなテキストエディタ)で `.env` を開く。
3. 以下の 5 項目を埋める:

   | キー | 何を入れる |
   |---|---|
   | `GA4_PROPERTY_ID` | GA4 管理画面 → プロパティ設定 → プロパティ ID(数字のみ) |
   | `GSC_SITE_URL` | Search Console の対象サイト(下記参照) |
   | `GOOGLE_CLIENT_ID` | ステップ 1 でコピーした OAuth Client ID |
   | `GOOGLE_CLIENT_SECRET` | ステップ 1 でコピーした OAuth Client secret |
   | `GOOGLE_REFRESH_TOKEN` | ステップ 2 でコピーした Refresh token |

   `GSC_SITE_URL` の書き方:
   - ドメインプロパティの場合: `sc-domain:example.com`
   - URL プレフィックスの場合: `https://example.com/`(末尾スラッシュ必須)

4. 上書き保存して閉じる。

> `.env` は **絶対に Git へコミットしたり、他人に共有したりしない** でください。
> 中身が漏れると、あなたの GA4 / Search Console データが第三者に読まれる恐れがあります。

---

### ステップ 4. Claude Desktop に MCP サーバを登録する

Claude Desktop の設定ファイルに、このサーバを追記します。

1. Claude Desktop を起動して、メニューから
   **「設定(Settings)」 → 「開発者(Developer)」 → 「設定ファイルを編集」** を開く。
   - 直接ファイルを開く場合のパス:
     - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
     - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. `mcpServers` セクションに以下を追記する(キー名 `ga4-gsc` は任意):

   **Windows の場合:**
   ```json
   {
     "mcpServers": {
       "ga4-gsc": {
         "command": "C:\\path\\to\\mcp_server\\run_server.bat"
       }
     }
   }
   ```

   **Mac の場合:**
   ```json
   {
     "mcpServers": {
       "ga4-gsc": {
         "command": "/absolute/path/to/mcp_server/run_server.sh"
       }
     }
   }
   ```

   `path` の部分は、この `mcp_server` フォルダの実際の絶対パスに置き換えてください。
   Windows のパス区切りはバックスラッシュ 2 つ (`\\`) です。

3. 保存して、Claude Desktop を **完全に終了 → 再起動** する。
   (タスクトレイから終了するまで完全には閉じません。)

4. Claude Desktop の入力欄左下に 🔌 アイコンが出ていれば成功です。
   `ga4-gsc` という名前で接続されているか確認してください。

---

## 動作確認

Claude Desktop に以下のように打ち込んでみてください。

```
health_check を実行して
```

応答の中の `ga4_ok` と `gsc_ok` が **両方 true** ならセットアップ完了です。
`refresh_token_set` / `client_id_set` / `client_secret_set` などもチェック用に
含まれています。

その後、たとえばこういう聞き方ができます:

- 「GA4 で直近 28 日のページビュー上位 20 件を出して」
- 「Search Console で CTR が低くて表示数が多い改善候補を出して」
- 「平均掲載順位が 4〜15 位のページを出して。1 ページ目に押し上げたい」

---

## トラブルシュート

| 症状 | 原因と対処 |
|---|---|
| `.env に必須項目がありません` | `.env` の値が空。ステップ 3 を見直してください。 |
| `OAuth トークンが無効です` 等 | リフレッシュトークンが期限切れ・失効。ステップ 2 を再度実行して `GOOGLE_REFRESH_TOKEN` を貼り直してください。 |
| `403 PERMISSION_DENIED` | 認可したアカウントが、GA4 や Search Console の対象プロパティに **閲覧権限以上** で追加されていません。GA4 / Search Console の管理画面で追加してください。 |
| `quota project ... not enabled` | API が有効になっていない可能性。GCP コンソールでステップ 1 の 2 API が「有効」になっているか確認。改善しない場合のみ `.env` の `GOOGLE_QUOTA_PROJECT` に OAuth クライアントを作った GCP プロジェクト ID を設定してください。 |
| `siteUrl ... not found` | `GSC_SITE_URL` の書式が違います。ドメインプロパティは `sc-domain:` を付ける必要があります。 |
| Claude Desktop に 🔌 アイコンが出ない | `claude_desktop_config.json` の JSON 文法エラーが多いです。{} と "" の対応を確認。Windows ではパス区切りを `\\` にしてください。 |
| 起動するが何も返らない | `MCP_DEBUG=1` を `.env` に設定して `run_server.bat` を手動でダブルクリックすると、ターミナルにエラーが表示されます。 |

---

## ファイル構成

| ファイル | 役割 |
|---|---|
| `server.py` | MCP サーバ本体。GA4 / Search Console を呼ぶ Python コード。 |
| `.env.example` | `.env` の雛形。コピーして使ってください。 |
| `.env` | あなたの設定値(コピー後に編集。Git にコミット禁止)。 |
| `requirements.txt` | Python 依存パッケージリスト。起動時に自動インストールされます。 |
| `run_server.bat` | Windows 用起動スクリプト。初回起動時に Python の仮想環境を自動構築。 |
| `run_server.sh` | Mac / Linux 用起動スクリプト。 |
| `sitemap_to_csv.py` | (おまけ) サイトマップから URL 一覧を CSV にダンプするユーティリティ。 |

---

## アンインストール / リセット

- このサーバを使うのをやめたい場合: `claude_desktop_config.json` から
  `ga4-gsc` のセクションを削除すれば OK。
- 認証だけリセットしたい場合: `.env` の `GOOGLE_REFRESH_TOKEN` を消し、
  ステップ 2 をやり直す。
- 完全に消す場合: `mcp_server` フォルダを削除。Google Cloud 側の OAuth クライアントも
  不要なら削除してください。
