---
name: "source-command-seo-assemble"
description: "全H2ドラフトを統合し、CMS貼付用の最終Markdown(frontmatter付き)を生成する"
---

# source-command-seo-assemble

Use this skill when the user asks to run the migrated source command `seo-assemble`.

## Command Template

# /seo:assemble — Step 6: 最終統合

`seo-growth-navigator` Skill の **Step 6**。詳細手順は [references/sop.md](../../skills/seo-growth-navigator/references/sop.md) を参照。

## 引数

- `--run <run_id>` (省略可) — 対象 run。省略時は最新

例: `/seo:assemble`

## 実行手順 (要点)

1. **run 特定 & phase 検証**
   - `phase == "drafting"` でなければ停止
   - `run.json.outline.h2s[]` 全件について `drafts[<id>] == "written"` を確認
   - 1件でも `"pending"` なら「{h2-id} が未執筆です」と報告して停止

2. **入力統合**
   - `04-outline.md` から H1 / Meta Description / H2 順序
   - `05-drafts/h2-NN.md` を H2 順序どおりに連結

3. **内部リンク推奨の生成**
   - `recommended_internal_link.from` は **Step 1 で取得した GA4/GSC データに登場した既存URL** に限定
   - 存在しない URL に貼らない
   - 各リンクに「なぜ貼るべきか」をデータ根拠で1行添える

4. **`06-final.md` 出力**
   ```markdown
   ---
   title: <タイトル>
   meta_description: <120-140字>
   target_keyword: <メインKW>
   secondary_keywords:
     - <サブKW1>
     - <サブKW2>
   recommended_internal_link:
     - from: <既存URL>
       to: <新記事スラッグ案>
       anchor_text: <推奨アンカー>
       reason: <データ根拠1行>
   ---

   # <H1 タイトル>

   ## <H2-1>
   ...

   ## <H2-2>
   ...
   ```

5. **run.json 更新**
   - `phase: "done"`
   - `final_path: ".seo/runs/{run_id}/06-final.md"`
   - `updated_at` 更新

## 出力

- ファイル: `.seo/runs/{run_id}/06-final.md`, `run.json`
- チャット: 「`.seo/runs/{run_id}/06-final.md` をCMS下書きに貼り付けてください」

## 守ること

- 全H2が `written` になるまで統合しない
- 内部リンク提案は GA4/GSC データに登場した実在URLに限定。架空ページに貼らない
- frontmatter の数値・KWはすべて MCP 実数 or ユーザー確定値に由来する
- 統合後の追加修正指示が来た場合は、該当 H2 を `/seo:write-section <id>` で書き直してから `/seo:assemble` を再実行する
