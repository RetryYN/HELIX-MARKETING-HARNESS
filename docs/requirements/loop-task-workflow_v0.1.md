# ループ・タスク・ワークフロー要件定義 v0.1

> status: **draft**（AI 起草 2026-07-30。人の承認で confirmed）
> 位置づけ: **業務全体**（計画立案・充填/設定・制作・審査・公開・応答・計測・基盤運用）を実行モデルの
> 3 構成要素 — **ループ（回転）／タスク（作業単位）／ワークフロー（手順）** — に分解した要件定義。
> 媒体公開系は [br-media_v0.1.md](br-media_v0.1.md)（BR-M）から、計画・充填・制作・運用は
> BR-A/D/G/H から降ろす。エンジン要件（FR-11〜16）のインスタンス定義にあたる。
> 漏れ検査は §3.7 の業務カバレッジ表で行う。
> **PoC 分離**: 調査だけでは確定できない要件は §5 の PoC 登録簿へ分離し、PoC PASS まで freeze しない
> （HELIX の poc kind / fail-close に準拠。PoC 未了の要件で実装スライスに着手しない）。
> ID: ループ = `LP-*`、タスク型 = `T-*`、ワークフロー = `WF-<略号>-<n>`、PoC = `POC-<n>`。

---

## 1. ループ要件（LP）

### 1.1 ループ型（全媒体共通の型。FR-11/14 のインスタンス）

| ID | 型 | サイクル | 開始条件 | 還流 |
|---|---|---|---|---|
| LP-U | 上位ループ（ブランド成長サイクル） | 月次 | ブランド計画（brand_plans）が存在 | 全媒体の learnings を集約し行動計画・KPI 目標を更新 → 下位ループへ再発行 |
| LP-OPS | 運用巡回（ヘルスチェック） | 日次 | 常時 | 異常検知 → T-OPS タスク発火（WF-OPS-7） |
| LP-D | 日次回転 | 1 日 | KPI 目標あり＋前日レビュー完了 | 日次でエンゲージ実績を蓄積、週次で learnings 化 |
| LP-W | 週次回転 | 1 週 | KPI 目標あり | スプリントレビュー（計画↔計測ペア）で learnings 生成 |
| LP-M | 月次回転 | 2 週〜1 月 | KPI 目標＋制作資産の充足 | 同上 |
| LP-E | イベント駆動 | なし（トリガ発火） | 上流イベント（記事公開・還流指示） | 発火元ループに帰属 |
| LP-MEAS | 計測サイクル | 週次（全媒体横断） | 常時 | measurements 投入→計画↔計測ペア成立判定 |

### 1.2 媒体 → ループ割当（暫定値は C: `loop.<媒体>.cycle`）

| 媒体 | ループ型 | 暫定サイクル | 備考 |
|---|---|---|---|
| WP | LP-W | 週 1〜2 記事 | S0 の主戦場 |
| X | LP-D | 日次 | MR-X-3 のレート内 |
| note | LP-W | 週 1 | 定期購読採用時は月次更新義務が下限制約（BR-M-NOTE-3） |
| YouTube | LP-M | 隔週 1 本 | 制作リードタイムが律速 |
| Instagram | LP-W | 週 2〜3 投稿 | 経路は POC-02 の結果待ち |
| Discord | LP-D | 日次巡回 | 応答中心・投稿は告知時のみ |
| Podcast | LP-E | 動画公開に追従 | 音声は副産物（MR-PC-1） |
| stand.fm | LP-E | Podcast に追従 | 従媒体（BR-M-STFM-1） |
| KDP | LP-M | 四半期 1 冊目安 | 低頻度・高品質（BR-M-KDP-3） |
| HubSpot | LP-M | 月次配信計画 | 月 2,000 通の予算配分（BR-M-HS-2） |
| LINE | LP-M | 週 1 配信・月次計画 | 月 200 通予算（BR-M-LINE-2） |
| AFF | LP-E | 記事企画に追従 | 提携申請は記事要件から発火 |
| PWA/Play | LP-E | 企画承認時のみ | 制作プロジェクト型 |
| GA4/SC ほか計測 | LP-MEAS | 週次 | 全媒体の実測を横断取得 |

