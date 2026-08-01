---
artifact_id: L5-ERROR-TAXONOMY
lifecycle_status: confirmed
slice: S0
---

# エラー分類正本 v0.1（②増補 — エラー台帳）

> status: **confirmed**（2026-08-01 全層再降下 §6 — AI 起草）
> pair: [integration-test-design_v0.1.md](../../../L4-basic-design/integration-tests/integration-test-design_v0.1.md)（②↔④ 文書ペアの増補側 — 拒否系 ITC/TC の分類根拠）
> 上位文書: [basic-design_v0.1.md](../../../L4-basic-design/canonical/basic-design_v0.1.md)（§4 エラー 3 系正規化）／
> [s0-contract_v0.1.md](../../../L3-system-requirements/canonical/s0-contract_v0.1.md)（**状態遷移表・イベント分類の正準** — 本書は重複記述せず参照で書く）
> 抽出元: [json/fr/fr-contracts.json](../../../L3-system-requirements/canonical/functional/fr-contracts.json)・
> [json/ac/ac-contracts.json](../../../L3-system-requirements/canonical/acceptance/ac-contracts.json) の error_type 全数（AC 155 件走査）
> 兄弟文書: [external-if-design_v0.1.md](../../../L4-basic-design/canonical/external-if/external-if-design_v0.1.md)（ConnectorError 境界型）／
> [approval-design_v0.1.md](../../../L4-basic-design/canonical/approval/approval-design_v0.1.md)（承認系分類の運用正準）
> 位置づけ: 例外型名・意味・発生層・retryable・fail-close 先・証跡の分類台帳。**型名の正規名は本書が宣言する**。
> 遷移先の正しさは s0-contract §3 が正準であり、矛盾したら上位を優先し本書を改訂する。

---

## 1. 3 系正規化（基本設計 §4 の再掲参照）

すべての例外は境界で次の 3 系（＋境界型 1 つ）へ正規化してから状態機械へ還元する。

| 系 | 状態機械イベント | 意味 |
|---|---|---|
| `RetryableError` | retryable_failure（上限到達で retry_exhausted） | 再実行で回復し得る一時失敗 |
| `FatalError` | non_retryable_failure（局所・代替発行可）又は fatal_failure/escalate（人の関与） | 自動回復不可 |
| `GateRejected` | 遷移拒否（状態・retry_count・証跡は不変） | ゲート不通過。拒否も state_transitions に guard_result = rejected で記録 |
| `ConnectorError` | kind 別写像（external-if-design §5） | コネクタ境界型。kernel 到達前に上記 3 系へ還元される |

- 分類は**失敗を検出した層**（ゲート・コネクタ・kernel）が事由コードから決定し `tasks.failure_code` に記録する
  （s0-contract §3.2）。
- 判定不能はすべて拒否・失敗側へ倒す（fail-close — NFR-1）。

## 2. 台帳の読み方

- **発生層**: kernel（状態機械・オーケストレータ）／gates（ゲートエンジン・充填検証）／store
  （db・evidence・config・資産等の永続層）／connector（外部 I/O・レジストリ・秘匿）。
- **retryable**: 自動リトライ（retryable_failure）の対象か。差戻し（verify_fail）は retryable とは区別する。
- **fail-close 先**: 発火する状態機械イベントと遷移先（正準 = s0-contract §3）。「拒否」= 遷移不発・状態不変。
- **証跡**: 拒否・失敗が残す観測点。

## 3. 分類台帳（正規名・全数）

### 3.1 kernel 層

| 型名 | 意味 | retryable | fail-close 先 | 証跡 |
|---|---|---|---|---|
| TransitionRejected | 遷移表に無い組合せ・ガード不成立・終端からの遷移要求（FR-11/13/16） | — | 拒否（状態不変） | state_transitions（guard_result = rejected） |
| TaskIssuanceRejected | workflow 不在・active agent 不足・principal 同一・T-PUB ペア未成立の発行要求（FR-12） | — | 拒否（tasks 行を作らない） | 例外＋発行元ログ |
| SprintStartRejected | KPI 目標欠如等での sprint 開始拒否（FR-14 — S1） | — | 拒否（planned のまま） | sprints 行不変・下位 run start の rejected 記録 |
| SelfReviewRejected | 自己審査割当・verifier execution の claim（FR-27 — エンジン層。DB 層は IntegrityError と二重） | — | 拒否 | 例外＋DB CHECK |
| LoopScopeViolation | 上流/下流ループの所掌違反（SR-01 — 下流からの上流正本更新等） | — | 拒否 | 例外＋保護トリガ |
| LearningSchemaViolation | learning_json の schema 違反（FR-15 — S1） | — | 拒否（learnings 行を作らない） | 例外 |
| SlotUnfilledRejected | 必須スロット未充填での確定要求（FR-31 — 三エンジン） | — | 拒否 | 例外 |
| AnswerTypeInvalid | ヒアリング応答の型不一致（FR-31） | — | 拒否（再照会） | 例外 |
| UnsourcedValueRejected | 出典なし値の投入（FR-32 — リサーチ） | — | 拒否 | 例外 |
| StaleSourceRejected | 鮮度切れ出典の投入（FR-32） | — | 拒否 | 例外 |

