# 要件定義書 v0.1

> status: **confirmed**（2026-07-31 PO 承認 — 要件定義完遂指示。AI 起草）
> pair: [verification-design_v0.1.md §2〜§6](verification-design_v0.1.md)（検証設計③ — HELIX 式 ①↔③ 文書ペア）
> 上位文書: [br-backbone_v0.1.md](br-backbone_v0.1.md)（BR 背骨）／ charter v0.3（層外 anchor）
> 機械可読正本: 要件エンティティ（BR/REQ/FR/NFR/AC/FN/MR/WF）は [json/](json/) に JSON 正本を併置する。
> 人の承認は MD、実装・変換の入力は JSON を用い、編集時は両方を同期する（PO 方針 2026-07-30）。
> 各 FR/NFR は BR に trace する。値はハードコードせず充填経路（H/R/C）を踏襲。
> スコープ: 背骨＋S0 ウォーキングスケルトンの要件。S1 以降のスライス要件は各スライス着手時に追補する。

---

## 1. システム構成（要件レベル）

```text
harness/（Python）
├── engine/        # ループ状態機械・タスク発行・マイクロループ制御      [FR-1x]
├── gates/         # ペアゲート・機械ゲート（fail-close）               [FR-2x]
├── fillers/       # ヒアリング/リサーチ/設定管理の三エンジン           [FR-3x]
├── connectors/    # MCP・ブラウザ・WP REST・Notion 同期                [FR-4x]
├── producers/     # 制作パイプライン（レンダリング・EPUB・音声・動画） [FR-5x]
├── metrics/       # 計測取り込み・KPI ツリー・ダッシュボード生成       [FR-6x]
└── db/            # SQLite スキーマ・マイグレーション                  [FR-7x]
```

## 2. 機能要求（FR）

### FR-1x エンジン（← BR-A1..A4）

- **FR-11** ループ状態機械: `loop_runs`（上位/下位/マイクロの3種）を状態遷移表で駆動する。遷移は
  `(現状態, イベント, ガード条件) → 次状態` の宣言的定義とし、コード分岐に埋め込まない
- **FR-12** タスク発行: ループステップ到達時に `tasks` 行を生成し、ワークフロー ID・担当エージェント・
  期待成果物型を割り当てる。タスクは `pending → in_progress → verifying → done/failed/escalated` を遷移
- **FR-13** 検証マイクロループ: `verifying` で検証エージェントを起動し、FAIL 時は差し戻し理由付きで
  `in_progress` へ戻す。リトライ回数は `config.retry_limit`（C・暫定既定値 3）で制御し、超過時 `escalated`
- **FR-14** スプリント制御: 媒体ごとに独立した `sprints` を持ち、開始条件（KPI 目標の存在 = 計画側の充足）を
  満たさない限り開始できない
- **FR-15** 還流: スプリントレビュー成立（FR-22）時に `learnings` を生成し、上位ループの次回転の入力キューへ積む
- **FR-16** エスカレーション制御: 異常（ゲート赤・予算超過・地図破損・リトライ超過）を検知した場合、該当タスクを
  `escalated` に遷移させ、通知（FR-46 経路）と安全停止（該当ループの保留）へ振り分ける（← BR-H3）

### FR-2x ゲート（← BR-B1..B4, C1..C4）

- **FR-21** 企画↔品質ペア判定: `pair_plan_quality` が (企画レコード, 審査 PASS レコード) の両参照を持つ場合のみ
  成立。公開系コネクタ（FR-4x）は成立済みペア ID なしの呼び出しを拒否する（fail-close）
- **FR-22** 計画↔計測ペア判定: `pair_kpi_measure` が (KPI 目標, 計測スナップショット) の両参照を持つ場合のみ
  レビュー成立イベントを発火
- **FR-23** ゼロ広告費ゲート: (a) KPI ノード登録時に有料指標（CAC/ROAS/広告費）の型を拒否、
  (b) ブラウザ自動化の URL 許可リストに広告マネージャ・課金ドメインを含めない（deny-by-default）
