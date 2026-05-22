---
description: SERP要約と検索意図から「勝てる構成案」を作成する
argument-hint: "[--run <run_id>]"
---

# /seo:draft-outline — Step 4: 構成案作成

`seo-growth-hacker` Skill の **Step 4**。詳細手順は [references/sop.md](../../skills/seo-growth-hacker/references/sop.md) を参照。

## 引数

- `--run <run_id>` (省略可) — 対象 run。省略時は最新

例: `/seo:draft-outline`

## 実行手順 (要点)

1. **run 特定 & phase 検証**
   - `phase == "serp-analyzed"` でなければ停止

2. **入力読み込み**
   - `02-selection.md` から ターゲットKW・サブKW・検索意図仮説
   - `03-serp-summary.md` から 共通トピック・カバーされていない観点

3. **構成設計**
   - 競合カバー済みトピック × 検索意図の充足度を整理
   - 競合がカバーしていないが重要な観点(One True Outline 的視点)を抽出
   - H1 / Meta Description / H2 群 / 各H2配下のH3群を設計

4. **`04-outline.md` 出力**
   ```markdown
   # 構成案 (run_id: {run_id})

   - H1: <タイトル案>
   - Meta Description (120-140字): <案>

   ## H2-1: <見出し> [id: h2-01]
   - 要点(1-2行)
   - ### H3-1-1: ...
   - ### H3-1-2: ...

   ## H2-2: <見出し> [id: h2-02]
   ...
   ```
   - 各H2に**安定したID**(`h2-01`, `h2-02`, ...)をゼロパディングで付与
   - これが `/seo:write-section` の引数になる

5. **run.json 更新**
   - `phase: "outline-ready"`
   - `outline: { title, meta_description, h2s: [{ id, title }, ...] }`
   - `drafts: { "h2-01": "pending", "h2-02": "pending", ... }`
   - `updated_at` 更新

## 出力

- ファイル: `.seo/runs/{run_id}/04-outline.md`, `run.json`
- チャット: H2 リストと「次は `/seo:write-section h2-01` から順に実行してください」

## 守ること

- 競合の見出しを**コピーしない**(参考であって複写ではない)
- 数値や事実をアウトラインに書く必要が出た場合は MCP データの実数を使う
- 検索意図仮説と外れたH2を立てない