### 3.2 gates 層

| 型名 | 意味 | retryable | fail-close 先 | 証跡 |
|---|---|---|---|---|
| GateRejected | 実行時ゲート不通過の基底型（本節の各型が具体） | — | 拒否（状態不変） | state_transitions rejected／operation_log |
| PairNotEstablished | 企画↔品質ペア不成立・revoked の公開判定（FR-21/15） | — | T-PUB を non_retryable_failure → failed。WP API を呼ばない | operation_log 拒否行 |
| ReviewNotEstablished | KPI 目標↔計測スナップショットのペア不成立（FR-22 — S1） | —（計測後着で再判定可 = 待機） | 不成立（レビュー・還流を発生させない） | pair_kpi_measure 不変 |
| PaidMetricRejected | 有料指標型（CAC/ROAS/広告費/CPC/CPM）の登録要求（FR-23/61） | — | 登録拒否 | 例外＋DB CHECK |
| UrlDenied | 許可リスト外 URL への遷移（FR-23 — deny-by-default） | — | 遷移拒否 | operation_log 拒否行 |
| PrLabelMissing | PR 表記ブロック欠落・判定不能のアフィリエイト成果物（FR-24 — S1） | — | T-PUB を non_retryable_failure → failed | operation_log 拒否行 |
| EthicsViolation | P5 該当・境界事例（FR-25 — S1） | —（差戻し = verify_fail） | verify_fail → in_progress（上限で verify_fail_exhausted → escalated） | verifier FAIL 証跡・state_transitions |
| EvidenceIncomplete | 必須証跡 kind の欠落・kind 規則違反での done 要求（FR-28） | — | done 拒否（verifying のまま） | state_transitions rejected |
| ApprovalRequired | approved な承認なしの公開・金銭系書込み要求（FR-26/44/46） | — | 拒否（外部送信 0 回） | operation_log 拒否行 |
| ApprovalBindingMismatch | binding 3 項目の不一致応答・照合（FR-44/46） | — | 公開拒否・応答は無効として待機継続 | operation_log 拒否行 |
| ApprovalRejected | 承認応答 decision = rejected（FR-26/46 — 正規名。§5 参照） | — | non_retryable_failure → failed（代替 task 発行可） | approvals 行・state_transitions |
| ApprovalExpired | 承認応答 decision = expired（FR-26/46） | —（再要求で待機継続） | 再要求。config.approval_retry_limit 到達で escalate | approvals 再要求系列 |
| ApprovalRetryExhausted | expired 再要求が approval_retry_limit 到達（FR-46） | — | escalate → escalated | approvals 系列・state_transitions |
| CommitHashMismatch | review_pass の hash と制作 hash の不一致（FR-54） | — | ペア成立拒否・公開拒否 | 例外＋operation_log |
| InvalidCommitHash | 不正桁の commit hash（FR-54） | — | 拒否 | 例外 |
| KpiNodeInvalid | KPI ノード定義の不整合（FR-61） | — | 登録拒否 | 例外 |
| UnversionedSourceRejected | 版管理外ソースからの制作・生成要求（FR-51/53） | — | 拒否 | 例外 |
| WpTargetDenied | 制作出力先としての不正 WP 対象（FR-51） | — | 拒否 | 例外 |
| ContentBodyRejected | 本文検証不合格（FR-55） | — | 登録拒否 | 例外 |
| AssetReferenceInvalid | 資産参照の不整合・循環（FR-55） | — | 登録拒否 | 例外 |

### 3.3 store 層（db・evidence・config・台帳）