- **FR-24** PR 表記ゲート: アフィリエイトリンクを含む成果物は、PR 表記ブロックの存在検証に合格しない限り
  公開ゲートを通過しない
- **FR-25** 倫理ゲート: 審査ワークフローに P5 チェック項目（恐怖訴求・偽希少性・不安増幅・診断の押し付け）を
  必須項目として含み、該当時は FAIL
- **FR-26** 金銭 escalation: 価格変更・返金・決済設定に類する操作型のタスクは、オートモード状態に関わらず
  束縛承認（FR-46）を要求する
- **FR-27** 自己審査禁止: `tasks.author_agent == tasks.verifier_agent` となる割り当てを DB 制約とエンジン両方で拒否
- **FR-28** 証跡完備検証: タスク完了（`done` 遷移）時に、タスク種別ごとに定義された必須証跡（§4bis）が
  `evidence` に揃っていることを検証し、欠落時は遷移を拒否する（← BR-B3）

### FR-3x 三エンジン（← BR-D1..D4）

- **FR-31** ヒアリングエンジン: スキーマ（§4）の必須スロットの空きを検出し、質問リストを生成して
  Claude Code 対話で人に照会、回答を型検証して充填する。未充足のままでは依存タスクを開始しない
- **FR-32** リサーチエンジン: Web 検索で KPI 初期形・媒体標準指標・運用詳細を取得し、出典 URL 付きで
  draft を起草する。出典なしの値は draft に書けない（幻覚抑止）
- **FR-33** 設定管理: `config` テーブル（key, value, type, changed_at, changed_by, reason）。
  変更は履歴保持（UPDATE でなく INSERT）。安全側数値の既定値は保守的に設定
- **FR-34** 事業非依存: 事業前提は `business_profiles` に分離し、複数プロファイルの共存を許すスキーマとする

### FR-4x コネクタ（← BR-F1..F4）

- **FR-41** 接続レジストリ: サービスごとに (優先経路: MCP/ブラウザ/API, フォールバック経路, 認証方式) を
  宣言的に保持。経路選定はレジストリ参照で行いコードに埋め込まない
- **FR-42** ブラウザ自動化基盤: Playwright 系で headed/headless を切替可能。操作は攻略地図
  （`playbooks`: サイト・手順・セレクタ・最終成功日時）を参照して実行し、成功時に地図を更新
- **FR-43** 攻略地図の自己修復: セレクタ不一致等の破損検知時、ページ再解析による地図再生成を 1 回試み、
  失敗時はタスクを `escalated` にして通知（BR-H3）
- **FR-44** WP コネクタ: REST（投稿・メディア・下書き）+ WP-CLI（構築系）。書き込み系は成立済みペア ID を要求（FR-21）
- **FR-45** Notion 同期: スプリント開始時に計画を読取り、レビュー成立時に結果を書戻す低頻度同期。
  Notion 障害時もループは SQLite のみで継続可能（Notion は判定に関与しない）
- **FR-46** 承認チャネル: Claude Code アプリ通知で束縛承認（対象・操作・時点を明記）を送り、
  応答を `approvals` に証跡化。オートモード判定は `config.auto_mode_criteria`（C）と実績証跡から機械判定
- **FR-47** 秘匿情報: 認証情報・セッションは OS キーチェーンまたは暗号化ストアに置き、
  リポジトリ・SQLite・ログへの平文書き込みを禁止（BR-F4）

### FR-5x 制作（← BR-G1..G4）

- **FR-51** レンダリングパイプライン: HTML/SVG → ブラウザスクショ（画像）／HTML → PDF（スライド・資料）。
  入力ソースは git ワークスペース、出力は WP メディアへアップし `assets` に参照登録
- **FR-52** デザイントークン適用: Claude Design（DesignSync）から取得したトークンをレンダリング時に注入。
  トークン取得不能時は直近同期済みキャッシュで継続
