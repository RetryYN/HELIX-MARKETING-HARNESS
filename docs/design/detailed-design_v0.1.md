# 詳細設計書 v0.1（⑤）

> status: **confirmed**（2026-07-31 PO 承認 — 詳細設計完遂指示。AI 起草）
> pair: [unit-test-design_v0.1.md](unit-test-design_v0.1.md)（単体テスト設計⑥ — HELIX 式 ⑤↔⑥ 文書ペア）
> 上位文書: [basic-design_v0.1.md](basic-design_v0.1.md)（②。CMP 13・依存規則・横断設計はここが正準）／
> [s0-contract_v0.1.md](../requirements/s0-contract_v0.1.md)（DDL・遷移・evidence 型・WF 契約の正準）
> JSON 正本: [json/detailed.json](json/detailed.json)（DU 台帳＝分解・対応の正本。**公開 API 署名の正本は本書 MD**）
> 位置づけ: ②の CMP 13 を **DU（設計ユニット）23 モジュール**に分解し、公開 API・エラー・データ接触を
> 実装単位で確定する。契約の再定義はしない。

---

## 1. 分解規約

- DU = `src/helix/` 直下の 1 実装モジュール。**DU は必ず 1 つの CMP に属し、全 CMP は 1 つ以上の DU を持つ**
  （ゲート G-DU-CMP が機械検証）。
- 公開 API は本書の署名が正本。private（`_` 接頭）は実装裁量。引数・戻り値の `conn` は
  `db.connect()` が返す接続のみ（PRAGMA foreign_keys=ON 保証済み）。
- 例外は基本設計 §4 の 3 系（`RetryableError` / `FatalError` / `GateRejected`）へ境界で正規化する。
  `GateRejected` は状態・DB を変更しない（記録は state_transitions の rejected 行のみ）。

## 2. DU 台帳

| DU | モジュール | CMP | 主対応 FN |
|---|---|---|---|
| DU-01 | kernel/state.py | CMP-01 | FN-101, FN-704 |
| DU-02 | kernel/orchestrator.py | CMP-02 | FN-102, FN-103 |
| DU-03 | kernel/assigner.py | CMP-02 | FN-105 |
| DU-04 | kernel/workflow.py | CMP-02 | FN-104 |
| DU-05 | gates/pair.py | CMP-03 | FN-201 |
| DU-06 | gates/publish.py | CMP-03 | FN-202 |
| DU-07 | gates/zero_ad.py | CMP-03 | FN-204 |
| DU-08 | gates/evidence_check.py | CMP-03 | FN-208 |
| DU-09 | evidence/store.py | CMP-04 | FN-703 |
| DU-10 | db/connect.py | CMP-05 | FN-701 |
| DU-11 | db/migrate.py | CMP-05 | FN-702 |
| DU-12 | config/store.py | CMP-06 | FN-305 |
| DU-13 | registry/resolver.py | CMP-07 | FN-401 |
| DU-14 | registry/secrets.py | CMP-07 | FN-411 |
| DU-15 | connectors/browser.py | CMP-08 | FN-402 |
| DU-16 | connectors/playbooks.py | CMP-09 | FN-404 |
| DU-17 | connectors/wp.py | CMP-10 | FN-406 |
| DU-18 | connectors/approval.py | CMP-11 | FN-409 |
| DU-19 | content/generate.py | CMP-12 | FN-501 |
| DU-20 | content/versioning.py | CMP-12 | FN-511 |
| DU-21 | measure/kpi.py | CMP-13 | FN-601 |
| DU-22 | measure/fetch.py | CMP-13 | FN-602 |
| DU-23 | measure/parse.py | CMP-13 | FN-603 |

## 3. モジュール仕様

### DU-01 kernel/state.py

- `transition(conn, entity_type: str, entity_id: int, event: str, actor_agent_id: int | None, details: dict, clock: Clock) -> TransitionResult`
  — 遷移表（docs/requirements/json/s0/transitions.json をパッケージデータとして同梱）を照合。
  未定義組合せは guard 評価前に `GateRejected`。許可時は guard 実行→状態 UPDATE→state_transitions
  INSERT を単一 transaction でコミット。拒否も rejected 行を別 transaction で記録する。
- `register_guard(event: str, fn: Callable[[Connection, Row], GuardResult]) -> None` — 登録制 guard。
  未登録 event の許可遷移は `FatalError`（配線漏れを実行時 fail-close）。
