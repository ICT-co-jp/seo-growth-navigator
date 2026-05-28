---
name: "source-command-seo-select-target"
description: "候補一覧から1件を選択して対象を確定する"
---

# source-command-seo-select-target

Use this skill when the user asks to run the migrated source command `seo-select-target`.

## Command Template

# /seo:select-target — Step 2: 対象決定

`seo-growth-navigator` Skill の **Step 2**。詳細手順は [references/sop.md](../../skills/seo-growth-navigator/references/sop.md) を参照。

## 引数

- `<候補番号>` (必須) — `01-candidates.md` の候補番号(1, 2, 3 ...)
- `--run <run_id>` (省略可) — 対象 run。省略時は `.seo/runs/` 配下の最新

例: `/seo:select-target 1`  `/seo:select-target 2 --run 20260522-1605-keyword-research`

## 実行手順 (要点)

1. **run 特定 & phase 検証**
   - 引数の `--run` か最新ディレクトリから `run.json` を読む
   - `phase == "candidates-ready"` でなければ停止し、現在の phase を報告
   - 候補番号が `candidates[]` の範囲内か検証

2. **必要に応じてクエリ詳細を追加取得**
   - `mcp__wpsecurity-analytics__gsc_page_queries` (`page=<選択URL>`)
   - サブKW候補(impressions / ctr / position 実数付き)を抽出

3. **`02-selection.md` 出力**
   ```markdown
   # 選択候補 (run_id: {run_id})

   - 対象URL: <URL>
   - メインKW: <KW>
   - サブKW候補:
     - <query>: impressions=X, ctr=Y%, position=Z
   - 検索意図仮説: <情報収集/比較/購入直前> + 根拠1行
   ```

4. **run.json 更新**
   - `phase: "target-selected"`
   - `selected: { index, url, target_kw, sub_kws: [...] }`
   - `updated_at` 更新

## 出力

- ファイル: `.seo/runs/{run_id}/02-selection.md`, `run.json`
- チャット: 確定内容のサマリと「次は `/seo:analyze-serp` を実行してください」

## 守ること

- 数値はMCP実数のみ。サブKWの数値も同様
- 範囲外番号や phase 不整合は停止して報告。勝手に補正しない