- **FR-53** 音声・動画・EPUB: VOICEVOX(localhost)・Remotion/ffmpeg(NVENC)・pandoc の各パイプライン。
  すべて入力（台本・素材参照）から出力まで再現可能なコード実行として記録
- **FR-54** 版と証跡: 審査に出す成果物はワークスペースの commit hash で特定。PASS 記録は hash に紐づく
- **FR-55** 資産収束・リパーパス追跡: コンテンツ実体は WP へアップし `assets` に参照登録する。
  派生制作（記事→SNS/スライド/音声/動画/EPUB）は元資産への参照を保持し、リパーパス系譜を追跡できる（← BR-G2）

### FR-6x 計測・KPI（← BR-E1..E3）

- **FR-61** KPI ツリー: `kpi_nodes`（階層: 露出/マイクロCV/転換/関係/収益, 媒体タグ, 集計式）+
  `measurements`（node_id, 値, 期間, 取得証跡 ID）。媒体横断集計クエリが書ける正規化を維持
- **FR-62** 取り込みパイプライン: 取得（正規 API またはブラウザエクスポート。経路は接続レジストリと
  [ADR-006](../governance/adr/ADR-006-official-api-routes.md) に従い、GA4/GSC は正規 API）→
  取得物のハッシュ記録 → パーサ（サービス別）→ `measurements` 投入。パース失敗はエラー隔離し部分投入を許す
- **FR-63** ダッシュボード生成: SQLite → HTML（自己完結・依存 CDN なし）。生成物も証跡として保存。
  xlsx エクスポート（従）を提供

### FR-7x DB（← BR 全般の基盤）

- **FR-71** 主要テーブル（S0 最小集合は §4）: business_profiles, brand_plans, action_plans, sprints,
  loop_runs, tasks, workflows, agents, pair_plan_quality, pair_kpi_measure, evidence, kpi_nodes,
  measurements, learnings, playbooks, assets, approvals, config, spend_ledger
- **FR-72** マイグレーション: スキーマ版数を持ち、前方参照のみで昇格（HELIX 同様、壊す変更をしない）
- **FR-73** 例外支出台帳: `spend_ledger`（サービス・金額・用途・タスク参照）。Seedance 等の例外利用を全件記録

## 3. 非機能要求（NFR）

- **NFR-1 fail-close**: 全ゲートは判定不能時に「通さない」側へ倒す。ゲートの無効化フラグを持たない
- **NFR-2 決定性**: 制作・集計は同一入力→同一出力。非決定要素（生成 AI・外部サイト）は出力を証跡化して固定
- **NFR-3 再開性**: 全ループ・タスクは SQLite の状態から再開可能。プロセス強制終了で状態を失わない
  （遷移は書き込み後に実行）
- **NFR-4 秘匿**: 平文credential ゼロ（FR-47）。ログ・証跡への秘匿情報混入をマスキングで防ぐ
- **NFR-5 可観測性**: すべての状態遷移・ゲート判定・外部操作は構造化ログ（SQLite）に残り、
  「いまどこで何が滞留しているか」を 1 クエリで答えられる
- **NFR-6 支出上限**: `config.spend_cap_monthly`（C・暫定既定値 5,000 円/月）超過で有償経路のタスクを自動停止
- **NFR-7 レート節度**（← BR-F5）: ブラウザ自動化の**書き込み・公開系操作**は人間相当のランダム化された操作間隔を守り、
  対象サービスに負荷をかけない。間隔は固定値でなく範囲からの乱数とする（固定間隔はそれ自体が機械の署名になるため）。
  暫定既定値（C）: 間隔 1〜5 秒の一様乱数、1 媒体あたり公開系操作 1 日 10 件以下。
  読み取り系（ページ遷移・計測エクスポート等）は通常のページ操作速度でよい。
  乱数のシード・生成値は再現性のため構造化ログに記録する（NFR-2 決定性はログ再生で担保）