- `TransitionResult(entity, from_state, to_state, transition_id)` は frozen dataclass。
- 終端状態（done/failed/escalated/completed/cancelled）からの遷移要求は常に `GateRejected`。

### DU-02 kernel/orchestrator.py

- `issue_task(conn, loop_run_id, step: WorkflowStep, clock: Clock) -> int` — tasks 行生成。
  `tasks.step_key`・`tasks.attempt` 列（DDL の `UNIQUE (loop_run_id, step_key, attempt)`）を正本に、
  idempotency_key = `f"{loop_run_id}:{step.key}:{attempt}"`。採番と発行は**単一 transaction** で:
  (1) 同一 (loop_run_id, step_key) に非終端の既存 task があればその id を返す（再利用 — 新規発行しない）、
  (2) なければ attempt = 終端行数 + 1 で INSERT、(3) UNIQUE 衝突時は再読して既存を
  返す（並行発行の最終防衛）。クラッシュ後の再実行は (1) により冪等。workflow_id・author・verifier・
  expected_output_kind 非 NULL を組立時に保証。
- `claim(conn, task_id, execution_id, clock) -> None` — lease 取得: `lease_owner_execution_id`・
  `lease_expires_at`（`config.lease_ttl_sec`）・`heartbeat_at` を `row_version` の楽観ロックで更新。
  **execution が task の `author_agent_id` に属さない場合は `GateRejected`**（verifier・無関係 agent の
  execution は lease を取れない。principal は複合 FK で agents と一致強制）。
  失効前の他 execution からの claim も `GateRejected`。
- `run_microloop(conn, task_id, executor, verifier, retry_limit_key="retry_limit") -> MicroloopResult`
  — submit→verify 反復。FAIL ごとに verify_fail 遷移（retry_count 消費）、上限到達で escalated。
- `resume(conn, entity_type, entity_id, clock) -> ResumeAction` — s0-contract §3.3 の全行を実装:
  pending 再 claim／in_progress 外部操作前は workspace・入力・既存証跡再読込／外部操作中後は
  `external_operations.status` で分岐（prepared=再送可、sent=リモート照合→confirmed 化、
  照合不能=unknown で escalate・再送禁止）／verifying は既存 PASS/FAIL 再採用
  （retry 二重加算なし）／waiting は充足再照合。判断根拠は DB 行のみ（メモリ状態禁止）。

### DU-03 kernel/assigner.py

- `assign(conn, author_role, verifier_role) -> Assignment` — active かつ **principal の異なる**
  agent の組（`agents.principal` 比較）。同一 principal しか存在しなければ `GateRejected`
  （tasks の CHECK と二重防御 — ID 違いだけの自己審査を封じる）。T-REVIEW の verifier は critic 以外。

### DU-04 kernel/workflow.py

- `load(conn, workflow_key, version=None) -> WorkflowDef` — definition_json / required_evidence_json の
  schema 検証つき読込（壊れた定義は `FatalError`）。
- `run_step(conn, task_id, step, ctx) -> StepOutcome` — ステップ実行。出力保存は kernel/evidence 経由。
  失敗は 3 系例外へ正規化し、遷移判断は呼出し側（DU-02）に委ねる（勝手に done へ進めない）。

### DU-05 gates/pair.py

- `establish(conn, plan_id, review_task_id, review_evidence_id, clock: Clock) -> PairPass` — review_pass 証跡の
  hash が制作 commit hash と一致する場合のみ pair_plan_quality(passed) を INSERT し `PairPass` を返す。
- `revoke_if_changed(conn, plan_id, current_commit_hash) -> bool` — 企画/commit 変更検知で revoked。
- `require_pair(conn, plan_id) -> PairPass` — passed 行がなければ `GateRejected`。
  **`PairPass` の偽造防止**: `__init__` はモジュール内部 sentinel token を要求し（不一致は `FatalError`）、
  生成関数は `establish`／`require_pair` のみ。frozen dataclass ＋ token で構築独占を実行時にも強制する。

### DU-06 gates/publish.py

- `check_publishable(conn, plan_id, commit_hash) -> PairPass` — require_pair＋hash 一致＋証跡完備を
  まとめて検証する公開前ゲート。拒否時はコネクタ呼出しに到達しない。

### DU-07 gates/zero_ad.py

- `check_metric_type(metric_type: str) -> None` — deny 型（cac/roas/ad_spend）は `GateRejected`
  （kpi_nodes の CHECK と二重）。
