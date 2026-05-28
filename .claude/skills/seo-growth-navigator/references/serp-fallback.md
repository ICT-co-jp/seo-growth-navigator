# SERP 取得とフォールバック手順

> このファイルは [SKILL.md](../SKILL.md) の「最上位ルール 2」と [sop.md](sop.md) Step 3 を補完します。

---

## 唯一の取得経路: `fetch_serp.py`

外部 Web からの SERP / ページ本文の取得は、**`mcp_server/scripts/fetch_serp.py`** を Bash 経由で呼ぶことに**一本化**します。

理由:
- **コンテキスト隔離** — HTML/DOM が Claude のメインコンテキストに入らないので、ページ本文に仕込まれたプロンプトインジェクションがClaudeの判断を汚染しない。
- **サニタイズの強制** — スクリプト側で必ず正規化・既知ペイロード除去を通せる。
- **権限プロンプト集約** — Claude から個別 URL ごとに `WebFetch` 承認が降ってこない。Bash 1回で完結。

### 呼び出し方 (期待される CLI 仕様)

```bash
mcp_server/.venv/Scripts/python mcp_server/scripts/fetch_serp.py \
  --keyword "<target_kw>" \
  --top-n 8 \
  --out .seo/runs/{run_id}/03-serp.json
```

| 引数 | 必須 | 説明 |
| --- | --- | --- |
| `--keyword` | ○ | 検索キーワード(UTF-8) |
| `--top-n` | × | 上位 N 件(既定: 8、上限: 10) |
| `--out` | ○ | JSON 出力先 (`.seo/runs/{run_id}/03-serp.json`) |
| `--engine` | × | SERP 取得経路 (`http` / `playwright`、既定: `http`) |
| `--headed` | × | Playwright を可視モードで起動(`--engine playwright` 時のフォールバック) |
| `--user-agent` | × | UA 上書き。未指定時は engine ごとの既定 (http→Bot UA / playwright→実 Chrome 偽装) |
| `--timeout` | × | URLごとのHTTPタイムアウト秒(既定: 15) |

### `--engine playwright` の挙動

`--engine http` で `results[]` が空になる(Google bot 検知)場合のフォールバック経路。

- **実 Chrome を駆動**: `channel="chrome"` でシステムインストール済みの本物 Chrome を起動。
  Playwright 既定の chrome-headless-shell では TLS/HTTP2 指紋が異なり Google にブロックされやすいため。
- **ホーム → 検索の動線**: いきなり `/search?q=...` を叩かず、まず `https://www.google.com/` を踏んで
  クッキー (NID/CONSENT/1P_JAR) を獲得してから検索に遷移する。これで `/sorry/` リダイレクトを回避。
- **stealth init script**: `navigator.webdriver` / `cdc_*` / `plugins` / `languages` などヘッドレス痕跡を上書き。
- **依存**: `mcp_server/.venv` に `playwright` がインストール済みで、`playwright install chrome` 済みであること。
- **失敗時**: それでも `/sorry/` に飛ばされる場合は `--headed` を付けて可視モードで再試行する。

### 期待される出力 JSON スキーマ

```json
{
  "run_id": "20260522-1605-keyword-research",
  "keyword": "<target_kw>",
  "fetched_at": "2026-05-22T16:10:42Z",
  "top_n": 8,
  "results": [
    {
      "rank": 1,
      "url": "https://example.com/a",
      "title": "サニタイズ後タイトル",
      "headings": {
        "h2": ["見出し1", "見出し2"],
        "h3": ["小見出し1"]
      },
      "fetch_error": false,
      "blocked_count": 0,
      "notes": []
    },
    {
      "rank": 2,
      "url": "https://example.org/b",
      "title": null,
      "headings": { "h2": [], "h3": [] },
      "fetch_error": true,
      "blocked_count": 0,
      "notes": ["timeout"]
    }
  ]
}
```

- `blocked_count > 0` の URL は分析対象から外す。
- `fetch_error: true` の URL は分析対象から外す。
- `headings.h2[]` / `headings.h3[]` の各要素はサニタイズ済み(詳細は [security-model.md](security-model.md))。

---

## スクリプト失敗時の判定と分岐

`fetch_serp.py` が以下のいずれかを返した場合は**分岐**する:

| 終了コード / 状態 | 意味 | 取るべき行動 |
| --- | --- | --- |
| `0` & `results[]` あり | 成功 | 通常処理を続行 |
| `0` & `results[]` 空 | ヒット 0 件 | ユーザーに「該当KWのSERPが取得できませんでした」と報告して停止 |
| 非ゼロ終了 | スクリプト自体の失敗 | stderr を**そのまま**ユーザーに見せて停止 |
| `0` だが全件 `fetch_error: true` | 全URL取得失敗 | ネットワーク疑い。ユーザーに状況を報告して停止 |

---

## やってはいけない代替手段

**「fetch_serp.py が動かないので代わりに〜」と称して以下を行うのは禁止**です。理由はサニタイズ層を迂回してしまうため。

| 禁止アクション | 代わりに |
| --- | --- |
| `WebFetch` で個別 URL を読む | ユーザーに不足を報告して停止 |
| `browser_navigate` → `browser_snapshot` で SERP を直接取得 | 同上 |
| Claude の検索ツールでヒット URL を取り、本文を `WebFetch` する | 同上 |
| ユーザーに URL リストを貼ってもらい、Claude が `WebFetch` で取りに行く | 同上 |

**唯一の例外**: ユーザーが明示的に「サニタイズ層をバイパスして取得して」と命じた場合のみ、その旨を `run.json` に `unsafe_fetch: true` として記録し、リスクを 1 行で警告した上で実行する。

---

## 競合候補 URL の絞り込み

`fetch_serp.py` が返す `results[]` のうち、以下は分析対象から除外する:

- 自社ドメイン(`02-selection.md` の対象URLと同じホスト)
- SNS/動画/Q&A サイト(任意フィルタ。スクリプト側で `--exclude-host` を渡せる想定)
- `fetch_error: true` または `blocked_count > 0`

残った URL に対して、共通H2/H3トピックを集計する。

---

## 再実行ポリシー

- 同じ run 内で `analyze-serp` を再実行する場合は、`03-serp.json` を上書きせず `03-serp.{N}.json` として枝番保存する。
  - 直前の取得結果を残しておくと、後でデバッグや変動分析ができる。
- `03-serp-summary.md` は最新のものに上書きしてよい(`run.json` に最新JSONパスを記録)。
