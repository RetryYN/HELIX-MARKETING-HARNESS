# TAKUMI 素材カタログ — ループスクラム・マッピング v0.1

> status: reference ／ 目的: TAKUMI の skills / procedures / agents の棚卸しと二重ループへの配置対応表。
> **一括移植はしない**（charter §7: スライス駆動）— 各スライスが必要とした素材をこの表から引き込む際のカタログ。
> 継承方針は charter §6（素材として HELIX 風にカスタマイズ）。

## 1. skills（42本）→ ループステップ配置案

### 上位ループ

| ステップ | 配置するスキル |
|---|---|
| リサーチ | voc-research-jp, quant-research-jp, social-insight-jp, demand-timing-jp |
| 市場分析 | market-analysis-jp, growth-teardown-jp, customer-analytics-jp |
| マーケティング戦略 | stp-jp, winning-position-jp, business-model-jp, scale-strategy-jp, gtm-jp, micro-business-jp, offer-design-jp |
| 行動計画 | kpi-design-jp, channel-planning-jp, hypothesis-design-jp |

### 下位ループ

| ステップ | 配置するスキル |
|---|---|
| 媒体戦術 | sns-jp, seo-jp, local-seo-jp, breakout-content-jp, referral-advocacy-jp |
| リサーチ（媒体） | search-console-jp, ga4-jp（計測取り込み側と共用） |
| 企画 | psych-target-jp, messaging-design-jp, content-design, storytelling |
| 運用（制作・公開） | copywriting, sales-writing, business-writing, logical-writing, video-script, web-design, psych-ux-jp, psych-nudge-jp, cro-jp, content-ops-jp, engagement-reply-jp |
| 計測 | ga4-jp, search-console-jp |
| 改善 | growth-teardown-jp（再掲: 実測の解体） |

### ゲート・横断（ループ外の常時適用）

| 用途 | スキル |
|---|---|
| 品質ゲート（企画↔品質ペア） | design-evidence-jp, brand-guideline-jp |
| 倫理・法規ゲート（P5、PR 表記） | ad-compliance-jp |

## 2. procedures（38本）→ 再編方針

| 分類 | procedures | 行き先 |
|---|---|---|
| 上位ループ駆動 | strategy, research, brand, customer, voc | loops/upper/ の駆動定義へ再編 |
| 下位ループ駆動 | campaign, content, ownedmedia, website, sns（+媒体別 sns-x/instagram/line/note/threads/tiktok/youtube）, email, engagement, retention, pr, publish | loops/lower/ へ。媒体別はブラウザ攻略地図と対で再設計 |
| 計測・還流 | analytics, dashboard, report, reporting, verify | harness/ の計測ゲート・還流処理へ吸収（手順書からコードへ） |
| ハーネス機能へ吸収 | setup, config, status, task, add-work, memory, feedback, customize, skillify | 状態機械・SQLite・Claude Code 標準機能で代替。手順書としては廃止 |
| 特殊 | crisis（炎上対応）, demo | crisis は独立ワークフローとして継承。demo は廃止 |

## 3. agents（10本）→ 再設計方針

| TAKUMI agent | 扱い |
|---|---|
| cmo-strategist, strategy-advisor | 統合 → 上位ループの strategist に |
| deliverable-writer | 下位ループの writer に |
| design-artisan | 制作（コード×レンダリング）担当に改修 |
| design-critic | 品質ゲートの critic に（企画↔品質ペアの判定者。PASS を SQLite へ書く形に改修） |
| outcome-verifier | 計測ゲートの verifier に（計画↔計測ペアの判定者） |
| pre-send-verifier | 公開前ゲート（PR 表記・ブランド線・ゼロ広告費チェック）に |
| privacy-auditor, risk-forecaster | 統合 → 倫理・リスクゲート（P5）に |
| growth-challenger | 改善ステップの challenger（学習の還流役）に |

原則（P4）: 作った本人に審査させない。writer/artisan 系と critic/verifier 系は別エージェントのまま維持。

## 4. 取り込み順の目安（スライスが引く際の参考）

1. 本マッピングの確定
2. リポジトリ骨格作成（skills/ agents/ loops/ harness/）
3. スキル移植: frontmatter 統一・匠文言除去・ループステップのタグ付け
4. procedures → loops/ 駆動定義への書き直し（上位から）
5. agents 再設計（ゲート判定を SQLite 書き込みで表現）