**LP 共通要件**:

- **LP-R1** 各媒体ループは独立に回り、他媒体の遅延に影響されない（BR-A2）
- **LP-R2** ループ開始はペア条件（KPI 目標の存在）を満たすまでブロック（FR-14）
- **LP-R3** サイクル長・回転数は config で媒体別に変更でき、コード変更を要しない（NFR-8）

## 2. タスク型要件（T）

### 2.1 タスク型（FR-12/13 のインスタンス。全タスクは author≠verifier・証跡完備で完了）

| ID | タスク型 | author | verifier | 必須証跡（kind） | 通過ゲート |
|---|---|---|---|---|---|
| T-PLAN | 企画 | strategist | critic | 企画レコード（訴求・ターゲット・狙い） | 倫理 |
| T-PROD | 制作 | writer/producer | critic | commit_hash | 企画↔品質（審査 PASS で成立） |
| T-REVIEW | 審査 | critic | —（審査自体が verifier 行為） | review_pass | 倫理・PR 表記・design-evidence（媒体による） |
| T-PUB | 公開 | connector | gate-engine | published_url ＋ screenshot | 公開ゲート（成立ペア ID 必須）・束縛承認 |
| T-ENGAGE | 応答 | responder | critic（事後サンプル審査） | 応答ログ | 倫理・レート |
| T-MEAS | 計測取込 | collector | parser（型検証） | file_hash ＋ screenshot | なし（読取専用） |
| T-SYNC | 登録・同期 | connector | gate-engine | API レスポンス/同期ログ | 種別による（金銭系は束縛承認） |
| T-FILL | 充填（ヒアリング/リサーチ/config） | filler-engine | 型検証（スキーマ） | 充填記録＋出典 URL（リサーチ時） | 出典なし値の拒否（FR-32） |
| T-OPS | 基盤運用（構築・接続・地図・復旧） | operator | ヘルスチェック（機械検証） | 実行ログ＋検証結果 | 種別による（credential 操作は attended） |

**T 共通要件**:

- **T-R1** タスク型ごとの必須証跡 kind 集合はワークフロー定義が宣言し、FR-28 が `done` 遷移時に検証する
- **T-R2** T-PUB は T-PROD の審査 PASS（ペア成立）なしに生成されない（エンジンがタスク発行段階で拒否）
- **T-R3** T-ENGAGE は事前審査なしで送出できるが、倫理ゲートのルールベース検査（禁止表現）を
  送出前に必ず通す。事後サンプル審査で FAIL が出た場合、当該媒体の T-ENGAGE を停止
- **T-R4** 金銭属性を持つタスク（価格設定・返金等）は型に関わらず束縛承認を要求（FR-26）

### 2.2 媒体 → タスク型割当

| 媒体 | PLAN | PROD | REVIEW | PUB | ENGAGE | MEAS | SYNC |
|---|---|---|---|---|---|---|---|
| WP | ○ | ○ | ○ | ○ | — | ○(GA4経由) | — |
| X | ○ | ○ | ○ | ○ | ○ | ○ | — |
| note | ○ | ○ | ○ | ○ | — | ○(CSV) | — |
| YouTube | ○ | ○ | ○ | ○ | ○(コメント) | ○(CSV) | — |
| Instagram | ○ | ○ | ○ | ○ | — | ○ | — |
| Discord | ○(告知) | ○ | ○ | ○ | ○ | ○(Bot自前) | — |
| Podcast | —(動画に従属) | ○(派生) | ○ | ○(RSS) | — | ○(CSV×3) | ○(初回登録=人) |
| stand.fm | — | ○(流用) | — | ○ | — | ○(参考値) | — |
| KDP | ○ | ○(EPUB) | ○ | ○(出版) | — | ○(CSV) | ○(AI申告) |
| HubSpot | ○(配信計画) | ○ | ○ | ○(配信) | — | ○ | ○(リード同期) |
| LINE | ○(セグメント) | ○ | ○ | ○(配信) | ○(応答=無料) | ○ | — |
| AFF | ○(案件選定) | —(記事はWP) | ○(PR表記) | ○(リンク埋込) | — | ○(成果CSV) | ○(提携申請) |
| PWA/Play | ○ | ○(コード) | ○(機能検証) | ○(配備) | — | ○ | ○(ストア) |
| Canva/GenAI/Seedance | — | ○(素材) | —(下流で審査) | — | — | — | ○(ライセンス台帳) |
| Notion/DS | — | — | — | — | — | — | ○(低頻度) |

