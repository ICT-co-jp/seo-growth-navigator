# `.claude/agents/` — サブエージェント取扱説明書

このフォルダには、本リポジトリ専用の Claude Code サブエージェント定義が入っています。
ファイル名がそのまま `subagent_type`(エージェント名)として利用されます。

| ファイル | エージェント名 | 役割 |
| --- | --- | --- |
| `seo-growth-hacker.md` | `seo-growth-hacker` | GA4 / GSC データを根拠にお宝KWを発見し、SOP に沿って SEO 記事ドラフトを段階的に生成 |

---

## `seo-growth-hacker` の使い方

### 1. 前提条件

このエージェントは `mcp_server/server.py` が提供する MCP ツール群を必須で利用します。
**起動前に以下が満たされていることを確認してください。**

| 項目 | 確認方法 |
| --- | --- |
| `mcp_server/.env` に Google OAuth と GA4 プロパティ ID、GSC サイト URL が設定されている | `mcp_server/README.md` のセットアップ手順を参照 |
| Claude Desktop / Claude Code に `ga4-gsc-analytics` MCP が登録されている | エージェント内で `health_check` を呼んで `ga4_ok: true, gsc_ok: true` が返ること |
| (任意) playwright 系 MCP がインストールされている | SERP の H2/H3 取得が高精度になる。無くても `WebSearch` + `WebFetch` フォールバックで動作 |

### 2. 起動方法

#### a. Claude Code の通常チャットから呼ぶ場合

チャットで明示的にサブエージェントを使うよう依頼します:

```
seo-growth-hacker エージェントを使って、お宝キーワードを提案してください。
```

または `/agents` コマンドで一覧から選択できます(Claude Code 対応版)。

#### b. プログラムから `Task` ツールで呼ぶ場合

```jsonc
{
  "subagent_type": "seo-growth-hacker",
  "description": "お宝KW発見と記事ドラフト生成",
  "prompt": "直近28日のデータでお宝キーワードを3件提案してください。期間は明示してください。"
}
```

### 3. 進行フロー(SOP)

このエージェントは **4 ステップ完結型** で動きます。各ステップで必ず停止し、ユーザーの承認・選択を待ちます。

```
[Step 1] お宝KWの抽出と提案
   │  使用ツール: gsc_position_window, gsc_low_ctr_pages, ga4_landing_pages
   │  出力: 候補1〜3件(タイプA/B/C 分類、実数データ付き)
   ▼ ユーザーが対象KWを指定
[Step 2] 競合分析と構成案
   │  使用ツール: playwright系MCP → 無ければ WebSearch + WebFetch
   │  出力: 競合H2/H3 サマリ + 勝てるアウトライン(H1/H2/H3)
   ▼ ユーザーが構成案を承認 or 修正指示
[Step 3] H2 単位の分割執筆
   │  出力: 1 つの H2 セクション(600〜1000字目安)
   ▼ ユーザーが「次へ」と入力(各H2ごとに繰り返し)
[Step 4] 統合出力
   │  出力: ```markdown フェンス内に Front Matter + 本文 + 内部リンク提案
   ▼ (完了)
```

#### 各ステップで人間が打つコマンドの例

| ステップ | ユーザー入力例 |
| --- | --- |
| Step 1 後 | 「候補2 のキーワード "○○ 比較" で進めてください」 |
| Step 2 後 | 「OKです、執筆を開始してください」 / 「H2-3 を分割して、より具体例を増やしてください」 |
| Step 3 中 | 「次へ」 / 「この段落の表現を専門家寄りに直してください」 |
| Step 4 後 | 「内部リンク提案を 5 本に増やしてください」 |

### 4. 期待される出力サンプル

#### Step 1 出力(イメージ)

```
### 候補1: /blog/seo-internal-linking
- タイプ: A(順位浮上型) + B(CTR改善型)
- 根拠データ(期間: 2025-04-22〜2025-05-19):
  - impressions: 4,820
  - position: 8.6
  - ctr: 1.4%
  - GA4 engagementRate: 41%
- なぜ「お宝」か: 8位帯で月4,800表示。順位を3位帯へ押し上げれば
  クリック数が概算で約3倍見込めるレンジ。
- 想定する記事ターゲットKW: 「内部リンク 設計」
```

> ※ 上記の数字はあくまでサンプルです。実運用ではエージェントが MCP から取得した実数を表示します。

#### Step 4 出力(イメージ)

```` markdown
---
title: 内部リンク設計の完全ガイド
meta_description: ...
target_keyword: 内部リンク 設計
secondary_keywords:
  - サイト構造
  - アンカーテキスト
recommended_internal_link:
  - from: /blog/seo-basics
    to: /blog/internal-linking-design
    anchor_text: 内部リンク設計の考え方
    reason: /blog/seo-basics は impressions 9,800 で関連性が高く、文中で
      内部リンク概念に触れている既存導線を活用できる。
---

# 内部リンク設計の完全ガイド
...
````

### 5. 設計ポリシー(知っておくと便利)

- **推測の排除**: 数値はすべて MCP ツール由来の実数のみ。データ欠損時は「(データなし)」と明示します。
- **ステップ停止**: 各 Step 末尾に `[待機]` マーカーがあり、エージェントは勝手に先に進みません。
- **ファイル書き込みなし**: 記事ドラフトは **チャット出力のみ**。コピーして CMS に貼り付けてください。
- **環境差吸収**: SERP 解析は playwright 系 MCP を優先しますが、無い環境では `WebSearch` + `WebFetch` に自動フォールバックします。

### 6. トラブルシュート

| 症状 | 確認ポイント |
| --- | --- |
| エージェントが「MCP ツールが見つからない」と返す | Claude Desktop / Claude Code の MCP 登録を確認。`health_check` を最初に走らせる |
| `health_check` で `ga4_ok: false` | `mcp_server/.env` の `GA4_PROPERTY_ID` と OAuth スコープを再確認 |
| `health_check` で `gsc_ok: false` | `GSC_SITE_URL` がプロパティに登録されている URL と一致しているか確認 |
| Step 2 で SERP 解析が止まる | playwright が無いことが多い。フォールバックの WebSearch/WebFetch が使えるかチェック |
| 一気に Step 4 まで進んでしまう | 起動プロンプトで「Step 1 のみ実行して停止してください」と明示すると確実 |

---

## エージェントを追加するには

新しいサブエージェントを追加する場合、本フォルダに `*.md` ファイルを 1 本作成します。

最小例:

```markdown
---
name: <kebab-case-name>
description: <いつこのエージェントを使うかが伝わる一文>
model: sonnet
---

# Role
...

# Rules
...

# SOP
...
```

- `name` はファイル名(拡張子除く)と一致させること。
- `description` の品質がエージェントの自動選択精度に直結します(短く、トリガー条件が分かる文に)。
- `tools` を明示すると最小権限化できますが、環境間で動かしたい場合は省略して親エージェントから継承させるのが安全です(本リポジトリの `seo-growth-hacker` はこの方針)。

その後、本ファイル冒頭の表に追記してください。
