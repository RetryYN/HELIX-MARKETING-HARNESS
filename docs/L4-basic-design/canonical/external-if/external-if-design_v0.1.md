---
artifact_id: L4-EXTERNAL-IF-DESIGN
lifecycle_status: confirmed
slice: S0
---

# 外部 IF 詳細設計 v0.1（②増補 — コネクタ境界契約）

> status: **confirmed**（2026-08-01 全層再降下 §6 — AI 起草）
> pair: [integration-test-design_v0.1.md](../../integration-tests/integration-test-design_v0.1.md)（②↔④ 文書ペアの増補側 — 結合観測点は④に従属）
> 上位文書: [basic-design_v0.1.md](../basic-design_v0.1.md)（CMP-07〜11・横断設計 §4）／
> [s0-contract_v0.1.md](../../../L3-system-requirements/canonical/s0-contract_v0.1.md)（**DDL・状態遷移・external_operations・環境契約の正準** — 本書は重複記述せず参照で書く）
> 兄弟文書: [error-taxonomy_v0.1.md](../../../L5-detailed-design/canonical/errors/error-taxonomy_v0.1.md)（エラー分類正本）／[approval-design_v0.1.md](../approval/approval-design_v0.1.md)（承認設計）
> 位置づけ: コネクタ層（CMP-07〜11・CMP-13 の外部 read）の公開 IF・intent／結果／エラー型・リトライ・
> 冪等性・秘匿・レート節度の詳細契約を確定する。要求内容は定義しない — FR-41〜47・NFR-7 と矛盾したら上位を優先し本書を改訂する。

---

## 1. 設計原則

1. **intent ベースの防腐層**: kernel・WF 実行器はサービス非依存の intent（意図）だけを発行し、
   各コネクタが経路（mcp/browser/api/wp_rest/wp_cli — 接続レジストリ FR-41 が解決）とサービス固有差を吸収する。
   kernel のコードに `service → 経路` の分岐を置かない（NFR-8 — 媒体追加はレジストリ行＋WF＋攻略地図の追加のみ）。
2. **コネクタは業務状態を書かない**: loop_runs／tasks／evidence への書込みは kernel・evidence API 経由のみ。
   コネクタ所掌テーブル（playbooks・approvals）への永続化はストア副層（`playbooks_store`／`approvals_store`）に限定する
   （基本設計 §1.3）。
3. **実外部操作だけを証跡化し、証跡が先、遷移が後**: route・credential・endpoint・PairPass・
   ApprovalPass・自主 cap の全 preflight を通過した実 read/write だけを CMP-02 所有の
   `ExternalOpRecorder` が `effect` 必須で `external_operations` に記録する。コネクタは request/result
   材料を返すだけで DB を書かない。送信済み行は confirmed／provider rejected／unknown のいずれでも
   row ID に束縛した operation_log をちょうど 1 行記録し、その後に状態遷移する（s0-contract §1・NFR-3）。
4. **fail-close**: 判定不能・照合不能・分類不能はすべて拒否側へ倒す。コネクタ例外は境界で必ず
   ConnectorError（§3）へ正規化し、[error-taxonomy_v0.1.md](../../../L5-detailed-design/canonical/errors/error-taxonomy_v0.1.md) §4 の写像で
   状態機械イベントへ還元する。

## 2. コネクタ公開 IF 表（intent ベース）

各関数は Python の公開 API（PascalCase 型・snake_case 関数）。低レベル client はモジュール非公開（`_client`）とし、
ゲート未通過の呼出し経路をコード構造で塞ぐ（基本設計 CMP-10）。

| 公開 IF | CMP | 対応 FR | intent の意図 | 前提（呼出元が保持するもの） |
|---|---|---|---|---|
| `resolve_route(intent) -> Route` | CMP-07 | FR-41 | service・operation から経路（route_type・認証方式）を解決 | config の registry 行が seed 済み |
| `get_secret(service) -> Secret` | CMP-07 | FR-47 | 暗号化ストアから秘匿値を実行時注入（メモリ内のみ） | credential 投入済み・endpoint 突合可 |
| `run_playbook(intent) -> BrowserResult` | CMP-08/09 | FR-42, FR-43 | 攻略地図の手順どおりのブラウザ操作（読取り／書込み） | 書込み系は idempotency key・PairPass |
| `capture_screenshot(intent) -> EvidenceRef` | CMP-08 | FR-42 | 公開確認・取得物固定のスクショ証跡取得 | 対象 URL が許可リスト内 |
| `create_draft(intent) -> DraftRef` | CMP-10 | FR-44 | Docker WP への下書き作成（専用 idempotency key） | PairPass（CMP-03 `require_pair` のみが生成） |
| `publish_content(intent) -> PublishResult` | CMP-10 | FR-44 | 承認済み下書きの公開（下書きとは別 key） | PairPass ＋ approved な ApprovalPass |
| `upload_media(intent) -> MediaRef` | CMP-10 | FR-44 | WP メディア登録 | PairPass・専用 idempotency key |
| `request_approval(intent) -> ApprovalRef` | CMP-11 | FR-46 | 実通知 transport の `ConnectorIntent(effect=write, policy_category=approval_notification)` と request/result 材料を返す（approvals を書かない） | CMP-02 が CMP-11 approval store のローカル tx で pending 行を先に確定済み |
| `poll_decision(approval_ref) -> Decision` | CMP-11 | FR-46 | 承認応答の照合（読取りのみ — 判定写像は承認設計 §3） | approvals 行が存在 |
| `fetch_metrics(intent) -> FetchResult` | CMP-13 | FR-62 | GA4 Data API 第一経路の読取り（ADR-006）。阻害時のみブラウザエクスポート | 読取専用 credential・property 一致 |

