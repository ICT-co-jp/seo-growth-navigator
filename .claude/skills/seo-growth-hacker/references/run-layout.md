# `.seo/runs/` ディレクトリ規約と run.json スキーマ

> このファイルは [SKILL.md](../SKILL.md) と [sop.md](sop.md) の永続化レイヤーを定義します。

---

## なぜディレクトリ永続化するのか

旧サブエージェント版は**チャット出力のみ**で成果物を返していたため:

- セッションを跨いで再開できない(コンテキスト消失)
- 途中で失敗すると最初からやり直し
- 中間生成物(SERP取得結果、Hごとのドラフト)が散逸

Skill 版ではすべての中間生成物を **`.seo/runs/{run_id}/`** に書き、`run.json` で進行状態を**機械可読**にする。これにより:

- 別セッションでも `/seo:<次のコマンド>` を叩けば続きから再開可能
- ユーザーが中間ファイルを直接編集して差し戻しできる
- 監査(誰がいつ何を生成したか)が可能

---

## run_id 規約

形式: `{YYYYMMDD-HHMM}-{slug}`

| 部分 | 例 | 説明 |
| --- | --- | --- |
| `YYYYMMDD-HHMM` | `20260522-1605` | run 開始時刻(ローカルタイム / `/seo:find-keywords` 起動時に確定) |
| `slug` | `keyword-research` | 短い識別子。引数省略時は `auto`。スペース不可、kebab-case |

例: `20260522-1605-keyword-research` / `20260522-1605-auto`

---

## ディレクトリレイアウト

```
.seo/
└── runs/
    └── 20260522-1605-keyword-research/
        ├── run.json                 # 進行状態の唯一の真実
        ├── 01-candidates.md         # /seo:find-keywords の出力
        ├── 02-selection.md          # /seo:select-target の出力
        ├── 03-serp.json             # fetch_serp.py の生出力(機械可読)
        ├── 03-serp.{N}.json         # 再実行時の枝番(任意)
        ├── 03-serp-summary.md       # /seo:analyze-serp の要約(人間可読)
        ├── 04-outline.md            # /seo:draft-outline の出力
        ├── 05-drafts/
        │   ├── h2-01.md             # /seo:write-section h2-01
        │   ├── h2-02.md
        │   └── ...
        └── 06-final.md              # /seo:assemble の最終出力(CMS貼付用)
```

### 命名規則

- ファイル名は**ゼロパディング**でソート可能に(`h2-01`, `h2-02`, ..., `h2-10`)
- run.json と `06-final.md` 以外は**追記/上書きせず再生成**を基本とする(例外: `05-drafts/h2-NN.md` はユーザー修正指示時に上書き可)

---

## run.json スキーマ

`run.json` は run 全体の進行状態を保持する**唯一の真実**。各コマンドは自分の工程の出力後に必ず更新する。

```json
{
  "run_id": "20260522-1605-keyword-research",
  "phase": "outline-ready",
  "started_at": "2026-05-22T16:05:00Z",
  "updated_at": "2026-05-22T16:42:18Z",
  "period": {
    "start_date": "2026-04-22",
    "end_date": "2026-05-19"
  },
  "candidates": [
    {
      "index": 1,
      "url": "https://example.com/blog/post-a",
      "type": ["A", "C"],
      "target_kw": "想定キーワードA",
      "evidence": {
        "impressions": 1234,
        "ctr": 0.012,
        "position": 7.4,
        "engagement_rate": 0.38
      }
    }
  ],
  "selected": {
    "index": 1,
    "url": "https://example.com/blog/post-a",
    "target_kw": "想定キーワードA",
    "sub_kws": ["サブKW1", "サブKW2"]
  },
  "serp": {
    "json_path": ".seo/runs/20260522-1605-keyword-research/03-serp.json",
    "fetched": 7,
    "blocked": 0,
    "failed": 1
  },
  "outline": {
    "title": "<H1 タイトル案>",
    "meta_description": "<120-140字>",
    "h2s": [
      { "id": "h2-01", "title": "見出し1" },
      { "id": "h2-02", "title": "見出し2" }
    ]
  },
  "drafts": {
    "h2-01": "written",
    "h2-02": "pending"
  },
  "final_path": null,
  "warnings": []
}
```

### `phase` の列挙

進行は以下の順序で進む。**前の phase が完了していないと次に進めない**。

| phase | 完了条件 | 次に叩くコマンド |
| --- | --- | --- |
| `find-keywords` | 初期化のみ(run.jsonが存在) | (進行中) |
| `candidates-ready` | `01-candidates.md` 出力済 | `/seo:select-target` |
| `target-selected` | `02-selection.md` 出力済 | `/seo:analyze-serp` |
| `serp-analyzed` | `03-serp.json` & `03-serp-summary.md` 出力済 | `/seo:draft-outline` |
| `outline-ready` | `04-outline.md` 出力済 | `/seo:write-section h2-01` |
| `drafting` | 最初のH2が `written` になった時点 | `/seo:write-section <次>` |
| `done` | `06-final.md` 出力済 | (完了) |

### `warnings[]`

- 各コマンドが検出した非致命警告を蓄積する。例:
  - `"SERP取得で example.org が __BLOCKED__"`
  - `"GA4のengagement_rateが取得できないURLが2件"`

---

## 各コマンドの run.json 更新責務

| コマンド | phase 更新後 | 必須フィールド更新 |
| --- | --- | --- |
| `/seo:find-keywords` | `candidates-ready` | `period`, `candidates[]` |
| `/seo:select-target` | `target-selected` | `selected` |
| `/seo:analyze-serp` | `serp-analyzed` | `serp` |
| `/seo:draft-outline` | `outline-ready` | `outline` |
| `/seo:write-section` | (現状維持/`drafting`) | `drafts[<h2-id>]` |
| `/seo:assemble` | `done` | `final_path` |

更新時は必ず `updated_at` も同時に書き換える。

---

## 既存 run の確認

各 `/seo:*` コマンドは起動時に:

1. カレントディレクトリ直下の `.seo/runs/` 配下に**最新の run_id ディレクトリ**を探す。
2. `run.json` を読み、自分の前提となる `phase` であることを確認。
3. `phase` が不整合なら、ユーザーに「現在は phase=X です。先に Y を実行してください」と報告して停止。

ユーザーが特定の run を指定したい場合は引数 `--run <run_id>` を許容する(各コマンドの実装で対応)。

---

## クリーンアップ

- `.seo/runs/` 配下は git 管理しない(`.gitignore` で除外)
- 古い run の自動削除は**しない**(ユーザーの明示的な削除に任せる)
