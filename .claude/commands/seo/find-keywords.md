---
description: GA4/GSCデータから「お宝KW」候補を1〜3件抽出し、新しい run を開始する
argument-hint: "[slug] [--start YYYY-MM-DD --end YYYY-MM-DD]"
---

# /seo:find-keywords — Step 1: お宝KW抽出

`seo-growth-hacker` Skill の **Step 1** を実行します。詳細手順は [references/sop.md](../../skills/seo-growth-hacker/references/sop.md) を参照。

## 引数

- `slug` (省略可) — run_id の末尾識別子(kebab-case)。省略時は `auto`
- `--start YYYY-MM-DD` / `--end YYYY-MM-DD` (省略可) — 集計期間。省略時は直近28日(MCP既定)

例: `/seo:find-keywords keyword-research`  `/seo:find-keywords blog-q2 --start 2026-04-01 --end 2026-04-30`

## 実行手順 (要点)

1. **前提チェック**
   - `mcp__wpsecurity-analytics__health_check` を呼び、`ga4_ok: true, gsc_ok: true` を確認。失敗なら停止しユーザー報告。

2. **run_id 発行 & 初期化**
   - 形式: `{YYYYMMDD-HHMM}-{slug}` (slug 省略時は `auto`)
   - `.seo/runs/{run_id}/run.json` を作成:
     ```json
     {
       "run_id": "{run_id}",
       "phase": "find-keywords",
       "started_at": "<ISO8601 UTC>",
       "updated_at": "<同上>",
       "period": { "start_date": "...", "end_date": "..." },
       "candidates": [],
       "warnings": []
     }
     ```

3. **MCP データ取得** (並列実行可)
   - `gsc_position_window` (`min_position=4, max_position=15, min_impressions=200`)
   - `gsc_low_ctr_pages` (`min_impressions=500, max_ctr=0.02`)
   - `ga4_landing_pages` (`limit=50`)

4. **URL名寄せ & タイプ分類** (詳細: [data-integrity.md](../../skills/seo-growth-hacker/references/data-integrity.md))
   - タイプA: 順位浮上型 / タイプB: CTR改善型 / タイプC: 離脱解消型

5. **`.seo/runs/{run_id}/01-candidates.md` 出力**
   - 候補 1〜3 件。各候補に impressions / ctr / position / engagement_rate を**実数で**記載
   - データ欠損は「(データなし)」と明示

6. **run.json 更新**
   - `phase: "candidates-ready"`、`candidates: [{ index, url, type, target_kw, evidence }]`、`updated_at`

## 出力

- ファイル: `.seo/runs/{run_id}/01-candidates.md`, `.seo/runs/{run_id}/run.json`
- チャット: 候補サマリと「次は `/seo:select-target <番号>` で1件選んでください」

## 守ること

- **数値はMCP実数のみ**(`data-integrity.md`)
- 一度に複数Stepを進めない。Step 1 完了で停止
- 書き込み先は `.seo/runs/{run_id}/` 配下に限定