| 型名 | 意味 | retryable | fail-close 先 | 証跡 |
|---|---|---|---|---|
| IntegrityError | SQLite 原始例外（CHECK・UNIQUE・FK・保護トリガ）。**業務層の分類名として使わない**（§5） | — | 拒否（transaction rollback） | DB 例外 |
| AppendOnlyViolation | append-only テーブルへの UPDATE/DELETE（FR-71 — evidence・state_transitions・strategic_briefs・TLP） | — | 拒否（保護トリガ） | トリガ ABORT |
| ConfigAppendOnlyViolation | config への UPDATE/DELETE（FR-33 — AppendOnlyViolation の config 特化名） | — | 拒否 | トリガ ABORT |
| ConfigReasonMissing | reason なしの config INSERT（FR-33） | — | 拒否 | 例外 |
| ConfigKeyUnresolved | 未定義 key の config 参照（FR-33） | — | 拒否（既定値へ黙って倒さない） | 例外 |
| SchemaVerificationFailed | DDL 相当性・FK 検査の不成立（FR-71） | — | 起動・適用拒否 | 検証ログ |
| MigrationChecksumMismatch | migration checksum の不一致（FR-72） | — | 適用停止 | schema_version 照合 |
| MigrationVerifyFailed | 昇格後検証（integrity_check 等）の失敗（FR-72） | — | backup 復元・停止 | 検証ログ |
| ProfileKeyConflict | profile_key の重複（FR-34） | — | 拒否 | 例外＋UNIQUE |
| CrossProfileAccessDenied | プロファイル横断アクセス（FR-34） | — | 拒否 | 例外 |
| ArchivedProfileWriteDenied | archived プロファイルへの書込み（FR-34） | — | 拒否 | 例外 |
| SpendRecordIncomplete | 支出台帳の必須項目欠落（FR-73） | — | 記録拒否（有償操作は開始しない） | 例外 |
| DuplicateSpendEntry | 同一 (service, external_operation_id) の二重計上（FR-73） | — | 拒否 | UNIQUE |
| ExternalReferenceDetected | 自己完結出力への外部参照混入（FR-63） | — | 出力拒否 | 例外 |

### 3.4 connector 層

kind 列は [external-if-design_v0.1.md](../../../L4-basic-design/canonical/external-if/external-if-design_v0.1.md) §3.1 の ConnectorError.kind への正規化先。

| 型名 | 意味 | kind | retryable | fail-close 先 | 証跡 |
|---|---|---|---|---|---|
| RouteNotRegistered | 未登録 service の経路解決（FR-41） | absent | false | escalate 誘導（経路なし）又は failed | operation_log |
| PaidRouteDenied | 例外宣言なしの有償 API 経路解決（FR-41） | blocked | false | 拒否 | operation_log |
| ProhibitedMediaWrite | X へのブラウザ書込みの登録・解決・実行要求（FR-41/42 — BR-M-X-4） | blocked | false | 拒否（バイパスなし） | operation_log |
| PlaybookMissing | 攻略地図行の不在（FR-42） | absent | false | 拒否（自己修復は FR-43 へ委譲） | operation_log |
| PlaybookBroken | status = broken の地図参照（FR-42） | absent | false | 拒否（書込みを開始しない） | operation_log |
| PlaybookRepairFailed | 自己修復 1 回の失敗（FR-43 — S2。escalate 事由コード） | absent | false | escalate → escalated | operation_log 試行記録 |
| RateLimitExceeded | 日次 cap・バースト上限・外部 429（FR-42/44） | rate-limit | true | retryable_failure（自主上限は当日拒否・翌日まで waiting） | operation_log |
| ProductionWriteDenied | Docker 以外の WP endpoint への書込み設定（FR-44 — 環境契約 §6） | blocked | false | 拒否（送信 0 回） | operation_log |
| NotionUnavailable | Notion 応答不能・認証失効（FR-45 — S1） | timeout/auth | 経路による | 同期タスクのみ failed（ループ本体へ波及させない） | operation_log |
| SecretUnavailable | 秘匿値の未投入・復号失敗・失効（FR-47） | auth | false | escalate（credential 再投入 = 人の関与） | operation_log（秘匿値なし） |
| CredentialLeakDetected | 書出しへの平文 credential 混入検知（FR-47） | — | false | マスクした上で当該タスクを escalate | operation_log |
| CredentialEndpointMismatch | テスト/本番 credential と endpoint の組合せ不一致（FR-47） | auth | false | 接続前拒否 | operation_log |
| OperationUnverifiable | sent のまま結果照合不能（FR-42/44 — unknown 化の事由コード） | unknown | false | escalate（再送しない — s0-contract §3.3） | external_operations（unknown） |
| ImportSourceInvalid | 取得物の全破損（FR-62 — 部分破損は隔離＋正常継続） | — | false | non_retryable_failure → failed | operation_log・隔離記録 |
| DesignTokenUnavailable | デザイントークン取得不能（FR-52 — S1） | absent | false | 拒否 | 例外 |
| PipelineExecutionFailed | 生成パイプラインの実行失敗（FR-53 — S1） | — | 状況による（一時失敗は retryable_failure） | failed 又は再試行 | 例外・ログ |