- **NFR-8 保守性**: 媒体追加がワークフロー＋攻略地図＋接続レジストリ行の追加のみで完結（外殻コード変更ゼロ）
- **NFR-9 法規遵守**: 景表法ステマ規制（FR-24）に加え、メール/LINE 配信は特定電子メール法の
  オプトイン・配信停止導線を機械ゲート化し（MR-HS-3, MR-LINE-2）、リード個人情報は APPI に従い
  収集目的の範囲内でのみ保持・利用する。機械ゲート化できない配信形態は採用しない（fail-close）
- **NFR-10 バックアップ・復旧**: SQLite は日次バックアップ＋世代保持（C・暫定 14 世代）。
  ブラウザセッション・WP はそれぞれ暗号化ストアの複製・WP 側バックアップで復旧可能とする（RSK-06）

> 注: 「暫定既定値」は S0 実装で使う安全側の初期値であり、確定値は初回セットアップ時に H/R/C で充填する
> （br-backbone「未起票」の数値目標後送りは、この暫定値の存在によりテスト可能性を確保した上で維持）。

## 4. S0 ウォーキングスケルトン要件

**目的**: ブログ記事 1 本を「Notion ネタ → ワークスペース制作 → 審査 PASS → WP 公開 → 計測取得 → SQLite 証跡」
まで細く一気通貫（charter §7）。

**最小スキーマ**: tasks, workflows, agents, pair_plan_quality, pair_kpi_measure, evidence, config,
sprints（1 件固定でよい）, measurements（GA4 の PV のみでよい）

**最小構成要素**:

- エンジン: 下位ループ 1 周のみ（上位ループはスタブ。行動計画 1 件は**ハーネスのシードコマンド**で投入 —
  SQL 直接編集は受入基準 5 に反するため用いない）
- ゲート: FR-21（企画↔品質）と FR-27（自己審査禁止）は完全実装。FR-23a（有料指標拒否）は型で実装
- エージェント: writer（制作）と critic（審査）の 2 体 + マイクロループ 1 種
- コネクタ: WP REST（下書き投稿→公開）+ 承認通知（FR-46 の最小版）。Notion 読取りは **S0 では任意**
  （企画入力はシードコマンド投入が正。MCP 読取りが使えれば併用可。本実装は S1・FN-408）
- 計測: GA4 正規 API（ADR-006。POC-03 は疎通検証）→ PV 1 指標の取り込み
- TAKUMI 素材: copywriting / seo-jp / design-evidence-jp あたりをワークフロー 1 本に統合（カタログから引く）

**受入基準（S0 完了条件）**:

1. 記事 1 本が公開され、`evidence` に公開 URL・審査 PASS・commit hash が揃っている
2. ペア未成立の状態で公開 API を呼ぶとエンジンが拒否することがテストで示されている
3. author == verifier のタスク割り当てが拒否されることがテストで示されている
4. 公開後の PV が `measurements` に取得証跡付きで入っている
5. 上記すべてが人手の DB 直接編集なしに、ハーネスの実行だけで達成されている
   （初期データ投入もハーネスのシードコマンド経由。人の関与は環境準備・credential 投入・束縛承認のみ）

**S0 契約**: 正準 DDL・状態遷移表・WF 実行契約・マイグレーション規則・環境契約・S0.1〜S0.3 の
アップデート分割（スコープ維持のまま段階実装）は [s0-contract_v0.1.md](s0-contract_v0.1.md) で確定する。

## 4bis. evidence 最小スキーマ（S0 で確定させる要件レベル定義）

`evidence` は完了判定の正本テーブル。**カラム集合・kind 語彙・型契約の正準定義は
[s0-contract_v0.1.md](s0-contract_v0.1.md) §2（DDL）と §2.1（kind 別 payload 規則）**であり、
本節はその要件レベルの要約である:

