---
description: H2セクションを執筆して保存する。引数なしで残り全H2を並列執筆、<h2-id>指定で単体執筆
argument-hint: "[<h2-id>] [--run <run_id>]"
---

# /seo:write-section — Step 5: H2執筆(単体 or 並列)

`seo-growth-hacker` Skill の **Step 5**。詳細手順は [references/sop.md](../../skills/seo-growth-hacker/references/sop.md) の Step 5 を参照。
共通の執筆スタイルは [references/writing-style.md](../../skills/seo-growth-hacker/references/writing-style.md) を参照。

## 引数

- `<h2-id>` (省略可) — 指定すると **単体モード**。`04-outline.md` の H2 ID(例: `h2-01`, `h2-02`)
- `--run <run_id>` (省略可) — 対象 run。省略時は最新

例:
- `/seo:write-section` — pending な全 H2 を並列執筆(初回一括執筆向き)
- `/seo:write-section h2-03` — 単体実行(差し戻し・部分書き直し向き)
- `/seo:write-section h2-03 --run 20260522-1605-keyword-research` — run 指定で単体実行

---

## モード判定

| 呼び出し方 | モード |
| --- | --- |
| `<h2-id>` あり | **単体モード**(Step 5-A) |
| `<h2-id>` なし | **並列モード**(Step 5-B) |

---

## 単体モードの実行手順(要点)

1. **run 特定 & phase 検証**
   - `phase ∈ { "outline-ready", "drafting" }` でなければ停止
   - `04-outline.md` から `<h2-id>` のメタ情報を取得。存在しなければエラー報告

2. **執筆**
   - `05-drafts/{h2-id}.md` を出力(対象 H2 1 つ分のみ)
   - スタイルは [writing-style.md](../../skills/seo-growth-hacker/references/writing-style.md) に厳格に従う
   - SERP 要約は**参考**。競合の文章をコピーしない

3. **run.json 更新**
   - `drafts[<h2-id>] = "written"`
   - 最初の H2 が書かれた時点で `phase: "drafting"` に遷移
   - `updated_at` 更新

4. **ユーザーへの案内**
   - 「次は `/seo:write-section <次のh2-id>` を実行してください。残り全部を一括で書くなら `/seo:write-section`(引数なし)で並列実行できます。すべて完了したら `/seo:assemble` で統合します」

---

## 並列モードの実行手順(要点)

詳細とプロンプト構成は [sop.md の Step 5-B](../../skills/seo-growth-hacker/references/sop.md) を参照。

1. **run 特定 & phase 検証**
   - `phase ∈ { "outline-ready", "drafting" }` でなければ停止
   - `run.json.outline.h2s[]` のうち `drafts[id] == "pending"` の一覧を抽出
   - 全 H2 が既に `written` なら「全 H2 執筆済みです。`/seo:assemble` を実行してください」で停止

2. **H2-01 を親が直列で執筆**(pending に `h2-01` が含まれる場合のみ)
   - 単体モードと同じ手順で `05-drafts/h2-01.md` を出力
   - **`run.json` はまだ更新しない**(並列完了後の一括更新で同時に反映するため)
   - 後続サブエージェントにとっての**文体見本**になるので writing-style.md に厳格に従う

3. **規模チェック**
   - pending な H2 が **10 個を超える** 場合、起動前に 1 行注意喚起: 「H2 が N 個あります。並列実行するとレート制限・コスト増の可能性があります」

4. **残りの H2 をすべて並列起動**
   - `Agent` ツールを **1 メッセージ内に複数並べて同時呼び出し**(=並列)
   - `subagent_type: "general-purpose"`
   - 各 Agent に渡すプロンプトの構成は [sop.md の Step 5-B 手順 3](../../skills/seo-growth-hacker/references/sop.md) に従う:
     - 担当 H2 のメタ情報(id, 見出し, 要点, H3 構造)
     - 書かない範囲(他 H2 のタイトルと要点)
     - SERP 要約(`03-serp-summary.md`)
     - 文体見本(`05-drafts/h2-01.md` の本文)
     - 共通スタイル([writing-style.md](../../skills/seo-growth-hacker/references/writing-style.md) 全文)
     - データ整合性ルール([data-integrity.md](../../skills/seo-growth-hacker/references/data-integrity.md))
     - 出力先: `.seo/runs/{run_id}/05-drafts/{h2-id}.md`
     - 禁止事項: `run.json` 変更禁止 / MCP ツール呼び出し禁止 / `fetch_serp.py` 実行禁止 / ネットワーク取得禁止 / 他 H2 への言及禁止
     - 完了報告: 出力パス + 文字数

5. **完了集約 & 検証**
   - 全 Agent の戻りを受け取った後、各 `05-drafts/{h2-id}.md` を Read で存在確認
   - 欠落・空ファイルは `failed_ids` リストに集約

6. **`run.json` 一括更新**(親が単独で実施)
   - 成功した H2 をまとめて `drafts[id] = "written"`
   - `phase: "drafting"`、`updated_at` 更新
   - 失敗 H2 は `pending` のまま残す(冪等な再開のため)

7. **ユーザーへの案内**
   - 全成功: 「すべての H2 を執筆しました。`/seo:assemble` で統合してください」
   - 部分失敗: 「次の H2 が書けませんでした: <id 一覧>。`/seo:write-section <id>` で個別に書き直すか、もう一度 `/seo:write-section`(引数なし)で再実行できます」

---

## 出力

- ファイル: `.seo/runs/{run_id}/05-drafts/{h2-id}.md`(単体は 1 ファイル、並列は N ファイル)、`run.json`
- チャット: 次工程への案内 1〜2 行

---

## 守ること

- **単体モードでは指定された 1 つの H2 だけ書く**(複数まとめて書かない)
- **並列モードのサブエージェントは `run.json` を絶対に変更しない**(レース回避のため親が一括更新)
- 同じ `<h2-id>` で単体モードを再実行された場合は上書き(差し戻し対応)
- 数値は MCP 実数のみ([data-integrity.md](../../skills/seo-growth-hacker/references/data-integrity.md))
- 並列モードでサブエージェントから返ってきた本文を親が改変しない(品質コントロールは writing-style.md とプロンプトで担保し、再実行で対応する)