- 上表の実 I/O はすべて `ConnectorIntent.effect` を明示する。`create_draft`／`publish_content`／
  `upload_media`／実通知送出は `write`、Web・DOM・DesignSync・Notion・GA4 等の取得と実 transport poll は
  `read` である。1 connector request = 1 `external_operations` 行とし、Notion の read 1 回と分割 write
  各要求を 1 行へまとめない。
- 実外部操作は必ず `policy_category` を明示する。read は `external_read` だけ、write は
  `content_publish`（公開コンテンツ。service=wp、Docker WP endpoint のみ）、
  `review_sync`（Notion `sync_result` 書戻し。明示 config と完全一致 ApprovalPass 必須）、
  `approval_notification`（Claude Code アプリ `approval_request`。binding 3 項目を確定済み）、
  `approved_paid_operation`（PO 承認と有償 route 必須）の閉集合とする。write は canonical lowercase の
  `rate_scope` も必須、read は NULL。`config.external_write_policy` の exact
  `(policy_category, service, operation, target_endpoint)` tuple と `rate.<rate_scope>.daily_write_cap` を
  preflight で照合し、category／tuple／rate_scope／config 欠落、wildcard、別 endpoint は prepare 前に拒否して
  external_operations／operation_log 0 行とする。「外部書込みは Docker WP のみ」は
  **content_publish** の制約であり、他 category を公開経路として許す意味ではない。
- Notion 同期（FR-45・FN-408）は S1 の追加コネクタであり、本表の intent 規約（`sync_plan(intent)`／`write_back(intent)`）に
  同型で載せる。S0 構造の変更は要しない（基本設計 §6）。
- 承認の decision→状態遷移写像は [approval-design_v0.1.md](../approval/approval-design_v0.1.md) §3 が正準。

## 3. intent／結果／エラー型

型はデータクラス（frozen）。詳細フィールドの検証は⑤詳細設計の DU 割当に従う。

| 型 | 輪郭 |
|---|---|
| `ConnectorIntent` | `{service, operation, effect: Literal['read','write'], policy_category: Literal['external_read','content_publish','review_sync','approval_notification','approved_paid_operation'], execution_mode: Literal['actual'], target_endpoint, rate_scope?, payload_ref, request_hash, request_sequence, idempotency_key?, correlation_key, pair_pass?, approval_ref?}`。write は write category・canonical lowercase rate_scope・request_sequence=1・決定的 idempotency key 必須かつ correlation key と同値。read は category=external_read・rate_scope/idempotency key は NULL、request_sequence は正整数かつ `correlation_key = "read:<task_id>:<request_hash>:<request_sequence>"`。request payload にも category/rate_scope/sequence を持ち、exact policy preflight 合格後にだけ Recorder へ渡せる |
| `ConnectorResult` | `{ok, effect, policy_category, rate_scope?, request_sequence, provider_operation_id?, remote_object_id?, response_hash?, result}`。intent／request payload と同じ category/rate_scope/sequence 必須。read の rate_scope は NULL。provider の operation ID は取得できない rejected／unknown を許すため任意。コネクタは DB row ID／evidence を生成せず、Recorder が結果を `external_operation_row_id` と operation_log evidence ID に束縛する |
| `ConnectorError` | `{kind, retryable, service, operation, message, external_operation_row_id?, provider_operation_id?}`。row ID は Recorder が prepare 済みの sent 後エラーだけに付与し、provider ID は任意。kind は下表 6 値。message・payload に秘匿値・本文を含めない（NFR-4） |
| `PairPass` | CMP-03 `require_pair` だけが生成できる検証済み値オブジェクト（基本設計 CMP-10） |
| `ApprovalPass` | decision = approved かつ binding 3 項目完全一致の照合を通過した検証済み値オブジェクト（承認設計 §5） |