## 3. ワークフロー要件（WF）

ワークフロー = タスクに割り当てる手順定義（TAKUMI カタログのスキル列＋ゲート＋証跡宣言）。
**WF-R1**: ワークフローは DB（workflows テーブル）に宣言的に保持し、追加・変更にコード変更を
要しない（NFR-8）。**WF-R2**: 各 WF は「入力→ステップ列→出力型→必須証跡→通過ゲート」を宣言する。

### 3.1 S0〜S1 で確定するワークフロー（要件確定・PoC 不要）

| WF | 媒体/用途 | ステップ列（TAKUMI スキル） | 出力 |
|---|---|---|---|
| WF-WP-1 | ブログ記事制作 | seo-jp → copywriting → content-design → design-evidence-jp（審査） | 記事ソース（commit） |
| WF-WP-2 | 記事公開 | ペア検証 → REST 下書き → 束縛承認 → 公開 → スクショ | published_url |
| WF-MEAS-1 | GA4 PV 取込 | エクスポート取得 → hash → パース → measurements | 計測行 |
| WF-DASH-1 | ダッシュボード生成 | SQLite クエリ → HTML 生成 → 証跡保存 | HTML |
| WF-NOTION-1 | 計画同期 | 読取り → 差分検出 → 書戻し | 同期ログ |

### 3.2 S2〜S3 のワークフロー（要件は本書で確定・実装はスライス時）

| WF | 媒体/用途 | ステップ列 | 前提 PoC |
|---|---|---|---|
| WF-X-1 | ポスト制作・投稿 | sns-jp → copywriting → 審査 → 投稿 → スクショ | POC-01 |
| WF-X-2 | リプライ応答 | engagement-reply-jp → 倫理ルール検査 → 送出 | POC-01 |
| WF-NOTE-1 | note 記事・有料記事 | storytelling → sales-writing → 審査 → 投稿（価格は束縛承認） | POC-05 |
| WF-YT-1 | 動画制作 | video-script → VOICEVOX → 素材 → Remotion/ffmpeg 合成 | POC-08 |
| WF-YT-2 | 動画公開 | 審査 → アップロード → メタ設定 → AI 開示フラグ → スクショ | POC-01（YT 変種） |
| WF-IG-1 | フィード/リール投稿 | sns-jp → design-evidence 審査 → 投稿 | POC-02 |
| WF-PC-1 | Podcast 派生配信 | 音声抽出 → mp3 → WP メディア → RSS 更新 | POC-08 |
| WF-KDP-1 | EPUB 出版 | WP 資産再編 → pandoc EPUB → 審査 → AI 申告 → 出版（価格は束縛承認） | POC-09 |
| WF-HS-1 | メルマガ配信 | messaging-design-jp → 法規要素検証（NFR-9）→ 審査 → MCP 配信 | POC-10 |
| WF-LINE-1 | セグメント配信 | セグメント抽出 → messaging-design-jp → 審査 → 配信 | POC-11 |
| WF-AFF-1 | 提携・リンク埋込 | 案件選定 → 提携申請 → PR 表記付き記事（WF-WP-1 に合流） → 表記位置検証 | POC-12 |
| WF-ASSET-1 | 素材調達 | 素材要求 → 取得（経路は POC-13）→ ライセンス台帳登録 | POC-13 |