### 3.5 戦略層（gates 系 — strategy-loop-design が実装正本）

| 型名 | 意味 | retryable | fail-close 先 | 証跡 |
|---|---|---|---|---|
| ObservationInterpretationMixRejected | 観測事実と AI 解釈の混在フィールド（SR-02 — 正規名。§5 参照) | — | 拒否 | 例外 |
| ModelSchemaRejected | 意味モデルの schema 違反（SR-03） | — | 拒否 | 例外 |
| PersonaSegmentRejected | 人口統計ペルソナの正本化要求（SR-04 — 状況ベースセグメントが正本） | — | 拒否 | 例外 |
| IncompleteStrategyRejected | 戦略必須フィールドの欠落・空文字（SR-05） | — | 拒否 | 例外 |
| BriefSchemaRejected | strategic_brief の schema 違反（SR-06） | — | 拒否（brief を発行しない） | 例外 |
| RevisionEvidenceRejected | 根拠・反証を欠く strategy_revision（SR-10/12） | — | 拒否 | 例外 |
| ContentValueDeclarationRejected | 認識変化資産の 5 宣言欠落（SR-13） | — | 拒否 | 例外 |
| MediaRoleRejected | 媒体役割語彙外の指定・台帳欠損（SR-14） | — | 拒否 | 例外 |
| GateFailure | CI ゲートの exit 非 0（SR-15 — 実行時ゲートの GateRejected とは別概念。§5 参照） | — | CI fail（マージ・確定の拒否） | CI ログ |

## 4. fail-close 写像の要約

| 分類 | イベント | 遷移先 | 正準 |
|---|---|---|---|
| ゲート拒否（GateRejected 系） | なし（遷移不発）又は non_retryable_failure | 状態不変又は failed | s0-contract §3.2 |
| 一時失敗（RetryableError 系） | retryable_failure／retry_exhausted | running 再試行／escalated | s0-contract §3.1 |
| 局所失敗（FatalError — 代替発行可） | non_retryable_failure | failed | s0-contract §3.1/§3.2 |
| 人の関与が必要（FatalError） | escalate（tasks）／fatal_failure（loop_runs） | escalated | s0-contract §3.1/§3.2 |
| 承認系 | 承認設計 §3 の decision 写像 | failed／waiting 継続／escalated | approval-design §3 |

## 5. 正規化表（同義の別名の吸収）

抽出時に検出した表記ゆれ・混同を以下の正規名へ吸収する。以後の文書・実装・テストは正規名を使う
（旧名は AC/FR 正本の改訂時に置換し、それまで read 互換として解釈する）。

| 出現名（出現箇所） | 正規名 | 判定 |
|---|---|---|
| NonRetryableFailure（AC-46-2） | ApprovalRejected | 例外名とイベント名の混同。イベントは `non_retryable_failure`（snake_case）、承認拒否の例外正規名は ApprovalRejected |
| ObservationInterpretationRejected（AC-SR-02 系の一部） | ObservationInterpretationMixRejected | 同義の短縮表記。Mix 付きを正規名とする |
| IntegrityError（AC 多数） | （層内正規化）AppendOnlyViolation 等の意味例外 | DB 原始例外。ストア層境界で意味例外へ変換して伝播し、業務層の分類名として IntegrityError を使わない。DB 層の二重防御としての記載は維持 |
| ConfigAppendOnlyViolation | AppendOnlyViolation（config 特化名として存置） | 別名ではなく下位分類。テーブル特化名の新設は今後行わず AppendOnlyViolation ＋対象テーブル名で表す |
| PairRequired（FR-44）と PairNotEstablished（FR-21） | 両立（同義ではない） | PairRequired = コネクタ入口の前提違反（ペア ID 未提示）、PairNotEstablished = ゲート判定の不成立。役割を宣言して混用を禁止 |
| GateFailure（SR-15）と GateRejected | 両立（同義ではない） | GateFailure = CI ゲートのプロセス失敗、GateRejected = 実行時ゲート基底。相互に代用しない |
| PlaybookBroken と PlaybookMissing | 両立 | 不在と破損は別事由。いずれも kind = absent へ収束 |

## 6. 実装への持ち越し

- 例外クラス階層（`RetryableError`／`FatalError`／`GateRejected`／`ConnectorError` と本台帳の具体型）は
  ⑤詳細設計の DU 割当で配置を確定し、⑥の拒否系 TC が型名単位で検証する。
- 本台帳への型追加は AC/FR の error_type 追記と同一コミットで行う（分母ラチェットと同じ規律）。