### 3.1 ConnectorError.kind（6 値・retryable 区分）

| kind | 意味 | retryable | 代表事由（分類正本 = error-taxonomy §3） |
|---|---|---|---|
| `absent` | 経路・地図・接続先が存在しない | false | RouteNotRegistered・PlaybookMissing・PlaybookBroken |
| `auth` | 認証不能（credential 未投入・失効・endpoint 不一致） | false | SecretUnavailable・CredentialEndpointMismatch |
| `rate-limit` | レート上限（自主上限 config.rate.* ・外部 429） | true | RateLimitExceeded |
| `timeout` | 応答期限超過（結果未確定） | true（送信前のみ。送信後は sent 照合 — §4） | 接続・応答 timeout |
| `blocked` | 方針により遮断（送信 0 回で拒否） | false | UrlDenied・ProhibitedMediaWrite・ProductionWriteDenied・PaidRouteDenied・ApprovalRequired |
| `unknown` | 分類不能・結果照合不能 | false | OperationUnverifiable・未知の外部エラー |

## 4. リトライ・タイムアウト・冪等性

正準は s0-contract §1（external_operations）・§3.3（再開規則）。本節はコネクタ層の実装規約だけを定める。

| 観点 | 規約 |
|---|---|
| リトライ対象 | `retryable = true`（rate-limit／送信前 timeout）のみ。retry_count の消費は verify_fail 系だけであり、通信再送は**同一 idempotency key の無消費再送**（s0-contract §3.2） |
| リトライ非対象 | absent／auth／blocked／unknown は即時 fail（分類写像 §5 へ）。自動リトライ経路を持たない |
| タイムアウト | 操作別に config（`config.timeout.<service>.<operation>_sec`）で宣言。送信後 timeout は失敗扱いにせず sent のまま結果照合へ回す |
| 冪等キー | 書込み 1 操作 = 1 idempotency key = external_operations 1 行。下書き作成と公開は別 key の別行。`idempotency_key` UNIQUE が二重送信を検出（BR-I7） |
| sent 照合 | 送信後クラッシュ・timeout は external_operations.status を先に照合: prepared は同一 key で再送可、sent はリモート側を external operation ID／remote object ID／idempotency key で照合し、成功確認で confirmed 化・証跡補完。照合不能は unknown とし**再送せず escalate**（s0-contract §3.3 — 最危険 kill point で再送 0 回） |
| key 非対応サービス | WP 側の決定的な meta key／slug として idempotency key を保存（又は operation ID／投稿 URL の事前照合）。照合不能時は fail-close（s0-contract §3.3） |

- read/write は同じ prepared→sent→confirmed／rejected／unknown lifecycle を使う。write は同一
  idempotency key（correlation key も同値）の二重送信を禁止する。read は idempotency key を持たず、
  再取得は安全だが各実 request を別行とし、同一 logical
  poll の request hash を固定して `request_sequence=1,2,...` を割り当て、
  `read:<task_id>:<request_hash>:<request_sequence>` で関連付ける。intent・request payload・result・
  external_operations・operation_log の sequence は一致必須。送信済み read の再試行は元行を上書きせず、
  元行を terminal＋operation_log へ確定してから新しい request 行を発行する。
- policy_category はすべての actual intent／request payload／result／external_operations／
  operation_log で同値。write の rate_scope も同じ 5 面で同値、read は intent／result／外部行で
  NULL とし、operation_log payload には `rate_scope: null` を常設して SQL `IS` 相当で外部行と照合する。
- provider rejected／unknown でも実 request が送信済みなら operation_log を 1 行作る。束縛正本は
  `external_operation_row_id` であり、provider operation ID の欠落を理由に証跡を捏造しない。
- mock／fixture／dry-run は実 request ではないため external_operations／operation_log をともに 0 行とし、
  予定 fingerprint と模擬結果は秘匿化済み process logger にだけ記録する。

## 5. エラー分類 → fail-close 写像表

分類はコネクタ境界で確定し、kernel へは状態機械イベントとして伝える（事由は `failure_code` へ記録 — s0-contract §3.2）。
型の全数台帳は [error-taxonomy_v0.1.md](../../../L5-detailed-design/canonical/errors/error-taxonomy_v0.1.md) が正本。