### 3.3 計画系ワークフロー（LP-U の中身 — 「計画の立て方」の分解）

| WF | 用途 | ステップ列 | 人の関与 |
|---|---|---|---|
| WF-PLAN-1 | ブランド計画策定（初回・年次改訂） | 事業前提充填（WF-FILL-1 呼出）→ 市場・媒体標準リサーチ → ブランド計画 draft（1 年地平・北極星 KPI）→ **人の承認（束縛）** → brand_plans 投入 | 承認のみ |
| WF-PLAN-2 | 行動計画更新（月次） | learnings 集約 → KPI 実績と目標の乖離分析 → 行動計画 draft 更新 → ブランド計画への trace 検証 → Notion 書戻し | なし（乖離が閾値超過時のみ通知） |
| WF-PLAN-3 | KPI ツリー構築・改訂 | 媒体標準指標リサーチ（出典必須）→ ツリー draft（露出/マイクロCV/転換/関係/収益の 5 層）→ 有料指標の型拒否検証（FR-23）→ kpi_nodes 投入 | なし |
| WF-PLAN-4 | 媒体ポートフォリオ選定・スプリント計画 | 行動計画 → 媒体別リソース配分 → KPI 目標設定 → スプリント生成（目標なしは開始拒否 = FR-14）→ タスクキュー生成 | なし |
| WF-PLAN-5 | スプリントレビュー・還流 | 計画↔計測ペア成立検証（FR-22）→ 達成/未達の要因分析 → learnings 生成 → 上位ループ入力キュー投入 | なし |
| WF-PLAN-6 | ネタ・企画の起票 | Notion ネタ帳読取り＋リサーチ → 企画 draft（訴求・ターゲット・狙い）→ 倫理ゲート → 企画レコード確定 | なし |

**PLAN 共通要件**: 計画系の全成果物（brand_plans・action_plans・kpi_nodes）は SQLite が正本で、
Notion は表示・入力用の投影のみ（ADR-004）。計画の全変更は変更前後を証跡化する。

### 3.4 充填系ワークフロー（「設定」の分解 — 三エンジンの実行形）

| WF | 用途 | ステップ列 | 人の関与 |
|---|---|---|---|
| WF-FILL-1 | 初回セットアップ（事業前提の充填） | スキーマ必須スロットの欠損検出（FR-31）→ 問診リスト生成 → **Claude Code 対話で人に照会** → 回答の型検証 → business_profiles / config 投入 | 回答（唯一の設計上の人手入力） |
| WF-FILL-2 | config 変更 | 変更要求（理由付き）→ 影響範囲の確認（依存タスク列挙）→ INSERT 履歴充填（FR-33）→ 変更通知 | 安全側→危険側の変更のみ束縛承認 |
| WF-FILL-3 | リサーチ充填 | 不足スロット特定 → Web 検索 → 出典付き draft（出典なし値は拒否 = FR-32）→ 型検証 → スロット投入 | なし |
| WF-FILL-4 | 別事業プロファイル追加 | WF-FILL-1 再実行 → プロファイル分離検証（FR-34: 既存事業への影響ゼロ確認）→ 有効化 | 回答＋有効化承認 |

### 3.5 制作系ワークフロー（制作工程の分解 — すべて T-PROD の具象。共通形: git ワークスペース → 審査 → 資産登録）