- `check_domain(url_or_domain: str, denylist: list[str]) -> None` — config の広告ドメイン denylist 照合。

### DU-08 gates/evidence_check.py

- `check_complete(conn, task_id) -> None` — 現 workflow の required kind 全存在＋各 kind 規則を
  DU-09 の validator で再検証。欠落・違反は `GateRejected`（done 遷移 guard から呼ばれる）。

### DU-09 evidence/store.py

- `record(conn, task_id, kind, value, payload: dict, clock: Clock, *, asset_id=None, commit_hash=None, external_operation_id=None, file_path=None, file_hash=None, created_by_agent_id=None) -> int`
  — s0-contract §2.1 の kind 別必須キー・列整合・追加検証（PASS 値、reviewer≠author、桁数、
  approvals 相互整合等）を INSERT 前に実施。違反は `GateRejected`。credential/secret パターン
  （鍵語・トークン形状の正規表現集合、config 拡張可）の混入も拒否。
- `for_task(conn, task_id, kind=None) -> list[Evidence]` ／ `exists(conn, task_id, kind, value) -> bool`
  — read-only。UPDATE/DELETE API は存在しない。重複は UNIQUE(task_id, kind, value) で拒否。

### DU-10 db/connect.py

- `connect(path: str | Path) -> Connection` — 唯一の接続入口。PRAGMA foreign_keys=ON、
  row_factory 設定、config 保護トリガ（UPDATE/DELETE 拒否）の存在確認。未適用 DB は `FatalError`。

### DU-11 db/migrate.py

- `apply_all(conn, migrations_dir, clock: Clock, applied_by: str) -> list[Applied]` — 連番 SQL を順適用。
  適用ごとに checksum・applied_at（clock）・applied_by を schema_version へ INSERT。同 version 存在・checksum 不一致は停止（`FatalError`）。
- `verify(conn) -> None` — foreign_key_check／integrity_check／21 テーブル存在。
- migration 0001 = s0-contract §2 正準 DDL と等価（G-DDL-APPLY が JSON 正本側を常時検証）。

### DU-12 config/store.py

- `set(conn, key, value, value_type, reason, agent_id, clock) -> int` — 新行 INSERT＋supersedes 連鎖。
  同 key 同時刻は `GateRejected`。`get(conn, key, default=None)` は changed_at 最大行を型変換して返す。

### DU-13 registry/resolver.py

- `resolve(conn, service, operation) -> Route` — 宣言 JSON（レジストリ行）から優先順
  （mcp → api → browser → 有償）で有効経路を返す。切替はデータ変更のみ。該当なしは `FatalError`。

### DU-14 registry/secrets.py

- `get_credential(name, scope: Literal["test","prod"]) -> Secret` — Fernet 復号。`Secret` は
  `repr/str` が伏字の wrapper で、ログ・例外へ平文が乗らない。
- `check_endpoint(secret: Secret, endpoint_url) -> None` — scope×endpoint の不正組合せ
  （test→本番／prod→Docker・mock）を接続前に `FatalError` で拒否。
- `scan(targets: list[Path], conn) -> list[Finding]` — repo・SQLite 全行・構造化ログを対象に
  平文 credential パターン（正本は本モジュールの pattern 集合、DU-09 と共有）を走査（TC-047 の実装点）。

### DU-15 connectors/browser.py

- `launch(headed: bool, storage_state_path=None) -> BrowserSession` — Playwright 起動・
  storage_state 保存/再利用。起動失敗は `RetryableError`。
- `screenshot(session, url, out_path) -> Path` — URL 到達確認つき capture（file_hash は呼出し側で固定）。

### DU-16 connectors/playbooks.py

- `get(conn, service, operation, route_type) -> Playbook` ／
  `record_success(conn, playbook_id, agent_id, clock)`（last_success_at 更新）／
  `record_failure(conn, playbook_id, clock) -> None`（`consecutive_failures` を加算し `last_failure_at`
  を更新、連続失敗閾値 config で broken 降格 — 列は DDL 正本）。
  永続化はストア副層 `_store`（生 SQL はここだけ — 基本設計 §1 規約 3）。

### DU-17 connectors/wp.py