| kind | 状態機械イベント | 遷移先 | 振る舞い |
|---|---|---|---|
| `absent` | escalate（地図・経路の人間対処が必要な場合）／non_retryable_failure（代替経路・代替 task 発行可の場合） | escalated／failed | フォールバック経路があればレジストリ解決で切替。外部操作前なので秘匿化済み process logger のみ。なければ倒す |
| `auth` | escalate | escalated | credential 再投入は人の関与（s0-contract §3.1 ガード）。外部操作は開始しない |
| `rate-limit` | retryable_failure（retry_count < config.retry_limit）／retry_exhausted | running（再試行）／escalated | 自主上限（日次 cap）は当日拒否・翌日まで waiting（NFR-7 violation_behavior） |
| `timeout` | retryable_failure（送信前）／escalate（sent 照合不能） | running／escalated | 送信後は §4 の sent 照合が先。推測で成功扱いしない |
| `blocked` | non_retryable_failure | failed | 送信 0 回で拒否し秘匿化済み process logger に理由記録。external_operations／operation_log は 0 行。ゲート層の拒否（GateRejected 系）と同格 |
| `unknown` | escalate | escalated | fail-close（安全側）。unknown のまま再送しない |

## 6. 認証・秘密（FR-47・NFR-4）

- **一元化**: 経路解決（registry）と秘匿注入（secrets）は CMP-07 に一元化する。コネクタは `get_secret(service)` の
  実行時注入だけを受け取り、credential を引数・設定ファイル・環境変数として横流ししない。
- **保管先**: OS キーチェーン又は `cryptography`（Fernet）暗号化ファイルストアのみ（BR-F4）。
  **SQLite・repo・ログ・evidence への平文格納は禁止**。復号値はメモリ内のみで、外部操作後に永続化しない。
- **マスキング**: ログ・operation_log・evidence への全書出しはマスキング層（config.secret.masking_patterns）を通過する。
  平文検知は永続化・外部操作より前に拒否し、CredentialLeakDetected を秘匿化済み process logger に記録して
  当該タスクを escalated へ誘導する。external_operations／operation_log は作らない。
  CMP-04 証跡ストアの secret 混入検査と二重化する（基本設計 CMP-04）。
- **テスト／本番分離**: credential は物理別ファイルで保管し、接続前に endpoint と突合する。
  テスト credential→本番 endpoint・本番 credential→Docker/mock の組合せは CredentialEndpointMismatch で接続前に拒否する
  （環境契約 = s0-contract §6）。
- **取得不能**: SecretUnavailable は外部操作を開始せず（fail-close）、credential 再投入（人の関与）へ escalate する。

## 7. レート節度（NFR-7・BR-F5）

| 項目 | 契約 |
|---|---|
| 対象 | 書込み・公開系の外部操作のみ。**読取り系は対象外**（通常速度可 — NFR-7 固定） |
| 間隔 | 連続書込み操作間に一様乱数の待機を挿入。範囲は `config.rate_interval_min_sec`〜`config.rate_interval_max_sec`（暫定 1〜5 秒・一様分布）。固定間隔は機械署名として禁止（分散 > 0） |
| 乱数 | Python `random.Random(seed).randint(min_sec, max_sec)`（MT19937・整数・両端包含）を固定し、seed・algorithm ID・生成値を秘匿化済み process logger へ 100% 記録。同一 seed で間隔列を再現できる（NFR-2） |
| 日次上限 | write intent の canonical lowercase `rate_scope` に対する required config `rate.<rate_scope>.daily_write_cap`。値の正本は各 BR／MR の hard cap とし本書に固定値を複製しない。同一 rate_scope で `effect='write'` かつ `sent_at >= day_start_utc AND sent_at < next_day_start_utc` の行を status を問わず数え、実送信済み rejected／unknown も消費し read は除外。到達後は翌日まで waiting。WP の `config.rate.wp.burst_per_min` も required config とする |
| 並行制御 | CMP-02 の単一 writer と `BEGIN IMMEDIATE` 相当の境界で UTC 半開区間 COUNT＋未送信 prepared 予約照合＋次 prepared 送信枠予約を直列化する。予約が sent 又は再開照合で確定するまで同一 rate_scope の次予約を発行せず、再起動時は prepared 行から予約を復元する |
| 媒体別 config | 間隔範囲・cap はすべて required config 行（ハードコード禁止 — 型×動的充填）。各 BR／MR hard cap から降下し、欠落は fail-close。変更は config INSERT（履歴保持 FR-33）のみ |
| 違反時 | 上限超過・範囲逸脱・cap 欠落の書込みは Recorder の `prepare` より前に拒否し、秘匿化済み process logger へ記録（fail-close）。external_operations／operation_log は 0 行。seed 未記録は決定性違反としてテスト red |

## 8. 実装への持ち越し

- intent／結果型の詳細フィールドと検証は⑤詳細設計（DU 割当）・⑥単体テスト設計の該当 TC/UT で確定する。
- 本書の写像表（§5）は error-taxonomy §4 と同一内容を保つ（片方だけの改訂は差戻し — 文書ペア規律）。
- S0.2 実装（CMP-07〜11）の test-first は⑥の割当テストを赤→実装の順で行う（CLAUDE.md 実装規律）。