| WF | 制作物 | ステップ列 | 前提 PoC |
|---|---|---|---|
| WF-PROD-TEXT | 記事・台本・コピー | 企画（WF-PLAN-6 出力）→ 構成 → 執筆（seo-jp/copywriting/storytelling）→ 推敲 → commit | — |
| WF-PROD-IMG | 図解・OGP・バナー | 構成案 → HTML/SVG 生成 → デザイントークン注入（FR-52）→ Playwright スクショ → design-evidence 審査。写実・イラスト系素材は Codex CLI image_gen（BR-M-GENAI-4）で生成し同審査へ | — |
| WF-PROD-SLIDE | スライド・資料 PDF | 構成 → HTML（slide テンプレート）→ トークン注入 → Playwright PDF → 審査 | — |
| WF-PROD-AUDIO | 音声（Podcast/stand.fm 用） | 台本（WF-PROD-TEXT 出力）→ VOICEVOX 音声合成 → mp3 変換 → 音質機械検証（長さ・無音区間） | POC-08 |
| WF-PROD-VIDEO | 動画 | 台本 → 音声（WF-PROD-AUDIO）→ 素材調達（WF-ASSET-1）→ Remotion 合成 → NVENC エンコード → 審査 | POC-08 |
| WF-PROD-SHORT | ショート派生（9:16） | 元動画 → ハイライト抽出 → ffmpeg プロファイル変換 → 独自編集付与（BR-M-YT-3）→ 審査 | POC-08 |
| WF-PROD-EPUB | 電子書籍 | WP 資産のテーマ別選定 → 再編・加筆 → pandoc EPUB（決定的生成）→ 検証（hash 一致） | POC-08 |
| WF-PROD-APP | 診断ツール・シミュレータ | 機能要件定義 → HTML/JS 実装 → 機能検証（テスト）→ Lighthouse → PWA 化（manifest+SW） | — |
| WF-PROD-REPURPOSE | リパーパス計画・実行 | 元資産選定 → 派生先媒体の選定（KPI 目標照合）→ 各 WF-PROD-\* を子タスクとして発火 → assets 系譜登録（FR-55） | — |

**PROD 共通要件**: 全制作 WF は (a) 同一入力→同一出力の決定性（NFR-2。生成 AI 利用ステップは
出力を証跡固定）、(b) 審査 PASS 時の commit hash 紐づけ（FR-54）、(c) デザイントークン適用
（視覚物のみ・FR-52）を満たす。制作途中の中断は git ワークスペースと tasks 状態から再開できる（NFR-3）。

### 3.6 基盤・設定系ワークフロー（環境と運用の分解）

| WF | 用途 | ステップ列 | 人の関与 |
|---|---|---|---|
| WF-OPS-1 | 環境構築（初回） | uv 依存解決 → DB 初期化（DDL）→ マイグレーション適用 → ヘルスチェック（全テーブル・設定検証） | 併走（初回のみ） |
| WF-OPS-2 | アカウント接続 | credential 登録（**人が入力**・暗号化ストア直行 = FR-47）→ attended ログイン/OAuth でセッション取得 → storage_state 暗号化保存 → 接続検証（read 操作） | credential 入力・初回ログイン |
| WF-OPS-3 | 媒体追加 | 接続レジストリ行追加 → WF-OPS-2（当該媒体）→ 攻略地図初期作成（WF-OPS-4）→ WF 定義投入 → KPI ノード追加 → 試験投稿（審査・承認付き） | 試験投稿の承認 |
| WF-OPS-4 | 攻略地図の作成・修復 | 対象ページ解析 → 地図 draft（手順・セレクタ）→ 試行検証（read 操作で確認）→ playbooks 保存。破損時は再解析 1 回 → 失敗で escalate（FR-43） | なし |
| WF-OPS-5 | バックアップ・復旧 | 日次 snapshot（SQLite・世代管理 = NFR-10）→ 完全性検証 → 月次で復元試験 → 結果を証跡化 | なし |
| WF-OPS-6 | デザイントークン同期 | DesignSync 取得 → 差分検証 → キャッシュ更新（取得不能時はキャッシュ継続 = MR-DS-1） | なし |
| WF-OPS-7 | 異常対応 | escalated 検知（LP-OPS/FR-16）→ 診断（分類: 地図破損/レート/認証切れ/予算/その他）→ 自動復旧可なら該当 WF-OPS 発火 → 不能なら通知＋安全停止 | 通知への応答（不能時のみ） |
| WF-OPS-8 | セッション保守 | 有効期限・失効の定期検査（LP-OPS 内）→ 失効検知 → attended 再ログイン要求を通知 | 再ログインのみ |

