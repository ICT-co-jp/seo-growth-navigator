# seo-growth-hacker Skill — 使い方ガイド(人間向け Quick Start)

GA4 / GSC データを根拠に SEO 改善機会を発見し、競合SERPを取得して、記事ドラフトを生成するまでを **1工程=1コマンド** で段階実行する Skill です。

設計思想・脅威モデル・SOP の詳細は [SKILL.md](SKILL.md) と [references/](references/) を参照。本ドキュメントは「**実際に動かすときの操作手順**」だけをまとめます。

---

## 1. 事前準備(初回のみ)

### 1.1 MCP サーバが動くこと

- `mcp_server/` の Google Analytics / Search Console MCP が Claude Desktop に登録済み
- Claude Code 上で `mcp__wpsecurity-analytics__health_check` を呼び、`{"ga4_ok": true, "gsc_ok": true}` が返ること

### 1.2 SERP 取得スクリプトの依存

```cmd
mcp_server\.venv\Scripts\python -m pip install -r mcp_server\requirements.txt
```

確認:

```cmd
mcp_server\.venv\Scripts\python -c "import httpx, selectolax; print('OK')"
```

`OK` が出ればよい。

---

## 2. 起動方法

### 方法A: 自然言語で頼む(推奨)

Claude Code に以下のような依頼を投げると、Skill が自動的に発火します:

> 「GA4とGSCのデータから今月のお宝キーワードを探して、改善記事のドラフトまで作って」

Skill は description のトリガー(「お宝キーワード」「SEO 改善機会」「GA4/GSC データから」等)で起動し、Step 1 から順番に走らせます。

### 方法B: スラッシュコマンドを直接叩く

工程ごとに自分でコマンドを叩く方法。途中再開や1工程だけやり直したいときはこちら。

---

## 3. 工程フロー

```
[1] お宝KW抽出      /seo:find-keywords  [slug]  [--start --end]
        ↓ .seo/runs/{run_id}/01-candidates.md
[2] 対象決定        /seo:select-target  <候補番号>
        ↓ 02-selection.md & run.json 更新
[3] 競合SERP取得    /seo:analyze-serp
        ↓ 03-serp.json + 03-serp-summary.md
[4] 構成案作成      /seo:draft-outline
        ↓ 04-outline.md
[5] H2単位執筆      /seo:write-section  <h2-id>     (複数回)
        ↓ 05-drafts/h2-NN.md
[6] 最終統合        /seo:assemble
        ↓ 06-final.md  (CMS貼付用 frontmatter 付き)
```

各コマンドの引数や前提 phase の詳細は `.claude/commands/seo/*.md` を参照。

---

## 4. 実行例(セッション全体)

```text
[ユーザー]
/seo:find-keywords blog-q2 --start 2026-04-01 --end 2026-04-30

[Claude]
health_check OK。run_id=20260522-1605-blog-q2 で開始します。
GSC位置帯・低CTR・GA4ランディングを並列取得 → 候補3件を 01-candidates.md に出力。
   #1 https://example.com/blog/foo  (想定KW: 〇〇)
   #2 https://example.com/blog/bar  (想定KW: △△)
   #3 https://example.com/blog/baz  (想定KW: □□)
次に /seo:select-target <番号> を叩いてください。

[ユーザー]
/seo:select-target 1

[Claude]
#1 を確定。02-selection.md を出力。次は /seo:analyze-serp。

[ユーザー]
/seo:analyze-serp

[Claude]
fetch_serp.py を起動 → 上位8件取得。
blocked_count>0 のURLが1件あったので分析対象から除外し warnings に記録。
03-serp.json と 03-serp-summary.md を出力。次は /seo:draft-outline。

[ユーザー]
/seo:draft-outline

(以下 /seo:write-section h2-01, h2-02, ... を繰り返し)

[ユーザー]
/seo:assemble

[Claude]
06-final.md を出力。CMS にそのまま貼れる形式です。done フェーズに移行。
```

---

## 5. 中間生成物のレイアウト

```
.seo/runs/20260522-1605-blog-q2/
├── run.json              ← 進行状態の唯一の真実(phase, warnings 等)
├── 01-candidates.md      ← Step 1 の出力(人間可読)
├── 02-selection.md       ← Step 2
├── 03-serp.json          ← Step 3 の生データ(fetch_serp.py)
├── 03-serp-summary.md    ← Step 3 の人間可読要約
├── 04-outline.md         ← Step 4
├── 05-drafts/
│   ├── h2-01.md
│   ├── h2-02.md
│   └── ...
└── 06-final.md           ← Step 6 (CMS貼付用)
```

- `.seo/runs/` は `.gitignore` 済み(コミットされない)
- 古い run は自動削除されないので、不要なら手で消す

---

## 6. 別セッションで再開する

新しい Claude Code セッションで、同じワークディレクトリで:

```
/seo:draft-outline   # 例: outline からやり直したい
```

各コマンドは起動時に `.seo/runs/` 配下から**最新の run_id ディレクトリ**を自動検出し、`run.json` の `phase` をチェックしてから動きます。

特定の run を指定したい場合は `--run <run_id>` 引数を渡せます。

---

## 7. トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| `health_check` が `ga4_ok: false` | MCP サーバの OAuth 期限切れ等 | `mcp_server/auth_login.py` で再認証 |
| `/seo:analyze-serp` で `ModuleNotFoundError: selectolax` | venv に未インストール | §1.2 の `pip install` 実行 |
| `fetch_serp.py` が exit code 2 で停止 | Google が SERP をブロック (429/503) | UA を変更して再試行 (`--user-agent`) または時間を置く |
| `fetch_serp.py` で全件 `fetch_error: true` | ネットワーク疑い | プロキシ・ファイアウォール確認 |
| `blocked_count > 0` が大量 | インジェクション疑い、または偶然キーワードが命令語と一致 | `03-serp.json` の `notes` を見て判断 |
| 数値が「(データなし)」ばかり | GA4/GSC に該当URLのデータが無い | 期間を広げる (`--start --end`)、または別候補を選ぶ |
| 「phase=X です。先に Y を実行してください」 | コマンド順序を飛ばした | 指示通り前工程を実行 |

---

## 8. やってはいけないこと(最上位ルールから)

- **数値の捏造**: 取れなかった数値は「(データなし)」と明示。架空の数値で穴埋めしない。
- **`WebFetch` / `browser_*` での SERP 直接取得**: 必ず `fetch_serp.py` 経由。サニタイズ層を迂回しない。
- **`.env` の中身を読む/書き込む**: 絶対禁止(CLAUDE.md グローバルルール継承)。
- **`.seo/runs/{run_id}/` 以外への書き込み**: ユーザー明示指示がない限り禁止。

詳細は [SKILL.md](SKILL.md) の「最上位ルール」セクションと [references/security-model.md](references/security-model.md) を参照。

---

## 9. 関連ドキュメント

| 読みたいとき | ファイル |
|---|---|
| 設計思想・全体像 | [SKILL.md](SKILL.md) |
| 各工程の詳細SOP | [references/sop.md](references/sop.md) |
| データ捏造禁止の運用 | [references/data-integrity.md](references/data-integrity.md) |
| `fetch_serp.py` の CLI 仕様 | [references/serp-fallback.md](references/serp-fallback.md) |
| run.json スキーマ | [references/run-layout.md](references/run-layout.md) |
| 脅威モデル | [references/security-model.md](references/security-model.md) |