- `create_draft(conn, task_id, pair_pass: PairPass, html, idempotency_key, clock: Clock) -> DraftRef` ／
  `publish(conn, task_id, pair_pass: PairPass, draft_ref, approval_evidence_id, idempotency_key, clock: Clock) -> PublishedRef`
  — 下書きと公開は**別 idempotency key の別 `external_operations` 行**。各操作は
  prepared→sent→confirmed を各々コミットで遷移し（送信直後クラッシュの検出窓）、confirmed 後に
  operation_log／published_url 証跡を DU-09 経由で派生記録する。WP 側には決定的な meta key として
  idempotency key を保存し、再開時のリモート照合キーとする。
- `register_asset(conn, task_id, published: PublishedRef, clock: Clock) -> int` — 公開成功後に
  assets 行（wp_media_id・canonical_url・content_hash）をストア副層 `_assets_store` で INSERT し
  asset_id を返す。**published_url 証跡はこの asset_id を得てから記録する**（s0-contract §2.1 の
  整合列を先に成立させる — WF-WP-2 ステップ 6）。
  — 公開系は `PairPass` 必須（DU-05 のみが生成可）。実行前に同 key の `external_operations` を照合し、
  confirmed 済みなら再送せず結果補完。sent で照合不能なら unknown とし `FatalError`（→ escalated）。
  base URL は Docker WP allow-list（config）外なら接続前拒否。低レベル client は `_client`（非公開）。

### DU-18 connectors/approval.py

- `request(conn, task_id, binding: Binding, transport, clock: Clock) -> int` — 通知送出＋approvals 行 INSERT
  （ストア副層経由）。`Binding(subject, operation, at)` は frozen。
- `poll(conn, approval_id, transport, clock: Clock) -> Decision` — approved は
  `_record_decision`（統合 API）で **approval 証跡の INSERT と approvals.evidence_id 更新を
  単一 transaction** で行い、相互整合の中間状態を外部に見せない。binding 1 項目でも不一致の応答は無効。pending は親 loop_run を waiting へ（task は不進行）、
  rejected/expired は task failed（遷移は DU-01 経由）。

### DU-19 content/generate.py

- `generate(plan: PlanInput, workspace: Path, rng_seed: int) -> GeneratedSource` — テンプレート＋
  種固定で決定的生成（同一入力→同一 SHA-256）。外部 I/O なし（純関数＋ファイル書出しのみ）。

### DU-20 content/versioning.py

- `commit_workspace(workspace, repo, message) -> str` — commit 実行・hash 返却（40/64 桁検証）。
- `link(conn, task_id, repository: str, commit_hash, paths, clock: Clock) -> int` — commit_hash 証跡化
  （payload の repository/paths 必須キーを供給、DU-09 経由）。
- `restore(repo, commit_hash, dest) -> Path` — 審査記録からの成果物ソース復元（AC-54）。

### DU-21 measure/kpi.py

- `create_node(conn, node: KpiNodeInput) -> int` — 階層・媒体タグ・集計式の検証つき登録。
  metric_type は DU-07 `check_metric_type` を必ず通す（DB CHECK と二重）。
- `tree(conn, business_profile_id) -> list[KpiNode]` — 親子解決済みツリー。

### DU-22 measure/fetch.py

- `fetch(conn, task_id, route: Route, property_id, period, out_dir, clock: Clock) -> FetchResult` — DU-13 解決経路で取得
  （api 第一、browser フォールバック）。取得物は即 SHA-256 固定＋screenshot・operation_log 証跡。
  read-only 保証（書込み系 operation は組み立て時点で拒否）。

### DU-23 measure/parse.py

- `parse(raw: Path, schema: SourceSchema) -> ParseResult(rows, quarantined)` — schema/type 検証。
  壊れた行は隔離ファイルへ（正常行と分離、件数を証跡化）。
- `ingest(conn, rows, raw: Path, expected_hash: str, kpi_node_id, task_id, evidence_id, clock: Clock) -> int`
  — imported_at は clock から供給。
  — 投入前に raw の SHA-256 を再計算し expected_hash（固定済み証跡値）と不一致なら拒否。
  単一 transaction 投入、FK 不能は投入前拒否、途中失敗は全 rollback。

## 4. 横断規約（実装レベル）

- `Clock`／`Rng` は関数引数注入（既定実装は cli 層でのみ生成）。モジュール内での
  `datetime.now()`・`random` 直呼びは禁止。
- 型は全公開 API に注釈必須。dataclass は frozen を既定とする。
- 各 DU は対応する ⑥ の単体テスト（TC 割当＋UT）を test-first で先に赤にしてから実装する
  （CLAUDE.md の TDD 規律）。