- 主キー・task_id（FK）・kind（10 種の語彙: plan_record / commit_hash / review_pass / published_url /
  measurement / screenshot / file_hash / approval / operation_log / dashboard）・value（kind 内の同一性キー）
- typed payload（`payload_json` に kind 別必須キー）・対象資産 ID・commit hash・外部 operation ID の列
- `UNIQUE(task_id, kind, value)` による重複投入防止、`created_by_agent_id`（FK→agents）
- タスク種別ごとの必須 kind 集合は `workflows.required_evidence_json` が宣言し、FR-28 が `done` 遷移時に検証
- カラム追加はマイグレーション（FR-72）で行い、既存 kind の意味変更はしない

## 4ter. 受入条件（AC）— S0 スコープ

方針: **S0 スコープの FR に AC を 1:1 で付す**。S1 以降の FR の AC は各スライス着手時に確定する
（明示 deferred — §6 参照。AC なしでのスライス実装着手は不可）。
各 AC の Given/When/Then 展開（前提 fixture・観測点・期待エラーを含む機械検証形）は
JSON 正本（[json/ac.json](json/ac.json)）に持ち、
fixture と外部環境の前提は [s0-contract_v0.1.md](s0-contract_v0.1.md) の環境契約に従う。

| AC | 対象 FR | 受入条件（検証可能形） |
|---|---|---|
| AC-11 | FR-11 | 遷移表に無い (状態, イベント) の組を与えると遷移が拒否され状態が変化しないことがテストで示される |
| AC-12 | FR-12 | ループステップ到達で tasks 行が生成され、ワークフロー ID・担当・期待成果物型がすべて非 NULL である |
| AC-13 | FR-13 | 検証 FAIL の差し戻しが retry_limit（暫定 3）回で `escalated` になることがテストで示される |
| AC-21 | FR-21 | 審査 PASS レコードなしの公開呼び出しをエンジンが拒否する（S0 受入基準 2 と同一） |
| AC-23 | FR-23 | CAC/ROAS 等の有料指標型の kpi_nodes 登録が拒否される |
| AC-27 | FR-27 | author == verifier の割当が DB 制約とエンジンの双方で拒否される（S0 受入基準 3 と同一） |
| AC-28 | FR-28 | 必須証跡（kind 集合）が欠けたタスクは `done` に遷移できないことがテストで示される |
| AC-33 | FR-33 | config 変更が INSERT で履歴化され、変更前の値と変更理由が後から取得できる |
| AC-41 | FR-41 | 経路の切替がレジストリ行の変更のみで反映される（コード変更なし） |
| AC-42 | FR-42 | playbooks を参照した操作が成功し、成功時に最終成功日時が更新される |
| AC-44 | FR-44 | 成立ペア ID なしの WP 書き込みが拒否され、ありでは下書き→公開が成功する |
| AC-46 | FR-46 | 承認要求が通知され、応答が approvals に証跡化されるまで対象タスクが進行しない |
| AC-47 | FR-47 | リポジトリ・SQLite・ログの全文検索で平文 credential の検出が 0 件である |
| AC-51 | FR-51 | 同一入力ソースからの再実行で同一出力（ファイルハッシュ一致）が得られる |
| AC-54 | FR-54 | 審査 PASS が commit hash に紐づき、hash から成果物ソースを復元できる |
| AC-61 | FR-61 | PV 計測値が該当 kpi_node に紐づき、取得証跡 ID を持って measurements に存在する |
| AC-62 | FR-62 | 破損した入力ファイルはエラー隔離され、正常行のみが measurements に投入される |
| AC-71 | FR-71 | S0 最小スキーマ（§4）の全テーブルが DDL から再現生成できる |
| AC-72 | FR-72 | スキーマ版数が記録され、旧版 DB からの昇格マイグレーションが成功する |

