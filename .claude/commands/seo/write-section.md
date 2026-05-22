---
description: 1つのH2セクションだけを執筆して保存する。複数まとめて書かない
argument-hint: "<h2-id> [--run <run_id>]"
---

# /seo:write-section — Step 5: H2単位執筆

`seo-growth-hacker` Skill の **Step 5**。詳細手順は [references/sop.md](../../skills/seo-growth-hacker/references/sop.md) を参照。

## 引数

- `<h2-id>` (必須) — `04-outline.md` の H2 ID(例: `h2-01`, `h2-02`)
- `--run <run_id>` (省略可) — 対象 run。省略時は最新

例: `/seo:write-section h2-01`  `/seo:write-section h2-03 --run 20260522-1605-keyword-research`

## 実行手順 (要点)

1. **run 特定 & phase 検証**
   - `phase ∈ { "outline-ready", "drafting" }` でなければ停止
   - `04-outline.md` から `<h2-id>` のメタ情報を取得。存在しなければエラー報告

2. **執筆**
   - `05-drafts/{h2-id}.md` を出力(対象 H2 1つ分のみ)
   - 構造: `## <H2 見出し>` → 本文 → `### <H3 見出し>` → 本文 ...
   - 目安: 600〜1000字 / H2(最低400字)
   - 表・箇条書きを適切に使い読みやすく
   - 不確実な数字を書かない。必要な場合は `(要出典)` と明示
   - SERP要約は**参考**。競合の文章をコピーしない

3. **run.json 更新**
   - `drafts[<h2-id>] = "written"`
   - 最初のH2が書かれた時点で `phase: "drafting"` に遷移
   - `updated_at` 更新

## 出力

- ファイル: `.seo/runs/{run_id}/05-drafts/{h2-id}.md`, `run.json`
- チャット: 執筆完了の通知と「次は `/seo:write-section <次のh2-id>` を実行してください。全H2完了後は `/seo:assemble` で統合します」

## 守ること

- **1コマンドで複数H2を書かない**。`<h2-id>` で指定された1つだけ
- 同じ `<h2-id>` で再実行された場合は上書き(ユーザーの差し戻し対応)
- 数値はMCP実数のみ([data-integrity.md](../../skills/seo-growth-hacker/references/data-integrity.md))