**OPS 共通要件**: 人の関与が必要なのは (1) WF-FILL-1/4 のヒアリング回答、(2) WF-OPS-2/8 の
credential・ログイン、(3) 束縛承認 — の 3 種のみ（BR-H1 の全業務での具体化）。それ以外の
ステップに人手が必要になった場合は設計違反として escalate する。

### 3.7 業務カバレッジ表（業務全体 → 分解先の対応。漏れ検査用）

| 業務領域 | ループ | タスク型 | ワークフロー |
|---|---|---|---|
| 戦略・計画立案 | LP-U | T-PLAN | WF-PLAN-1..6 |
| 事業前提・設定の充填 | LP-E（スロット欠損駆動） | T-FILL | WF-FILL-1..4 |
| コンテンツ制作 | 各媒体ループ内 | T-PROD | WF-PROD-\*（9 本） |
| 審査・品質 | 各媒体ループ内 | T-REVIEW | 各 WF 内の審査ステップ＋ゲート |
| 公開・配信 | 各媒体ループ（§1.2） | T-PUB | WF-WP-2, WF-X-1, WF-HS-1 等（§3.1/3.2） |
| コミュニティ応答 | LP-D（X/DC/LINE） | T-ENGAGE | WF-X-2 等 |
| 計測・KPI | LP-MEAS | T-MEAS | WF-MEAS-1, WF-DASH-1 |
| 収益・決済 | LP-E（Stripe/AFF） | T-SYNC | WF-AFF-1 ほか |
| 環境・接続・保守 | LP-OPS | T-OPS | WF-OPS-1..8 |
| 素材調達 | LP-E | T-PROD/T-SYNC | WF-ASSET-1 |

## 4. スライス配分（PoC 込み）

| スライス | 確定実装 | PoC 実施 |
|---|---|---|
| S0 | WF-OPS-1/2（WP・GA4 分）, WF-WP-1/2（= WF-PROD-TEXT の WP 具象）, WF-MEAS-1, WF-PLAN-6（手動投入の代替可）, LP-W(WP), T-PLAN/PROD/REVIEW/PUB/MEAS | POC-03（GA4 取得経路）を S0 内で先行 |
| S1 | WF-PLAN-2/4/5（還流・スプリント）, WF-DASH-1, WF-NOTION-1, WF-PROD-IMG, WF-OPS-5/7, LP-U 最小形, LP-MEAS, LP-OPS | POC-08（音声/動画パイプ）着手 |
| S2 | WF-FILL-1..4（三エンジン）, WF-PLAN-1/3, LP の複数媒体化, WF-OPS-3（媒体追加の型） | POC-01, 05, 10 |
| S3+ | 各媒体 WF・WF-PROD-AUDIO/VIDEO/SHORT/EPUB/APP の本実装（PoC PASS 済みのみ）, WF-OPS-4 本格化 | POC-02, 09, 11, 12, 13 |

## 5. PoC 登録簿（要件 freeze のブロッカー）

> 規律: PoC は使い捨て検証（poc kind）。**成功基準を先に書き、PASS/FAIL を evidence で判定**。
> FAIL 時は代替分岐へ進み、本実装コードに PoC コードを昇格させない（書き直す）。
> PoC 未了の WF/媒体要件は draft のまま freeze せず、当該媒体の実装スライスに着手しない。