**AC deferred（S1+ で確定）**: FR-14, 15, 16, 22, 24, 25, 26, 31, 32, 34, 43, 45, 52, 53, 55, 63, 73
（対象スライス着手時に AC を先に書き、AC なしで実装しない）

## 5. トレース表（BR → FR/NFR、1 行 1 BR）

| BR | FR / NFR |
|---|---|
| BR-A1 | FR-11 |
| BR-A2 | FR-14 |
| BR-A3 | FR-11, FR-71（brand_plans） |
| BR-A4 | FR-12, FR-13 |
| BR-B1 | FR-21 |
| BR-B2 | FR-22 |
| BR-B3 | FR-28, FR-54, FR-71（evidence, §4bis） |
| BR-B4 | FR-27 |
| BR-C1 | FR-23 |
| BR-C2 | FR-24 |
| BR-C3 | FR-25 |
| BR-C4 | FR-26 |
| BR-D1 | FR-31 |
| BR-D2 | FR-32 |
| BR-D3 | FR-33 |
| BR-D4 | FR-34 |
| BR-E1 | FR-61 |
| BR-E2 | FR-62 |
| BR-E3 | FR-63 |
| BR-F1 | FR-41, FR-73, NFR-6 |
| BR-F2 | FR-42, FR-43 |
| BR-F3 | FR-41, NFR-8 |
| BR-F4 | FR-47, NFR-4 |
| BR-F5 | NFR-7, FR-42, FR-16 |
| BR-G1 | FR-51, FR-54 |
| BR-G2 | FR-55 |
| BR-G3 | FR-52 |
| BR-G4 | FR-44 |
| BR-H1 | FR-31, FR-46 |
| BR-H2 | FR-46 |
| BR-H3 | FR-16, FR-43 |

## 5bis. 上流戦略層（2026-08-01 追補）

上流戦略ループの意味モデル（market_observation〜strategy_revision の 12 モデル）・
strategic_brief／tactical_learning_packet／strategy_revision の 3 契約・S0 境界は
[strategy-loop-requirements_v0.1.md](strategy-loop-requirements_v0.1.md)（SR-01〜16）と
[strategy-learning-contract_v0.1.md](strategy-learning-contract_v0.1.md) を正本とする。
S0 への影響は s0-contract §2 の DDL 追加（strategic_briefs／tactical_learning_packets）と
loop_runs 開始ガードのみで、本書の FR/NFR/AC の分母・S0 スコープは不変（SR-15）。
FR-15 の learnings・FR-22 のレビュー成立は、上流へは TLP の構成要素として還流する。

## 6. 未決・スライス送り

> 優先度と slice の関係: REQ の Must はリリースまでに必須の意（priority）であり、slice（実装順）とは
> 独立の軸である。S0 のスコープは落とさず、s0-contract の S0.1〜S0.3 アップデート分割で段階実装する。

- S1: 還流（FR-15）の実装詳細、レビュー成立イベントの上位接続
- S2: ヒアリングエンジン（FR-31）の質問生成方式、事業前提スキーマ本体
- S3+: 媒体別ワークフロー・攻略地図の個別要件、オートモード移行基準の具体値（C 充填）
- 全スライス共通: config 既定値の確定（初回セットアップ時に H/R で充填。それまでは §3 の暫定既定値を使用）
- S1+ の FR の AC は各スライス着手時に確定（§4ter の deferred リスト。AC なしで実装着手しない）

## 7. 検証・承認の運用

- テスト戦略: 機械ゲート（拒否系）と決定性（NFR-2）・再開性（NFR-3）は pytest で検証する。
  決定性は同一入力の 2 回実行で出力ハッシュ一致、再開性はタスク実行中のプロセス強制終了→再起動で
  状態が失われないことをテストで示す。カバレッジ目標は S0 完了時に確定
- 承認: 文書の draft → confirmed 昇格は [approvals.md](../governance/approvals.md) に記録する
- 用語: 独自語の定義は [glossary_v0.1.md](glossary_v0.1.md) を正本とする