| POC | 検証事項 | 成功基準 | FAIL 時の分岐 | ブロック対象 |
|---|---|---|---|---|
| POC-01 | X ブラウザ投稿の生存性（Playwright→Camoufox、検知・BAN 兆候の観測込み） | テストアカウントで 2 週間・MR-X-3 レート内の投稿/応答が警告ゼロで継続 | X の優先度降格（note/WP へ再配分）or Premium+API 検討 | WF-X-1/2、LP-D(X) |
| POC-02 | IG Graph API 経路（プロアカウント・投稿＋インサイト取得） | API でリール/フィード投稿と insights 取得が成功 | ブラウザ突破（Camoufox）の POC-01 相当を IG で再実施 | WF-IG-1（§99-1 の PO 判断とセット） |
| POC-03 | GA4 Data API / GSC API の無料取得（PV・検索クエリ） | API で S0 対象サイトの PV が証跡付きで取得できる | ブラウザエクスポート（現行 charter 経路）へフォールバック | WF-MEAS-1 の経路確定（§99-3） |
| POC-05 | note ブラウザ投稿＋アナリティクス CSV 取得 | 下書き投稿→公開→CSV DL が 2 週間安定 | note の手動運用格下げ | WF-NOTE-1 |
| POC-08 | 音声/動画パイプライン（VOICEVOX→mp3、Remotion+NVENC 合成、pandoc EPUB） | 台本→動画 1 本・音声 1 本・EPUB 1 冊が決定的に再現生成できる（hash 一致） | ツール代替（tech-stack §7 トリガー） | WF-YT-1, WF-PC-1, WF-KDP-1 |
| POC-09 | KDP 出版フロー（ブラウザ・AI 申告含む）の自動化可能範囲の特定 | アップロード→申告→出版の各ステップの自動化可否が確定し、人手ステップが列挙される | KDP を半自動媒体（人手併用）として要件を書き直す | WF-KDP-1 |
| POC-10 | HubSpot MCP 配信＋法規要素（オプトイン記録・停止導線）の機械検証 | MCP でセグメント配信でき、法規 3 要素がテンプレ検証で機械判定できる | ブラウザ補完 or 配信専業サービス再検討 | WF-HS-1 |
| POC-11 | LINE 配信経路（Messaging API vs 管理画面ブラウザ、§99-2 の判断材料） | 選定経路でセグメント配信＋結果取得が成功 | もう一方の経路へ切替 | WF-LINE-1 |
| POC-12 | ASP 管理画面の自動化可能範囲（A8/もしも。楽天は対象外） | リンク発行と成果 CSV 取得の自動化可否が確定 | AFF を半自動媒体として要件を書き直す | WF-AFF-1 |
| POC-13 | 素材調達経路（Canva MCP の実際の限界確認＋代替: attended/ブラウザ/Openverse） | 1 記事分の素材がライセンス台帳付きで調達できる経路が 1 つ確立 | 素材は attended 工程（人が選ぶ）に確定 | WF-ASSET-1（§99-6 とセット） |

**PoC 共通要件**:

- **POC-R1** 各 PoC の実施・判定は evidence（実行ログ・スクショ・hash）で記録し、PASS/FAIL の宣言のみの
  判定を認めない（BR-B3 準拠）
- **POC-R2** PoC 用アカウント・環境は本番アカウントと分離する（特に Google 系 — RSK-09）
- **POC-R3** PoC の期限は各スライス計画で定め、期限超過は FAIL 分岐として扱う（塩漬け禁止）

## 6. トレースと未決

- 上流: LP-U/D/W/M/E → BR-A1..A3/FR-11/14、LP-OPS → BR-H3/FR-16、T → BR-A4/FR-12/13/27/28、
  T-FILL → BR-D1..D3/FR-31..33、T-OPS → BR-F2/F4/H3、WF → BR-F3/NFR-8、
  WF-PLAN → BR-A3/E1、WF-PROD → BR-G1..G3/FR-51..55、WF-OPS → FR-41..43/47/72/NFR-10、
  PoC 規律 → HELIX poc kind
- 本書の WF は workflows テーブルのシード定義になる（S0 で WF-WP-1/2, WF-MEAS-1 を投入）
- 未決: §99（br-media）の PO 判断 8 件のうち #1/2/3/6 は対応 PoC（02/11/03/13）の結果と併せて判断する。
  #4（Gemini 除外）は PoC 不要 — 規約明文違反のため要求済み（BR-M-GENAI-1）
