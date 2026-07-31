<!-- GENERATED FILE — 編集禁止。正本は docs/design/json/du-contracts.json。再生成 = python3 scripts/render_views.py -->

# 詳細設計 実装契約（DU contracts）v0.1

> status: **confirmed**（2026-08-01 PO 承認 — receipt 4d1ef4b6c613）。JSON 内容正本の生成ビュー（全層再降下 §7）
> 各 DU に公開 API 署名・DbC・例外・tx 境界・冪等性・競合制御・AC/TC/UT 対応を必須化
> （G-DU-API／G-DU-DBC／G-DU-ERROR／G-DU-DATA／G-API-UT）。

## DU-01 `kernel/state.py`（CMP-01）

### `def transition(conn: Connection, entity_type: str, entity_id: int, event: str, actor_agent_id: int | None, details: dict, clock: Clock) -> TransitionResult`

- **pre**: conn は db.connect() が返した接続（PRAGMA foreign_keys=ON・保護トリガ確認済み）／entity_type は 'loop_run' 又は 'task'、event は遷移表（transitions.json 同梱正本）の語彙／event に対応する guard が register_guard で配線済み（未登録の許可遷移は FatalError）／clock は注入済み（モジュール内での現在時刻直接取得は禁止）
- **post**: 許可時: guard 評価→状態 UPDATE→state_transitions（guard_result=passed）INSERT を BEGIN IMMEDIATE の単一 transaction でコミットし TransitionResult を返す／lower loop_run の終端遷移（completed/failed/escalated/cancelled）では DU-02 generate_tactical_learning_packet の INSERT を同一 transaction に内包する（completed=learning、それ以外=failure）／拒否時: 状態・retry_count・証跡は不変で、rejected 行のみ別 transaction で state_transitions に記録される／retry_count の増加は verify_fail（G4 通過時）のみ。通信再送は retry を消費しない
- **raises**: `GateRejected`（遷移表に無い (entity, 現状態, イベント) の組合せ・guard 不成立・終端状態からの遷移要求（TransitionRejected として正規化。DB 不変・rejected 行のみ記録））／`FatalError`（未登録 event の許可遷移（配線漏れの実行時 fail-close）・遷移表ロード不能・遷移表破損）／`RetryableError`（SQLITE_BUSY が busy_timeout（config.sqlite_busy_timeout_ms）を超過（retryable_failure へ正規化）） ／ **pure**: no

### `def register_guard(event: str, fn: Callable[[Connection, Row], GuardResult]) -> None`

- **pre**: fn は純関数 guard（DB read のみ・書込みなし・外部 I/O なし）／event は遷移表のイベント語彙に含まれる
- **post**: guard 登録簿に event→fn が登録され、以後の transition() が G1〜G5 の評価順序で呼び出す／登録は起動時配線に限る（実行中の差替えは行わない）
- **raises**: `FatalError`（同一 event への矛盾する二重登録・遷移表語彙外 event の登録（配線異常）） ／ **pure**: no

- **DTO・値オブジェクト**: TransitionResult(entity: str, from_state: str, to_state: str, transition_id: int) — frozen dataclass の遷移結果／GuardResult(ok: bool, reason: str | None) — guard 評価結果の値オブジェクト（reason は拒否時 details_json へ）
- **状態遷移**: loop_runs: s0-contract §3.1 の全行（start/wait/resume/complete/retryable_failure/retry_exhausted/non_retryable_failure/fatal_failure/cancel）の唯一の実行主体／tasks: s0-contract §3.2 の全行（claim/submit_for_verification/verify_pass/verify_fail/verify_fail_exhausted/non_retryable_failure/escalate）の唯一の実行主体／終端状態（done/failed/escalated/completed/cancelled）からの遷移要求は常に拒否（G0）
- **DB read**: loop_runs／tasks／sprints／brand_plans／strategic_briefs／agents／agent_executions／workflows／evidence／config ／ **DB write**: loop_runs／tasks／state_transitions
- **tx 境界**: 1 状態遷移 = 1 transaction。BEGIN IMMEDIATE で書込みロックを先取し、guard 判定→状態 UPDATE→state_transitions INSERT→（lower 終端のみ TLP INSERT）→COMMIT。拒否の rejected 行は別 transaction。遷移 transaction に外部 I/O を入れない
- **pure／副作用端点**: 遷移表照合・guard 関数は純関数部（Connection read のみ）。副作用端点は transition() の DB 書込みに一元化。時刻は Clock 注入のみ
- **冪等性**: 同一イベントの二重発火は先行コミットで from_state が変わり G0 で拒否（rejected 記録が残る）— 事故にならない。拒否は何度実行しても DB 不変 ／ **retry/resume**: クラッシュ時は transaction ごと消え中間状態が残らない（申し送りなし — BR-A1）。再開はプロセス再起動後に loop_runs/tasks の DB 現在状態からのみ判断（s0-contract §3.3。再開分岐の実行は DU-02 resume）
- **競合制御**: BEGIN IMMEDIATE による遷移 tx の直列化＋WAL＋busy_timeout（超過は retryable_failure）。lease・row_version の整合は G2 で検査し、check-then-act 競合を単一ロック区間で消す（state-machine-design §4）
- **ログ・証跡**: 許可・拒否とも state_transitions（from/event/to/guard_result/details_json/created_at/created_by_agent_id）へ append-only 記録。構造化ログ（FN-704 二重化）は entity/event/guard_result/duration のみで本文・credential を含めない
- **依存 API**: DU-10: connect()／DU-02: validate_strategic_brief()（lower start ガード G3 の実体 — SCM-03）／DU-02: generate_tactical_learning_packet()（lower 終端遷移と同一 transaction）／DU-08: check_complete()（done/complete の G5 guard）／DU-12: get()（retry_limit・approval_retry_limit・sqlite_busy_timeout_ms）
- **trace**: AC = AC-11-1 AC-11-2 AC-11-3 AC-11-4 AC-13-1 AC-13-2 AC-13-3 AC-13-4 AC-13-5 AC-13-6 AC-16-1 AC-16-2 AC-16-3 AC-16-4 AC-16-5 AC-16-6 AC-SR-02 AC-SR-07-1 AC-SR-07-2 ／ TC = STC-I-03 TCC-11-1 TCC-11-2 TCC-11-3 TCC-11-4 TCC-13-1 TCC-13-2 TCC-13-3 TCC-13-4 TCC-13-5 TCC-13-6 TCC-16-1 TCC-16-2 TCC-16-3 TCC-16-4 TCC-16-5 TCC-16-6 TCC-CONFLICT-1 TCC-KILL-1 TCC-SR-02 TCC-SR-07-1 TCC-SR-07-2 ／ UT = test_kernel_state.py::test_transition_allowed_commits_state_and_passed_log test_kernel_state.py::test_transition_undefined_combination_rejected_db_unchanged test_kernel_state.py::test_transition_terminal_state_request_rejected test_kernel_state.py::test_transition_rejected_records_rejected_row_only test_kernel_state.py::test_transition_crash_mid_tx_leaves_no_partial_state test_kernel_state.py::test_transition_verify_fail_retry_boundary_switches_to_exhausted test_kernel_state.py::test_transition_double_fire_rejected_by_stale_from_state test_kernel_state.py::test_transition_begin_immediate_serializes_concurrent_write test_kernel_state.py::test_register_guard_wires_event_guard test_kernel_state.py::test_register_guard_unregistered_event_allowed_transition_fatal test_kernel_state.py::test_lower_start_without_valid_brief_rejected test_kernel_state.py::test_lower_terminal_transition_includes_tlp_same_tx ／ 機能別設計 = features/state-machine.md、features/strategic-brief.md、features/tlp.md

## DU-02 `kernel/orchestrator.py`（CMP-02）

### `def issue_task(conn: Connection, loop_run_id: int, step: WorkflowStep, clock: Clock) -> int`

- **pre**: 対象 loop_run が running（親 loop の有効性は guard 済み）／workflow_id・author_agent_id・verifier_agent_id・expected_output_kind を組立時に非 NULL で確定できる（割当は DU-03 assign）／T-PUB は pair_plan_quality（status=passed）成立済みのみ発行可
- **post**: 同一 (loop_run_id, step_key) に非終端の既存 task があればその id を返す（新規発行しない — 冪等）／なければ attempt = 終端行数 + 1、idempotency_key = f"{loop_run_id}:{step.key}:{attempt}" で INSERT（採番と発行は単一 transaction）／UNIQUE (loop_run_id, step_key, attempt) 衝突時は再読して既存 id を返す（並行発行の最終防衛）
- **raises**: `TaskIssuanceRejected`（workflow 不在・active agent 不足・T-PUB のペア未成立での発行要求（GateRejected 系 — tasks 行を作らない））／`SelfReviewRejected`（principal 同一の author/verifier 組しか構成できない（DB CHECK と二重防御）） ／ **pure**: no

### `def claim(conn: Connection, task_id: int, execution_id: int, clock: Clock) -> None`

- **pre**: task は pending 又は lease 失効済み in_progress、親 loop_run は running／execution は agent_executions に実在し complex FK で principal 一致が強制済み
- **post**: lease_owner_execution_id・lease_expires_at（config.lease_ttl_sec）・heartbeat_at を row_version 楽観ロックで更新（row_version +1）／状態遷移（pending→in_progress の claim イベント）は DU-01 transition() 経由
- **raises**: `GateRejected`（execution が task の author_agent_id に属さない（verifier・無関係 agent）・lease 失効前の他 execution からの claim・row_version 不一致（0 行更新）） ／ **pure**: no

### `def run_microloop(conn: Connection, task_id: int, executor: Executor, verifier: Verifier, retry_limit_key: str = "retry_limit") -> MicroloopResult`

- **pre**: task は in_progress で lease を保持、executor/verifier は principal の異なる agent に帰属／retry_limit_key は config に解決可能
- **post**: submit→verify を反復し、FAIL ごとに verify_fail 遷移（retry_count 消費）を DU-01 経由で適用／retry_count + 1 >= config.retry_limit 到達時は verify_fail_exhausted で escalated とし MicroloopResult に終端理由を返す
- **raises**: `GateRejected`（verifier が author と同一 principal・差戻し理由/verifier 証跡なしの verify_fail 要求）／`RetryableError`（executor 実行の一時失敗（retryable_failure へ還元）） ／ **pure**: no

### `def resume(conn: Connection, entity_type: str, entity_id: int, clock: Clock) -> ResumeAction`

- **pre**: entity は非終端状態（終端は再開対象外 — 新 run/task の明示発行のみ）／判断根拠は DB 行のみ（プロセス内メモリ・「成功したはず」の推測は禁止）
- **post**: s0-contract §3.3 の全行を実装: pending=再 claim 可／in_progress（外部操作前）=workspace・入力・既存証跡再読込／in_progress（外部操作中後）=external_operations.status で分岐（prepared=同一 key 再送可、sent=リモート照合→confirmed 化、照合不能=unknown で escalate・再送禁止）／verifying=既存 PASS/FAIL 再採用（retry 二重加算なし）／waiting=充足再照合／ResumeAction は分岐結果と根拠行 id を保持し、遷移は DU-01 経由でのみ実行される
- **raises**: `FatalError`（sent のままリモート照合不能（OperationUnverifiable — unknown 化し escalate。再送しない）） ／ **pure**: no

### `def issue_strategic_brief(conn: Connection, brief: StrategicBriefDraft, clock: Clock) -> int`

- **pre**: brief は strategic_brief schema（json/strategy/ 正本）に適合／呼出しは上流ループ改善工程・S0 シードコマンドのみ（下流実行経路・コネクタ層へ非公開 — SR-09）
- **post**: 正準化 JSON（キー昇順・区切り (",", ":")・UTF-8。digest/status/created_at を除外）の SHA-256 を digest として決定的に計算し INSERT（同一入力→同一 digest — STC-I-04）／created_at は clock から供給（digest 計算からは除外）
- **raises**: `BriefSchemaRejected`（brief draft の schema 不適合（brief を発行しない）） ／ **pure**: no

### `def supersede_strategic_brief(conn: Connection, old_brief_id: int, new_draft: StrategicBriefDraft, clock: Clock) -> int`

- **pre**: old_brief_id は status=active の既存版／new_draft は schema 適合
- **post**: 新版 INSERT（supersedes_id=old_brief_id・version+1・digest 決定計算）と旧版 status=superseded 化を単一 transaction で実行（新旧とも active の中間状態を残さない）
- **raises**: `GateRejected`（superseded/retired/期限切れ版への supersede 要求等の不正連鎖）／`BriefSchemaRejected`（new_draft の schema 不適合） ／ **pure**: no

### `def validate_strategic_brief(conn: Connection, brief_id: int, held_digest: str, clock: Clock) -> ValidBrief`

- **pre**: held_digest は 64 桁 SHA-256（呼出し側 run が保持する digest）
- **post**: status=active・digest 一致・有効期間内（valid_from <= now < valid_until 又は valid_until NULL）をすべて満たす場合のみ ValidBrief を返す（lower run start ガード G3 の実体 — STC-I-03）／検証は read-only で DB を変更しない
- **raises**: `GateRejected`（brief 不在・status 非 active・digest 不一致・有効期間外（下位 loop_run は開始されない — fail-close）） ／ **pure**: no

### `def generate_tactical_learning_packet(conn: Connection, loop_run_id: int, packet: TlpDraft, clock: Clock) -> int`

- **pre**: 対象 run は loop_kind='lower' かつ終端状態（DU-01 の終端遷移と同一 transaction で呼ばれる）／packet は TLP schema 適合、packet_kind 別必須フィールド完備（learning: causal_interpretation/hypothesis_result/assessment_reason、failure: failure_fact/reproduction_conditions/recovery_conditions かつ causal_interpretation なし）
- **post**: run 保持の strategic_brief_id/digest を写して INSERT（run/brief/digest 三者一致 — DDL の integrity トリガが最終防衛）／completed は packet_kind='learning'、failed/escalated/cancelled は 'failure'（1 run 1 packet — UNIQUE）
- **raises**: `GateRejected`（非 lower run・非終端 run・brief/digest 不整合・既存 packet ありへの生成要求）／`SchemaVerificationFailed`（TlpDraft の schema 不適合・kind 別必須フィールド欠落） ／ **pure**: no

### `def get_tactical_learning_packet(conn: Connection, loop_run_id: int) -> TlpRecord | None`

- **pre**: 呼出しは上流（WF-STRAT-REVISE）が読む唯一の還流読取り口
- **post**: 該当行があれば TlpRecord、なければ None（read-only・DB 不変）
- **raises**: なし ／ **pure**: yes

- **DTO・値オブジェクト**: WorkflowStep(key: str, task_type: str, expected_output_kind: str) — WF ステップ定義の値オブジェクト／MicroloopResult(task_id: int, outcome: str, retry_count: int) — frozen dataclass のマイクロループ結果／ResumeAction(entity: str, action: str, basis_rows: tuple) — 再開分岐の決定（根拠は DB 行 id のみ）／StrategicBriefDraft(brief_key: str, payload: dict) — schema 検証前の brief 起草値／ValidBrief(brief_id: int, digest: str, valid_until: str | None) — 検証済み brief の値オブジェクト（validate のみが生成）／TlpDraft(packet_kind: str, payload: dict) — TLP 起草値（観測/解釈/判定の分離フィールド）／TlpRecord(id: int, loop_run_id: int, packet_kind: str, payload: dict) — 還流読取り結果
- **状態遷移**: 直接の状態 UPDATE は行わない — claim/submit/verify_*/wait/resume/終端イベントはすべて DU-01 transition() 経由で発火（イベント発火元: state-machine-design §3）／lease 列（lease_owner_execution_id/lease_expires_at/heartbeat_at/row_version）の更新は claim 経路のみ
- **DB read**: loop_runs／tasks／agents／agent_executions／workflows／strategic_briefs／tactical_learning_packets／external_operations／evidence／sprints／config ／ **DB write**: tasks／loop_runs／agent_executions／strategic_briefs／tactical_learning_packets
- **tx 境界**: issue_task = 採番＋INSERT の単一 transaction／claim = lease 更新の単一 transaction（遷移は DU-01 の tx）／supersede = 新版 INSERT＋旧版 superseded の単一 transaction／generate_tactical_learning_packet = DU-01 の下位終端遷移 transaction に参加（独自 BEGIN しない）／resume は read-only 判断＋各分岐先の所有 tx
- **pure／副作用端点**: digest 計算・idempotency_key 組立・再開分岐判断・schema 検証は純関数部。副作用端点は tasks/strategic_briefs/tactical_learning_packets への INSERT と lease UPDATE のみ。Clock/Rng は注入（NFR-7 の書込み間隔は Rng 注入）
- **冪等性**: issue_task は決定的 idempotency_key と非終端再利用で冪等（クラッシュ後再実行は既存 id 返却）。brief digest は同一入力から常に同一値で再計算可能。TLP は UNIQUE(loop_run_id) で 1 run 1 packet。claim の二重要求は row_version/lease で拒否 ／ **retry/resume**: resume() が s0-contract §3.3 の正本実装: DB 行のみを根拠に pending/in_progress/verifying/waiting を分岐し、sent 照合不能は unknown 化して再送せず escalate（最危険 kill point の再送禁止）。verifying の既存 PASS/FAIL 再採用で retry 二重加算なし
- **競合制御**: claim は row_version 楽観ロック（UPDATE 条件一致・0 行更新は GateRejected）＋ lease 排他（失効前の他 execution 拒否・失効後は author agent の新 execution のみ）。issue_task の並行発行は UNIQUE 制約→再読で収束。書込みは kernel 単一 writer（BR-I7）
- **ログ・証跡**: タスク発行・claim・再開分岐を構造化ログへ（task_id/step_key/attempt/execution_id — 本文なし）。brief 発行・supersede・TLP 生成は strategic_briefs/tactical_learning_packets の append-only 行自体が証跡。ステップ出力の証跡化は DU-09 record() 経由
- **依存 API**: DU-01: transition()（全状態変更）／DU-01: register_guard()（start/claim/complete ガードの配線）／DU-03: assign()（author/verifier 割当）／DU-04: load(), run_step()（WF 定義と実行）／DU-08: check_complete()（done 前の証跡完備）／DU-09: record()（ステップ出力の証跡化）／DU-10: connect()／DU-12: get()（retry_limit・lease_ttl_sec・approval_retry_limit）
- **trace**: AC = AC-12-1 AC-12-2 AC-12-3 AC-12-4 AC-27-1 AC-27-2 AC-27-3 AC-27-4 AC-27-5 AC-SR-01 AC-SR-02 AC-SR-03 AC-SR-04 AC-SR-06 AC-SR-06-1 AC-SR-06-2 AC-SR-06-3 AC-SR-06-4 AC-SR-06-5 AC-SR-07-1 AC-SR-07-2 AC-SR-08-1 AC-SR-08-2 AC-SR-08-3 AC-SR-09-1 AC-SR-09-2 AC-SR-09-3 AC-SR-09-4 AC-SR-15-1 AC-SR-15-2 AC-SR-15-3 AC-SR-15-4 AC-SR-15-5 AC-SR-15-6 ／ TC = STC-I-03 STC-I-04 STC-I-05 STC-I-06 TCC-12-1 TCC-12-2 TCC-12-3 TCC-12-4 TCC-27-1 TCC-27-2 TCC-27-3 TCC-27-4 TCC-27-5 TCC-CONFLICT-2 TCC-KILL-2 TCC-SR-01 TCC-SR-02 TCC-SR-03 TCC-SR-04 TCC-SR-06 TCC-SR-06-1 TCC-SR-06-2 TCC-SR-06-3 TCC-SR-06-4 TCC-SR-06-5 TCC-SR-07-1 TCC-SR-07-2 TCC-SR-08-1 TCC-SR-08-2 TCC-SR-08-3 TCC-SR-09-1 TCC-SR-09-2 TCC-SR-09-3 TCC-SR-09-4 TCC-SR-15-1 TCC-SR-15-2 TCC-SR-15-3 TCC-SR-15-4 TCC-SR-15-5 TCC-SR-15-6 ／ UT = test_kernel_orchestrator.py::test_issue_task_inserts_with_deterministic_idempotency_key test_kernel_orchestrator.py::test_issue_task_reuses_nonterminal_existing_task test_kernel_orchestrator.py::test_issue_task_unique_collision_rereads_existing test_kernel_orchestrator.py::test_issue_task_attempt_increments_after_terminal_rows test_kernel_orchestrator.py::test_issue_task_pair_not_established_tpub_rejected test_kernel_orchestrator.py::test_claim_by_author_execution_acquires_lease test_kernel_orchestrator.py::test_claim_by_verifier_execution_rejected test_kernel_orchestrator.py::test_claim_by_unrelated_agent_execution_rejected test_kernel_orchestrator.py::test_claim_before_lease_expiry_by_other_execution_rejected test_kernel_orchestrator.py::test_claim_after_lease_expiry_author_new_execution_only test_kernel_orchestrator.py::test_claim_row_version_mismatch_rejected test_kernel_orchestrator.py::test_run_microloop_verify_fail_consumes_retry_until_escalated test_kernel_orchestrator.py::test_resume_pending_reclaimable test_kernel_orchestrator.py::test_resume_in_progress_before_external_reloads_state test_kernel_orchestrator.py::test_resume_sent_remote_match_confirms_without_resend test_kernel_orchestrator.py::test_resume_sent_unverifiable_unknown_escalates test_kernel_orchestrator.py::test_resume_verifying_reuses_existing_verdict_no_double_count test_kernel_orchestrator.py::test_resume_waiting_rechecks_satisfaction test_kernel_orchestrator.py::test_issue_strategic_brief_digest_deterministic_for_equivalent_json test_kernel_orchestrator.py::test_issue_strategic_brief_schema_violation_rejected test_kernel_orchestrator.py::test_supersede_strategic_brief_single_tx_new_active_old_superseded test_kernel_orchestrator.py::test_validate_strategic_brief_active_digest_period_passes test_kernel_orchestrator.py::test_validate_strategic_brief_invalid_status_digest_period_rejected test_kernel_orchestrator.py::test_generate_tlp_kind_branches_learning_and_failure test_kernel_orchestrator.py::test_generate_tlp_non_lower_or_nonterminal_rejected test_kernel_orchestrator.py::test_generate_tlp_brief_digest_mismatch_rejected test_kernel_orchestrator.py::test_generate_tlp_atomic_with_terminal_transition test_kernel_orchestrator.py::test_get_tactical_learning_packet_returns_record_or_none test_kernel_orchestrator.py::test_downstream_paths_cannot_write_strategic_briefs ／ 機能別設計 = features/state-machine.md、features/strategic-brief.md、features/tlp.md、features/external-operations.md

## DU-03 `kernel/assigner.py`（CMP-02）

### `def assign(conn: Connection, author_role: str, verifier_role: str) -> Assignment`

- **pre**: agents に status=active の行が存在する（役割該当）／conn は db.connect() 由来
- **post**: active かつ principal の異なる agent の組（agents.principal 比較）を返す／T-REVIEW の verifier は critic 以外を割り当てる（tasks.verifier_agent_id は全タスク必須 — NULL の三値論理に委ねない）／read-only（tasks への書込みは呼出し側 issue_task）
- **raises**: `SelfReviewRejected`（同一 principal の agent しか存在しない（ID 違いだけの自己審査を封じる — tasks の CHECK と二重防御））／`TaskIssuanceRejected`（役割該当の active agent が不足し組を構成できない） ／ **pure**: no

- **DTO・値オブジェクト**: Assignment(author_agent_id: int, verifier_agent_id: int) — principal の異なる検証済み割当の値オブジェクト（frozen）
- **状態遷移**: なし
- **DB read**: agents ／ **DB write**: なし
- **tx 境界**: なし（読み取りのみ/pure）— 割当結果の tasks への反映は DU-02 issue_task の transaction
- **pure／副作用端点**: principal 比較・役割フィルタは純関数部。DB read のみで副作用なし（書込み端点を持たない）
- **冪等性**: 同一 agents 状態からは同一の割当候補集合（決定的選択規則）。再実行は安全 ／ **retry/resume**: stateless。クラッシュ後の再実行は agents 現在行からの再判定のみ（申し送りなし）
- **競合制御**: 競合なし（read-only）。agents の同時変更は issue_task 側の transaction 内再検証と DB CHECK（author != verifier）が防衛
- **ログ・証跡**: 割当結果は tasks 行（author_agent_id/verifier_agent_id）として記録。拒否は例外＋発行元の構造化ログ（principal は記録するが credential は含めない）
- **依存 API**: DU-10: connect()
- **trace**: AC = AC-27-1 AC-27-2 AC-27-3 AC-27-4 AC-27-5 ／ TC = TCC-27-1 TCC-27-2 TCC-27-3 TCC-27-4 TCC-27-5 ／ UT = test_kernel_assigner.py::test_assign_active_different_principal_pair test_kernel_assigner.py::test_assign_same_agent_pair_rejected test_kernel_assigner.py::test_assign_distinct_agents_same_principal_rejected test_kernel_assigner.py::test_assign_review_verifier_excludes_critic test_kernel_assigner.py::test_assign_inactive_agents_excluded ／ 機能別設計 = features/state-machine.md

## DU-04 `kernel/workflow.py`（CMP-02）

### `def load(conn: Connection, workflow_key: str, version: int | None = None) -> WorkflowDef`

- **pre**: workflows に該当 workflow_key（version 指定時はその版、未指定時は active 最新版）が存在
- **post**: definition_json / required_evidence_json を schema 検証して WorkflowDef を返す（read-only）／required_evidence_json の kind は evidence enum 内であることを検証する
- **raises**: `FatalError`（定義行不在・definition_json/required_evidence_json の schema 破損（壊れた定義で実行を開始しない — fail-close）） ／ **pure**: no

### `def run_step(conn: Connection, task_id: int, step: WorkflowStep, ctx: StepContext) -> StepOutcome`

- **pre**: task は in_progress で lease 保持中（claim 済み）／外部書込みステップは操作単位の idempotency key を保持し、実行前に external_operations の同 key を照合済み
- **post**: ステップ出力の証跡保存は DU-09 record() 経由のみ（evidence 直 INSERT しない）／外部操作は external_operations を prepared→sent→confirmed の順で各々コミットし、confirmed 後に operation_log 証跡→状態遷移の順を固定（NFR-3）／失敗は RetryableError/FatalError/GateRejected の 3 系へ正規化して返し、遷移判断は呼出し側（DU-02）に委ねる — 勝手に done へ進めない
- **raises**: `RetryableError`（ステップ実行の一時失敗（コネクタ境界 ConnectorError の retryable kind を含む））／`FatalError`（sent のまま照合不能（unknown 化 — 再送禁止・escalate）・回復不能な実行環境異常）／`GateRejected`（ゲート不通過のステップ前提違反（状態・DB 不変で拒否）） ／ **pure**: no

- **DTO・値オブジェクト**: WorkflowDef(workflow_id: int, workflow_key: str, version: int, steps: tuple, required_evidence: tuple) — schema 検証済み WF 定義（frozen）／StepContext(loop_run_id: int, workspace: Path, clock: Clock, rng: Rng) — ステップ実行文脈（Clock/Rng 注入の運搬体）／StepOutcome(step_key: str, status: str, evidence_ids: tuple) — ステップ実行結果（遷移はしない）
- **状態遷移**: 状態遷移は実行しない（StepOutcome を返すのみ — 遷移判断は DU-02、実行は DU-01）／external_operations.status の prepared→sent→confirmed/rejected/unknown 遷移（操作状態機械 — 業務状態機械とは別）は本 DU が所有（db-design §2: CMP-02 WF 実行器）
- **DB read**: workflows／tasks／external_operations／evidence ／ **DB write**: external_operations
- **tx 境界**: external_operations の prepared・sent・confirmed/rejected/unknown を各々単独コミット（送信直後クラッシュの検出窓 — s0-contract §1）。外部 I/O は業務遷移 transaction の外。証跡 INSERT は DU-09 の transaction
- **pure／副作用端点**: 定義 schema 検証・required kind 検証は純関数部。副作用端点は external_operations の状態コミットとコネクタ呼出し（コネクタ自体は業務状態を書かない）。Clock/Rng は StepContext 経由で注入
- **冪等性**: 外部書込みは操作単位 idempotency key を必須とし、実行前に同 key の external_operations を照合（confirmed 済みは再送せず結果補完）。下書きと公開は別 idempotency key の別行。1 外部操作 = 1 行 ／ **retry/resume**: 再開時は external_operations.status を先に照合: prepared=同一 key で再送可、sent=リモート照合成功で confirmed 化し証跡補完、照合不能=unknown で escalate・再送禁止（最危険 kill point で再送 0 回 — s0-contract §8）。分岐実行は DU-02 resume と協働
- **競合制御**: idempotency_key の UNIQUE で並行実行の二重行を拒否。操作状態の前進のみ許可（confirmed からの巻き戻し不可）。単一プロセス・kernel 単一 writer 前提（BR-I7）
- **ログ・証跡**: 外部操作ごとに request_hash・external_operation_id・response_hash を external_operations に、confirmed 後に operation_log 証跡（service/operation/external_operation_id/request_fingerprint/result — secret/本文禁止）を DU-09 経由で派生記録
- **依存 API**: DU-09: record()（operation_log・ステップ出力の証跡化）／DU-10: connect()／DU-12: get()（レート間隔・操作上限の config 値）
- **trace**: AC = AC-12-1 AC-12-2 AC-12-3 AC-12-4 AC-42-1 AC-42-2 AC-42-3 ／ TC = TCC-12-1 TCC-12-2 TCC-12-3 TCC-12-4 TCC-42-1 TCC-42-2 TCC-42-3 TCC-RESUME-1 ／ UT = test_kernel_workflow.py::test_load_active_definition_schema_validated test_kernel_workflow.py::test_load_broken_definition_raises_fatal test_kernel_workflow.py::test_load_version_pinned_lookup test_kernel_workflow.py::test_run_step_output_saved_via_evidence_api test_kernel_workflow.py::test_run_step_failure_normalized_to_three_kinds test_kernel_workflow.py::test_run_step_never_transitions_task_to_done test_kernel_workflow.py::test_external_operation_prepared_sent_confirmed_each_committed test_kernel_workflow.py::test_external_operation_sent_crash_resume_no_resend test_kernel_workflow.py::test_external_operation_unverifiable_marked_unknown_escalates test_kernel_workflow.py::test_draft_and_publish_use_distinct_idempotency_keys ／ 機能別設計 = features/external-operations.md、features/campaign.md

## DU-05 `gates/pair.py`（CMP-03）

### `def establish(conn: Connection, plan_id: int, review_task_id: int, review_evidence_id: int, clock: Clock) -> PairPass`

- **pre**: review_evidence_id は kind=review_pass・result=PASS の証跡／review_pass 証跡の commit_hash が制作側 commit_hash 証跡と一致／reviewer は author と別 principal（証跡側検証済み — DU-09）
- **post**: hash 一致時のみ pair_plan_quality(status=passed) を INSERT し PairPass を返す／PairPass は内部 sentinel token 付きで構築される（生成関数は establish/require_pair のみ）
- **raises**: `CommitHashMismatch`（review_pass の hash と制作 commit hash の不一致（pair 不成立・公開拒否））／`GateRejected`（review_pass 証跡不在・result 非 PASS・重複成立要求（UNIQUE(plan_id, review_evidence_id)）） ／ **pure**: no

### `def revoke_if_changed(conn: Connection, plan_id: int, current_commit_hash: str) -> bool`

- **pre**: plan_id に成立済み pair（passed）が存在し得る状態
- **post**: 企画又は commit の変更検知時に該当 pair を status=revoked へ更新し True を返す（変更なしは False・DB 不変）／revoked 後の公開系要求は require_pair が拒否（再審査を要求）
- **raises**: なし ／ **pure**: no

### `def require_pair(conn: Connection, plan_id: int) -> PairPass`

- **pre**: conn は db.connect() 由来
- **post**: status=passed の pair 行が存在する場合のみ PairPass を返す（read-only）
- **raises**: `PairNotEstablished`（passed 行が存在しない・revoked のみ（GateRejected 系 — 公開系はコネクタに到達しない）） ／ **pure**: no

- **DTO・値オブジェクト**: PairPass(pair_id: int, plan_id: int, verified_at: str) — 検証済みペア通過の型強制。`__init__` はモジュール内部 sentinel token を要求（不一致は FatalError）し、frozen dataclass ＋ token で構築独占を実行時にも強制
- **状態遷移**: pair_plan_quality.status の passed／revoked 遷移（業務状態機械とは別の所掌状態 — 状態所有者は CMP-03）
- **DB read**: pair_plan_quality／evidence／action_plans／tasks ／ **DB write**: pair_plan_quality
- **tx 境界**: establish の INSERT・revoke_if_changed の UPDATE は各単独 transaction。遷移 guard として評価される場合は DU-01 の遷移 transaction に参加
- **pure／副作用端点**: hash 一致判定・PASS 検証は純関数部。副作用端点は pair_plan_quality の INSERT/UPDATE のみ。PairPass 偽造検知（sentinel 不一致）は FatalError で即停止
- **冪等性**: 同一 (plan_id, review_evidence_id) の再成立要求は UNIQUE で拒否（冪等拒否）。require_pair は read-only で何度でも安全。revoke は変更検知時のみ 1 回作用 ／ **retry/resume**: stateless 判定＋DB 行のみが状態。クラッシュ後は pair_plan_quality 現在行からの再判定（再実行安全）。revoked 後の復帰は再審査→再 establish のみ
- **競合制御**: 成立/失効は単独 transaction の行更新で直列化（kernel 単一 writer）。同時 establish は UNIQUE 制約が防衛。判定はコネクタ呼出し前に完了（拒否時は外部到達 0 回）
- **ログ・証跡**: 成立 = pair_plan_quality 行（review_task_id/review_evidence_id で審査に FK 接続）。拒否は 構造化ログの拒否行／例外＋構造化ログ（plan_id・事由コードのみ）
- **依存 API**: DU-09: for_task(), exists()（review_pass/commit_hash 証跡の照合）／DU-10: connect()
- **trace**: AC = AC-21-1 AC-21-2 AC-21-3 AC-21-4 AC-21-5 ／ TC = TCC-21-1 TCC-21-2 TCC-21-3 TCC-21-4 TCC-21-5 ／ UT = test_gates_pair.py::test_establish_hash_match_creates_passed_pair_and_pairpass test_gates_pair.py::test_establish_hash_mismatch_rejected_no_row test_gates_pair.py::test_establish_duplicate_pair_rejected test_gates_pair.py::test_require_pair_missing_or_revoked_rejected test_gates_pair.py::test_require_pair_passed_returns_pairpass test_gates_pair.py::test_revoke_if_changed_revokes_on_commit_change test_gates_pair.py::test_pairpass_forgery_without_sentinel_raises_fatal ／ 機能別設計 = features/campaign.md、features/evidence.md

## DU-06 `gates/publish.py`（CMP-03）

### `def check_publishable(conn: Connection, plan_id: int, commit_hash: str) -> PairPass`

- **pre**: commit_hash は 40 又は 64 桁の hash（形式検証済み入力）／呼出しは WP コネクタ到達前の公開前ゲートとして行われる（WF-WP-2 ステップ 1）
- **post**: require_pair（passed 存在）＋ pair の review_pass hash と commit_hash の一致 ＋ 公開前必須証跡（review_pass/commit_hash）完備をまとめて検証し、全成立時のみ PairPass を返す／拒否時はコネクタ呼出しに到達しない（WP API を呼ばない — 外部送信 0 回）
- **raises**: `PairNotEstablished`（成立 pair（passed）が存在しない公開要求（T-PUB を non_retryable_failure → failed））／`CommitHashMismatch`（pair 成立時の hash と公開対象 commit_hash の不一致（版ずれ公開の拒否））／`EvidenceIncomplete`（公開前必須証跡（review_pass/commit_hash）の欠落・kind 規則違反） ／ **pure**: no

- **DTO・値オブジェクト**: なし
- **状態遷移**: なし
- **DB read**: pair_plan_quality／evidence／action_plans ／ **DB write**: なし
- **tx 境界**: なし（読み取りのみ/pure）— 判定のみで書込みを持たない。拒否に伴う failed 遷移は呼出し側が DU-01 経由で実行
- **pure／副作用端点**: 全体が read-only 判定（stateless ゲート）。副作用なし・PairPass の返却は DU-05 の構築独占経路を経由
- **冪等性**: read-only 判定のため何度実行しても DB 不変・同一入力同一判定（決定的） ／ **retry/resume**: stateless で復旧不要。再実行は DB 現在状態（pair・証跡）からの再判定のみ
- **競合制御**: 競合なし（read-only）。判定と公開実行の間の pair 失効は、コネクタ側の PairPass 必須引数＋遷移 guard の再検証で防衛（二重ゲート）
- **ログ・証跡**: 拒否は 構造化ログの拒否行（plan_id・事由コード）と state_transitions rejected 行（遷移 guard 経由時）。成立はログのみ（証跡は既存の pair/evidence 行）
- **依存 API**: DU-05: require_pair()／DU-09: for_task(), exists()（証跡完備の照合）／DU-10: connect()
- **trace**: AC = AC-21-1 AC-21-2 AC-21-3 AC-21-4 AC-21-5 AC-44-1 AC-44-2 AC-44-3 ／ TC = TCC-21-1 TCC-21-2 TCC-21-3 TCC-21-4 TCC-21-5 TCC-44-1 TCC-44-2 TCC-44-3 ／ UT = test_gates_publish.py::test_check_publishable_all_conditions_returns_pairpass test_gates_publish.py::test_check_publishable_without_pair_rejected test_gates_publish.py::test_check_publishable_hash_mismatch_rejected test_gates_publish.py::test_check_publishable_missing_evidence_rejected test_gates_publish.py::test_check_publishable_rejection_precedes_connector_call ／ 機能別設計 = features/campaign.md

## DU-07 `gates/zero_ad.py`（CMP-03）

### `def check_metric_type(metric_type: str) -> None`

- **pre**: metric_type は非空文字列
- **post**: deny 型（cac/roas/ad_spend — 有料指標）でなければ何もせず返る（kpi_nodes の CHECK と二重防御）／判定は大文字小文字を正規化して行う（表記揺れで素通りさせない）
- **raises**: `PaidMetricRejected`（有料指標型（cac/roas/ad_spend 及びその表記揺れ）の登録要求（GateRejected 系 — 登録拒否）） ／ **pure**: yes

### `def check_domain(url_or_domain: str, denylist: list[str]) -> None`

- **pre**: denylist は config（広告ドメイン denylist）から呼出し側が取得済み／url_or_domain は URL 又はドメイン文字列
- **post**: denylist 非該当かつ判定可能な場合のみ返る。denylist/allowlist が取得不能・未設定の場合は fail-close（通さない — deny-by-default）
- **raises**: `UrlDenied`（広告ドメイン denylist 該当・allowlist 未設定状態での遷移要求・判定不能 URL（fail-close）） ／ **pure**: yes

- **DTO・値オブジェクト**: なし
- **状態遷移**: なし
- **DB read**: なし ／ **DB write**: なし
- **tx 境界**: なし（読み取りのみ/pure）— DB 接続を持たない純関数ゲート
- **pure／副作用端点**: 両 API とも純関数（引数のみで判定・副作用なし・テスト注入可能）。denylist の取得は呼出し側の責務（config 経由）
- **冪等性**: 純関数のため同一入力同一判定。何度実行しても安全 ／ **retry/resume**: stateless・復旧対象なし。再実行は同一判定の再取得のみ
- **競合制御**: 競合なし（純関数）。DB CHECK（kpi_nodes.metric_type NOT IN ('cac','roas','ad_spend')）が並行経路の最終防衛
- **ログ・証跡**: 拒否は例外＋構造化ログの拒否行（呼出し側が記録 — metric_type/URL と事由コードのみ、credential なし）
- **依存 API**: なし
- **trace**: AC = AC-23-1 AC-23-2 AC-23-3 AC-23-4 AC-23-5 ／ TC = TCC-23-1 TCC-23-2 TCC-23-3 TCC-23-4 TCC-23-5 ／ UT = test_gates_zero_ad.py::test_check_metric_type_free_metric_passes test_gates_zero_ad.py::test_check_metric_type_deny_types_rejected test_gates_zero_ad.py::test_check_metric_type_case_variant_rejected test_gates_zero_ad.py::test_check_domain_denylist_hit_rejected test_gates_zero_ad.py::test_check_domain_clean_domain_passes test_gates_zero_ad.py::test_check_domain_empty_allowlist_fail_close ／ 機能別設計 = features/kpi-handoff.md

## DU-08 `gates/evidence_check.py`（CMP-03）

### `def check_complete(conn: Connection, task_id: int) -> None`

- **pre**: task の workflow が load 可能で required_evidence_json を持つ／done 遷移 guard（G5）から呼ばれる（verifying → done の前提検査）
- **post**: 現 workflow の required kind 全てが当該 task の evidence に存在し、各 kind の型契約規則（s0-contract §2.1）を DU-09 の validator で再検証して全通過の場合のみ返る／read-only（evidence を追加・変更しない）
- **raises**: `EvidenceIncomplete`（必須 kind の欠落・kind 規則違反での done 要求（done 拒否 — verifying のまま））／`FatalError`（required_evidence_json に evidence.kind enum 外の値が宣言されている（判定不能は拒否側へ — fail-close）） ／ **pure**: no

- **DTO・値オブジェクト**: なし
- **状態遷移**: なし
- **DB read**: workflows／tasks／evidence ／ **DB write**: なし
- **tx 境界**: なし（読み取りのみ/pure）— done 遷移 guard として DU-01 の遷移 transaction 内で評価される（自 BEGIN しない）
- **pure／副作用端点**: 全体が read-only 検査。kind 規則の再検証は DU-09 validator（純関数部）を共有。副作用なし
- **冪等性**: read-only 検査のため何度実行しても DB 不変・同一状態同一判定 ／ **retry/resume**: stateless。再開時の再検査は verifying 状態からの再判定として常に安全（s0-contract §3.3 verifying 行）
- **競合制御**: guard として BEGIN IMMEDIATE の遷移 transaction 内で評価されるため、検査と done UPDATE の間に証跡が変化する競合は構造的に発生しない
- **ログ・証跡**: 不通過は state_transitions rejected 行（done 遷移 guard 経由）＋構造化ログ（task_id・欠落 kind・違反規則の列挙。証跡本文は含めない）
- **依存 API**: DU-09: for_task()（kind 別証跡の取得）／DU-04: load()（required_evidence_json の取得）／DU-10: connect()
- **trace**: AC = AC-28-1 AC-28-2 AC-28-3 AC-28-4 AC-28-5 AC-28-6 ／ TC = TCC-28-1 TCC-28-2 TCC-28-3 TCC-28-4 TCC-28-5 TCC-28-6 ／ UT = test_gates_evidence_check.py::test_check_complete_all_required_kinds_pass test_gates_evidence_check.py::test_check_complete_missing_kind_rejected test_gates_evidence_check.py::test_check_complete_kind_rule_violation_rejected test_gates_evidence_check.py::test_check_complete_unknown_required_kind_fail_close ／ 機能別設計 = features/evidence.md

## DU-09 `evidence/store.py`（CMP-04）

### `def record(conn: Connection, task_id: int, kind: str, value: str, payload: dict, clock: Clock, *, asset_id: int | None = None, commit_hash: str | None = None, external_operation_id: str | None = None, file_path: str | None = None, file_hash: str | None = None, created_by_agent_id: int | None = None) -> int`

- **pre**: kind は evidence enum（10 種）内／payload は s0-contract §2.1 の kind 別必須キーを充足（構文検証だけでなく本 API が INSERT 前に実施）／value は kind 内での安定した同一性キー
- **post**: kind 別必須キー・列整合（asset_id/external_operation_id/file_path/file_hash/commit_hash）・追加検証（review_pass は result=PASS かつ reviewer≠author、commit_hash は 40/64 桁、file_hash は 64 桁、approval は approvals 相互整合、operation_log は secret/本文/credential 禁止）を全通過した場合のみ INSERT し evidence_id を返す／credential/secret パターン（鍵語・トークン形状の正規表現集合 — DU-14 と共有・config 拡張可）の混入は kind を問わず拒否／created_at は clock から供給
- **raises**: `GateRejected`（kind 別必須キー欠落・列整合違反・PASS 値不正・桁数不正・approvals 相互整合違反（SchemaVerificationFailed 相当 — INSERT しない・DB 不変））／`SelfReviewRejected`（review_pass の reviewer が author と同一 agent/principal）／`CredentialLeakDetected`（payload・value への credential/secret パターン混入（記録拒否・マスクの上 escalate 誘導）） ／ **pure**: no

### `def for_task(conn: Connection, task_id: int, kind: str | None = None) -> list[Evidence]`

- **pre**: conn は db.connect() 由来
- **post**: 該当 task の証跡行（kind 指定時は絞込み）を返す（read-only・DB 不変）
- **raises**: なし ／ **pure**: yes

### `def exists(conn: Connection, task_id: int, kind: str, value: str) -> bool`

- **pre**: conn は db.connect() 由来
- **post**: UNIQUE(task_id, kind, value) キーでの存在照会結果を返す（read-only）
- **raises**: なし ／ **pure**: yes

- **DTO・値オブジェクト**: Evidence(id: int, task_id: int, kind: str, value: str, payload: dict, created_at: str) — 読取り専用の証跡行ビュー（frozen）
- **状態遷移**: なし
- **DB read**: evidence／tasks／agents／approvals／assets／pair_plan_quality／external_operations ／ **DB write**: evidence
- **tx 境界**: 単発 record() は自トランザクション。遷移 guard・TLP 生成・`_record_decision` 等との合成時は呼出し側（DU-01/02/18）の transaction に参加（証跡化→状態遷移の順序は NFR-3）
- **pure／副作用端点**: kind 別 validator・credential パターン照合は純関数部（CMP-03 の証跡完備検査と共有）。副作用端点は evidence INSERT のみ。UPDATE/DELETE API は存在しない（append-only は API 非提供＋保護トリガの二重防御）
- **冪等性**: 重複投入は UNIQUE(task_id, kind, value) で拒否（クラッシュ後リトライの二重到達は冪等拒否で収束 — AC-54-3）。同一入力の再検証・再 INSERT は安全 ／ **retry/resume**: stateless（テーブル以外の状態なし）。INSERT 失敗は transaction ごと消え中間状態なし。再開後の証跡補完は同一 value キーで冪等
- **競合制御**: UNIQUE 制約が並行 INSERT の二重登録を防衛。append-only のため更新競合は構造的に不存在。呼出し側 transaction 参加時は所有者の直列化に従う
- **ログ・証跡**: evidence テーブル自体が証跡正本（append-only・保護トリガで改竄不能）。拒否は例外＋構造化ログ（task_id/kind/事由コード — payload 本文・secret は記録しない）
- **依存 API**: DU-10: connect()／DU-14: scan() と共有する credential パターン集合（正本は registry/secrets 側）
- **trace**: AC = AC-28-1 AC-28-2 AC-28-3 AC-28-4 AC-28-5 AC-28-6 AC-47-1 AC-47-2 AC-47-3 AC-47-4 AC-47-5 AC-47-6 AC-54-1 AC-54-2 AC-54-3 AC-54-4 AC-54-5 ／ TC = TCC-28-1 TCC-28-2 TCC-28-3 TCC-28-4 TCC-28-5 TCC-28-6 TCC-47-1 TCC-47-2 TCC-47-3 TCC-47-4 TCC-47-5 TCC-47-6 TCC-54-1 TCC-54-2 TCC-54-3 TCC-54-4 TCC-54-5 ／ UT = test_evidence_store.py::test_record_valid_kind_payload_inserts_and_returns_id test_evidence_store.py::test_record_missing_required_key_rejected_per_kind test_evidence_store.py::test_record_column_consistency_violation_rejected test_evidence_store.py::test_record_review_pass_result_not_pass_rejected test_evidence_store.py::test_record_review_pass_reviewer_equals_author_rejected test_evidence_store.py::test_record_commit_hash_length_boundary_40_64 test_evidence_store.py::test_record_file_hash_length_boundary_64 test_evidence_store.py::test_record_approval_mutual_consistency_enforced test_evidence_store.py::test_record_credential_pattern_in_payload_rejected test_evidence_store.py::test_record_duplicate_task_kind_value_rejected_idempotent test_evidence_store.py::test_for_task_filters_by_kind_read_only test_evidence_store.py::test_exists_reflects_unique_key_presence test_evidence_store.py::test_no_update_delete_api_and_trigger_blocks_mutation ／ 機能別設計 = features/evidence.md

## DU-10 `db/connect.py`（CMP-05）

### `def connect(path: str | Path) -> Connection`

- **pre**: path は migration 適用済み SQLite ファイル（未適用 DB は不正な実行環境）
- **post**: PRAGMA foreign_keys=ON・journal_mode=WAL・busy_timeout（config.sqlite_busy_timeout_ms）を設定し row_factory を構成した Connection を返す（唯一の接続入口 — これを経ない接続経路をコード上に存在させない）／保護トリガ（config/evidence/state_transitions/strategic_briefs/tactical_learning_packets の append-only／整合トリガ 14 本）の存在を確認してから返す
- **raises**: `FatalError`（保護トリガ未適用・PRAGMA 設定不能・スキーマ未適用 DB（不正な実行環境として接続を返さない — fail-close）） ／ **pure**: no

- **DTO・値オブジェクト**: なし
- **状態遷移**: なし
- **DB read**: config ／ **DB write**: なし
- **tx 境界**: なし（読み取りのみ/pure）— 接続構成と検査のみ。業務 transaction は各所有 DU（DU-01/02 等）が開閉する
- **pure／副作用端点**: トリガ存在検査・PRAGMA 検証は純関数的検査。副作用は接続オブジェクトの生成と PRAGMA 設定のみ（DB 行を書かない）
- **冪等性**: 何度呼んでも同一構成の Connection を返す（検査は read-only）。失敗時に部分構成の接続を漏らさない ／ **retry/resume**: stateless。クラッシュ後の再接続は同一検査を再実行するのみ。検査不合格 DB は使用開始自体を拒否（db-design §4）
- **競合制御**: WAL＋busy_timeout で読み書き並行を許容し、SQLITE_BUSY は busy_timeout 内待機→超過を呼出し側で retryable_failure に正規化（s0-contract §1）。書込みは kernel 単一 writer 前提
- **ログ・証跡**: 接続検査の不合格は FatalError＋構造化ログ（path・欠落トリガ名。credential なし — DB パスは非秘匿）
- **依存 API**: なし
- **trace**: AC = AC-71-1 AC-71-2 AC-71-3 AC-71-4 ／ TC = TCC-71-1 TCC-71-2 TCC-71-3 TCC-71-4 ／ UT = test_db_connect.py::test_connect_sets_foreign_keys_on test_db_connect.py::test_connect_sets_wal_and_busy_timeout test_db_connect.py::test_connect_configures_row_factory test_db_connect.py::test_connect_missing_protection_trigger_fatal test_db_connect.py::test_connect_unmigrated_db_fatal test_db_connect.py::test_connected_db_append_only_trigger_blocks_update_delete ／ 機能別設計 = features/migration.md

## DU-11 `db/migrate.py`（CMP-05）

### `def apply_all(conn: Connection, migrations_dir: Path, clock: Clock, applied_by: str) -> list[Applied]`

- **pre**: migrations_dir に NNNN_description.sql の連番・不変ファイルが存在（0001 = s0-contract §2 正準 DDL と等価 — G-DDL-APPLY が JSON 正本側を常時検証）／適用済み migration は編集されていない（checksum で検証）
- **post**: 未適用の連番 SQL を順に適用し、適用ごとに version・migration_name・checksum_sha256・applied_at（clock）・applied_by を schema_version へ同一 transaction で INSERT／適用済み version はスキップ（schema_version 照合による冪等再開 — version が冪等キー）／0001 適用後は 25 テーブル（業務 23＋インフラ 2）＋保護トリガ 14 本が成立する
- **raises**: `FatalError`（同 version 既存（重複適用）・非連番・SQL 適用失敗（当該版ごと rollback し停止 — MigrationChecksumMismatch/SchemaVerificationFailed を包含する正規化先））／`MigrationChecksumMismatch`（適用済み migration ファイルの事後編集による checksum 不一致（適用前に停止）） ／ **pure**: no

### `def verify(conn: Connection) -> None`

- **pre**: conn は migration 適用済み DB への接続
- **post**: PRAGMA foreign_key_check／integrity_check 違反 0 件・25 テーブルと保護トリガ 14 本の存在・TLP 孤児検査（packet を持たない終端 lower run = 0 件）・相互整合検査（approvals.evidence_id ↔ approval 証跡、pair passed の review 証跡実在、measurements.evidence_id の kind=measurement）を全通過した場合のみ返る／検査はすべて read-only（何度でも安全・自動修復しない）
- **raises**: `MigrationVerifyFailed`（FK/integrity 検査失敗・テーブル/トリガ欠落・相互整合違反（FatalError 系 — 不合格 DB は使用開始拒否・backup 復元へ））／`FatalError`（TLP 孤児検出（packet なし終端 lower run > 0 件 → escalate。自動修復しない — fail-close）） ／ **pure**: no

- **DTO・値オブジェクト**: Applied(version: int, migration_name: str, checksum_sha256: str, applied_at: str) — 適用結果の値オブジェクト（frozen）
- **状態遷移**: なし
- **DB read**: schema_version／loop_runs／tactical_learning_packets／strategic_briefs／approvals／evidence／pair_plan_quality／measurements ／ **DB write**: schema_version
- **tx 境界**: 1 migration = 1 transaction（SQL 適用と schema_version INSERT を同一 transaction でコミット — クラッシュは当該版ごと巻き戻る）。verify は transaction を持たない（read-only）
- **pure／副作用端点**: checksum 計算・連番検証・検査 SQL の組立は純関数部。副作用端点は migration SQL の適用と schema_version INSERT のみ。applied_at は Clock 注入
- **冪等性**: version = 冪等キー。適用済みはスキップ、改変は checksum で検知停止。verify は read-only で冪等。失敗版は同 version を書換えず次 version で修正（s0-contract §5.2） ／ **retry/resume**: クラッシュは当該 migration transaction ごと rollback し、再実行は schema_version 照合から冪等再開。昇格失敗は適用前 backup から復元（TCC-RESUME-2）。孤児・破損の検出は escalate（自動修復しない）
- **競合制御**: migration 適用は単独プロセス・排他実行が前提（適用中の業務書込みなし）。transaction 単位の適用で部分適用状態を残さない
- **ログ・証跡**: schema_version 行（version/checksum/applied_at/applied_by）が適用証跡の正本。verify 結果は検証ログ（違反項目の列挙 — credential なし）。backfill は migration に混ぜず件数・hash・失敗を evidence に残す（db-design §4）
- **依存 API**: DU-10: connect()
- **trace**: AC = AC-71-1 AC-71-2 AC-71-3 AC-71-4 AC-72-1 AC-72-2 AC-72-3 AC-72-4 AC-72-5 AC-SR-05 AC-SR-11-1 AC-SR-11-2 AC-SR-11-3 AC-SR-11-4 AC-SR-11-5 AC-SR-11-6 ／ TC = STC-I-01 STC-I-02 TCC-71-1 TCC-71-2 TCC-71-3 TCC-71-4 TCC-72-1 TCC-72-2 TCC-72-3 TCC-72-4 TCC-72-5 TCC-RESUME-2 TCC-SR-05 TCC-SR-11-1 TCC-SR-11-2 TCC-SR-11-3 TCC-SR-11-4 TCC-SR-11-5 TCC-SR-11-6 ／ UT = test_db_migrate.py::test_apply_all_empty_db_creates_25_tables_and_14_triggers test_db_migrate.py::test_apply_all_records_version_checksum_applied_at_by test_db_migrate.py::test_apply_all_skips_applied_versions_idempotent test_db_migrate.py::test_apply_all_duplicate_version_stops_fatal test_db_migrate.py::test_apply_all_checksum_mismatch_stops_before_apply test_db_migrate.py::test_apply_all_crash_mid_migration_rolls_back_whole_version test_db_migrate.py::test_verify_complete_schema_passes test_db_migrate.py::test_verify_missing_table_or_trigger_fails test_db_migrate.py::test_verify_foreign_key_violation_fails test_db_migrate.py::test_verify_tlp_orphan_detected_fatal test_db_migrate.py::test_append_only_triggers_reject_update_and_delete test_db_migrate.py::test_strategic_briefs_content_update_rejected_status_transition_allowed test_db_migrate.py::test_tlp_integrity_trigger_rejects_mismatched_insert ／ 機能別設計 = features/migration.md、features/tlp.md、features/strategic-brief.md

## DU-12 `config/store.py`（CMP-06）

### `def set(conn: Connection, key: str, value: object, value_type: str, reason: str, agent_id: int | None, clock: Clock) -> int`

- **pre**: value_type は string/integer/number/boolean/json のいずれか／reason は非空（履歴の説明責任 — なぜ変えたかを消せなくする）／conn は config 保護トリガ適用済み DB への接続
- **post**: 旧行を UPDATE/DELETE せず新行を INSERT し、supersedes_config_id に直前の有効行を連鎖させる（append-only 履歴）／changed_at は clock から供給。同 key 同時刻の INSERT は拒否（履歴の全順序保証）
- **raises**: `ConfigReasonMissing`（reason が空・欠落の変更要求（INSERT しない））／`GateRejected`（同一 key 同一 changed_at の INSERT（UNIQUE(key, changed_at) と二重防御）・value_type 不整合な value） ／ **pure**: no

### `def get(conn: Connection, key: str, default: object | None = None) -> object`

- **pre**: conn は db.connect() 由来
- **post**: key ごとに changed_at 最大の行を有効値とし、value_type に従って型変換して返す（read-only）／key 不在時は default 指定があれば default、なければ fail-close（既定値へ黙って倒さない）
- **raises**: `ConfigKeyUnresolved`（未定義 key の参照で default 未指定（安全側既定値表にない key — fail-close）） ／ **pure**: no

- **DTO・値オブジェクト**: なし
- **状態遷移**: なし
- **DB read**: config ／ **DB write**: config
- **tx 境界**: 1 変更 = 1 INSERT transaction（set の単発 tx）。get は transaction を持たない（read-only）
- **pure／副作用端点**: 型変換・supersedes 解決・最新行選択は純関数部。副作用端点は config INSERT のみ。changed_at は Clock 注入（現在時刻直取得禁止）
- **冪等性**: 同一 key 同一時刻の再 INSERT は拒否（クラッシュ後リトライは changed_at が変わり別行 — 履歴として保存され最新行選択で収束）。get は read-only で冪等 ／ **retry/resume**: stateless ロジック＋append-only テーブルで復旧不要。誤設定は新行 INSERT（supersedes 連鎖）でのみ是正し履歴は消えない
- **競合制御**: UNIQUE(key, changed_at) が並行 set の同時刻衝突を拒否。読取りは changed_at 最大行の決定的選択で常に一意。UPDATE/DELETE は API 非提供＋保護トリガの二重で拒否
- **ログ・証跡**: config 行自体が変更履歴の正本（key/value/value_type/changed_at/changed_by_agent_id/reason/supersedes_config_id — いつ誰がなぜ変えたか）。credential は config に置かない（DU-14 に分離・混入は DU-09/14 の検査対象）
- **依存 API**: DU-10: connect()
- **trace**: AC = AC-33-1 AC-33-2 AC-33-3 AC-33-4 AC-33-5 AC-33-6 ／ TC = TCC-33-1 TCC-33-2 TCC-33-3 TCC-33-4 TCC-33-5 TCC-33-6 ／ UT = test_config_store.py::test_set_inserts_new_row_with_supersedes_chain test_config_store.py::test_set_without_reason_rejected test_config_store.py::test_set_same_key_same_changed_at_rejected test_config_store.py::test_get_returns_latest_row_type_converted test_config_store.py::test_get_missing_key_returns_default_when_given test_config_store.py::test_get_missing_key_without_default_fail_close test_config_store.py::test_direct_update_delete_blocked_by_trigger ／ 機能別設計 = features/brand-isolation.md

## DU-13 `registry/resolver.py`（CMP-07）

### `def resolve(conn: Connection, service: str, operation: str) -> Route`

- **pre**: conn は db.connect() が返す接続（PRAGMA foreign_keys=ON 保証済み）／接続レジストリ行（config の registry.<service>.<operation> 系 key）が seed 済み／service・operation は空文字でない
- **post**: 優先順 mcp → api → browser →（例外宣言時のみ）有償 の順で最初の有効経路を Route として返す／経路切替はレジストリ行（config INSERT）だけで反映され、コード変更を要しない（AC-41-1）／X（x.com）への書込み系 operation は browser 経路を返さない（BR-M-X-4 — 解決段階で遮断）／拒否時は operation_log 証跡へ理由を記録する経路（呼出元 DU-09 経由）に必要な事由コードを例外へ載せる
- **raises**: `RouteNotRegistered`（未登録 service/operation の解決要求、又は fallback なしの第一経路が無効（kind=absent — 推測で経路を返さない））／`PaidRouteDenied`（例外宣言（config の paid 許可行＋承認参照）なしに有償 API 経路のみが該当（kind=blocked））／`ProhibitedMediaWrite`（X へのブラウザ書込み経路の解決要求（kind=blocked — バイパスなし）） ／ **pure**: no

### `def list_declared(conn: Connection, service: str | None = None) -> list[RegistryRow]`

- **pre**: conn は db.connect() が返す接続／service 指定時は当該 service の宣言行のみに絞る
- **post**: レジストリ宣言行を読取専用で返す（診断・ヘルスチェック用。DB を変更しない）／宣言 JSON が schema 不適合の行は結果に含めず不正行として報告する（fail-close）
- **raises**: なし ／ **pure**: no

- **DTO・値オブジェクト**: Route(service: str, operation: str, route_type: str, auth_kind: str, endpoint: str) — frozen。route_type は playbooks DDL の enum（mcp/browser/api/wp_rest/wp_cli）と同語彙／RegistryRow(key: str, service: str, operation: str, priority: int, declaration: dict) — frozen。宣言 JSON の検証済み展開
- **状態遷移**: なし
- **DB read**: config ／ **DB write**: なし
- **tx 境界**: なし（読み取りのみ — config の changed_at 最大行を有効宣言として参照）
- **pure／副作用端点**: 経路優先順・宣言 JSON 検証・X 書込み判定は pure 関数（`_select_route`）に分離。DB 読取だけが副作用端点
- **冪等性**: 同一レジストリ状態に対する resolve は決定的に同一 Route を返す。解決自体は外部副作用を持たない ／ **retry/resume**: リトライ不要（読取のみ）。RouteNotRegistered/PaidRouteDenied/ProhibitedMediaWrite は自動リトライ経路を持たず external-if-design §5 の写像（escalate 又は non_retryable_failure／blocked は拒否）へ倒す
- **競合制御**: 読取専用のため競合制御なし。config の append-only 履歴により解決中の宣言書換えは新行としてのみ現れ、読取スナップショットは transaction 内で一貫
- **ログ・証跡**: 解決成功・拒否の事由（service/operation/route_type/事由コード）を構造化ログへ記録。拒否は呼出元が operation_log 証跡（DU-09 経由）に残す — 秘匿値は含めない
- **依存 API**: DU-10: connect()／DU-12: get()
- **trace**: AC = AC-41-1 AC-41-2 AC-41-3 AC-41-4 AC-41-5 AC-41-6 ／ TC = TC-041 TCC-41-1 TCC-41-2 TCC-41-3 TCC-41-4 TCC-41-5 TCC-41-6 ／ UT = test_registry_resolver.py::test_resolve_priority_order_mcp_first test_registry_resolver.py::test_resolve_switch_by_config_insert_only test_registry_resolver.py::test_unregistered_service_route_not_registered test_registry_resolver.py::test_paid_route_denied_without_exception test_registry_resolver.py::test_x_browser_write_route_prohibited test_registry_resolver.py::test_list_declared_readonly_and_schema_failclose ／ 機能別設計 = external-operations.md

## DU-14 `registry/secrets.py`（CMP-07）

### `def get_credential(name: str, scope: Literal['test', 'prod']) -> Secret`

- **pre**: credential は OS キーチェーン又は Fernet 暗号化ファイルストアに人手で投入済み（BR-F4）／name はプロファイル接頭規約 <profile_key>/<service>/<name> に従う（ブランド隔離設計 §3 — 物理ファイルもプロファイル別・test/prod 物理分離と直交）／scope は test/prod のいずれか（物理別ファイルを選択）
- **post**: 復号値はメモリ内の Secret ハンドルのみとして返り、SQLite・repo・ログ・evidence へは書かれない（参照ハンドル設計 — NFR-4）／Secret の repr/str は常に伏字であり、例外メッセージ・トレースバック経由でも平文が漏れない／外部操作後も復号値を永続化しない（メモリ内のみ）
- **raises**: `SecretUnavailable`（未投入・復号失敗・失効（kind=auth）。外部操作を開始せず credential 再投入（人の関与）へ escalate 誘導） ／ **pure**: no

### `def check_endpoint(secret: Secret, endpoint_url: str) -> None`

- **pre**: secret は get_credential が返した scope 付きハンドル／endpoint_url は接続予定の実 URL（接続前に必ず呼ぶ）
- **post**: scope×endpoint が正当（test→Docker/mock、prod→本番）の場合のみ正常復帰し、接続を許可する／検査は接続前に完了し、不正組合せでは外部呼出が 0 回である（環境契約 = s0-contract §6）
- **raises**: `CredentialEndpointMismatch`（test credential→本番 endpoint、又は prod credential→Docker/mock の組合せ（kind=auth — 接続前拒否）） ／ **pure**: yes

### `def scan(targets: list[Path], conn: Connection) -> list[Finding]`

- **pre**: targets は repo・構造化ログ等の走査対象パス（存在検査は内部で行い、欠落はエラー報告）／conn は SQLite 全行走査用の接続（読取のみ）
- **post**: 平文 credential パターン（鍵語・トークン形状の正規表現集合 — 正本は本モジュール、DU-09 と共有・config 拡張可）の検出結果を Finding のリストで返す（TC-047 の実装点）／検出 0 件が AC-47-1 の合格条件。検出時は呼出元が CredentialLeakDetected を operation_log に記録し当該タスクを escalate へ誘導する／Finding は位置・パターン名のみを持ち、マッチした平文値そのものを含めない
- **raises**: なし ／ **pure**: no

### `def mask(text: str) -> str`

- **pre**: text はログ・operation_log・evidence へ書き出す直前の任意文字列
- **post**: config.secret.masking_patterns と本モジュールのパターン集合に一致する部分をすべて伏字化した文字列を返す（マスキング層 — external-if-design §6）／入力を変更しない（新文字列を返す純関数）
- **raises**: なし ／ **pure**: yes

- **DTO・値オブジェクト**: Secret(scope: Literal['test','prod']) — 復号値を閉じ込めた wrapper。repr/str/format は常に伏字、比較・シリアライズ不可。平文取出しは接続層内部の一箇所のみ／Finding(target: str, pattern_name: str, location: str) — 平文値を含まない検出報告
- **状態遷移**: なし
- **DB read**: config／evidence／tasks／external_operations／approvals／playbooks／assets／measurements／state_transitions／spend_ledger ／ **DB write**: なし
- **tx 境界**: なし（読み取りのみ — 秘匿ストアは SQLite 外の暗号化ファイル/OS キーチェーン）
- **pure／副作用端点**: check_endpoint・mask・パターン照合は pure。復号（ファイル/キーチェーン読取）と DB/ファイル走査だけが副作用端点
- **冪等性**: get_credential・scan は同一ストア状態で決定的。副作用を持たないため再実行に補償は不要 ／ **retry/resume**: SecretUnavailable・CredentialEndpointMismatch は自動リトライしない（kind=auth — 再投入は人の関与で escalate。再投入後は同一タスク状態から再実行 — AC-47-3）
- **競合制御**: 読取専用・ファイルは open 時スナップショット。秘匿ストアの更新（人手投入）とは排他不要（次回 get_credential から反映）
- **ログ・証跡**: 取得・検査・走査の結果（name・scope・endpoint ホスト・検出件数）のみ構造化ログへ記録。秘匿値・平文パターン一致部分はいかなる書出しにも含めない（全書出しは mask 通過）
- **依存 API**: DU-10: connect()／DU-12: get()
- **trace**: AC = AC-47-1 AC-47-2 AC-47-3 AC-47-4 AC-47-5 AC-47-6 ／ TC = TC-047 TCC-47-1 TCC-47-2 TCC-47-3 TCC-47-4 TCC-47-5 TCC-47-6 ／ UT = test_registry_secrets.py::test_secret_repr_and_exception_masked test_registry_secrets.py::test_get_credential_unavailable_fail_close test_registry_secrets.py::test_endpoint_mismatch_rejected_before_connect test_registry_secrets.py::test_scan_repo_sqlite_logs_zero_plaintext test_registry_secrets.py::test_scan_finding_contains_no_plaintext test_registry_secrets.py::test_mask_patterns_from_config ／ 機能別設計 = external-operations.md、brand-isolation.md

## DU-15 `connectors/browser.py`（CMP-08）

### `def launch(headed: bool, scope: ScopeContext, storage_state_path: Path | None = None) -> BrowserSession`

- **pre**: scope は resolve_scope(profile_key) だけが生成する検証済み ScopeContext（ブランド隔離設計 §2）／storage_state_path は当該 profile の名前空間（<profile_key>/ 配下）のみ許可 — 別ブランドの storage_state 再利用は拒否（隔離設計 §3）
- **post**: Playwright セッションを起動し、storage_state をプロファイル別ファイルへ保存/再利用する／セッションは ScopeContext を保持し、以後の操作がプロファイル帰属を持つ
- **raises**: `RetryableError`（ブラウザ起動失敗（一時的環境要因 — retryable_failure として再試行可））／`CrossProfileAccessDenied`（scope と異なるプロファイルの storage_state_path を指定（ログイン混線の遮断 — fail-close）） ／ **pure**: no

### `def screenshot(session: BrowserSession, url: str, out_path: Path) -> Path`

- **pre**: url は許可リスト内（呼出元が DU-07 check_domain 通過済み — 外部 IF 表の前提）／session は launch が返した有効セッション
- **post**: URL 到達確認（最終 URL 一致）つきで capture を out_path へ保存しパスを返す／file_hash の固定（SHA-256）と screenshot 証跡化は呼出し側（DU-09 経由）で行う
- **raises**: `UrlDenied`（遷移先が要求 URL と不一致・許可リスト外へリダイレクト（kind=blocked — deny-by-default））／`RetryableError`（到達 timeout・描画失敗（読取り系 — 再試行可。上限到達で escalated は呼出元の遷移判断）） ／ **pure**: no

### `def run_playbook(conn: Connection, session: BrowserSession, playbook: Playbook, intent: ConnectorIntent, rng: Rng, clock: Clock) -> BrowserResult`

- **pre**: playbook は DU-16 get() が返した status=active の行（missing/broken は到達前に拒否済み）／書込み系 intent は idempotency_key と pair_pass を保持（外部 IF §2 前提。1 外部操作 = 1 key = external_operations 1 行）／X（x.com）向け書込み intent はここへ到達しない（DU-13 で遮断済み — 到達時は二重防御で拒否）／rng・clock は注入（モジュール内 random/datetime.now() 直呼び禁止）
- **post**: 書込み系は external_operations を prepared→sent→confirmed の順で各々コミットして遷移させ、confirmed 後に operation_log 証跡（DU-09 経由）を派生させてから結果を返す（証跡が先、遷移が後）／連続書込み操作間に config.rate_interval_min_sec〜rate_interval_max_sec（暫定 1〜5 秒）の一様乱数待機を挿入し、seed と生成間隔値を構造化ログへ 100% 記録する（NFR-7・BR-F5 — 同一 seed で間隔列を再現可能）／読取り系はレート節度の対象外（通常速度）で external_operations 行を作らない／BrowserResult は operation_log 証跡への参照（evidence_refs）を成功時に必ず持つ
- **raises**: `ProhibitedMediaWrite`（X への書込み手順の実行要求（kind=blocked — 送信 0 回・バイパスなし））／`RateLimitExceeded`（媒体別日次 cap（config.rate.<media>.daily_write_cap）到達・外部 429（kind=rate-limit — 実行前拒否し operation_log 記録、当日拒否・翌日まで waiting））／`RetryableError`（送信前 timeout・一時的操作失敗（同一 idempotency key の無消費再送で回復可））／`OperationUnverifiable`（sent 後の結果照合不能（kind=unknown — external_operations を unknown 化し再送せず escalate）） ／ **pure**: no

- **DTO・値オブジェクト**: BrowserSession(scope: ScopeContext, storage_state_path: Path) — frozen ハンドル。低レベル page/driver は非公開／ConnectorIntent(service: str, operation: str, target: str, payload_ref: str, idempotency_key: str | None, pair_pass: PairPass | None) — frozen（external-if-design §3）／BrowserResult(ok: bool, external_operation_id: int | None, remote_object_id: str | None, response_hash: str | None, evidence_refs: tuple) — frozen
- **状態遷移**: external_operations.status: prepared→sent→confirmed／rejected／unknown（書込み系のみ・各段階を各々コミット — loop/task の状態機械遷移は行わず呼出元が DU-01 経由で発火）
- **DB read**: external_operations／config ／ **DB write**: external_operations
- **tx 境界**: external_operations の prepared・sent・confirmed/rejected/unknown を各々独立 transaction でコミット（送信直後クラッシュの検出窓 — s0-contract §1）。operation_log 証跡は confirmed 後に DU-09 の transaction で記録
- **pure／副作用端点**: 手順展開・待機間隔計算（rng から一様乱数）・結果分類は pure 関数に分離。Playwright I/O・external_operations 書込み・ファイル保存が副作用端点
- **冪等性**: 書込み 1 操作 = 1 idempotency key = external_operations 1 行（UNIQUE が二重送信検出 — BR-I7）。再実行は同 key 行の status 照合から始め、confirmed 済みは再送せず結果補完のみ ／ **retry/resume**: rate-limit／送信前 timeout のみ retryable（retry_count 無消費の同一 key 再送）。sent はリモート照合（external operation ID／remote object ID／idempotency key）で成功確認時のみ confirmed 化＋証跡補完、照合不能は unknown で再送 0 回・escalate（s0-contract §3.3 — AC-42-3）
- **競合制御**: external_operations の status 更新は現 status を WHERE に含む条件付き UPDATE（変更行数 0 は競合として FatalError）。ブラウザセッションは execution 単位で専有し共有しない
- **ログ・証跡**: 全書込み操作の operation_log 証跡（service/operation/external_operation_id/request_fingerprint/result — 秘匿値・本文なし）を DU-09 経由で記録。rate 待機の seed・間隔値・拒否事由を構造化ログへ記録（マスキング層通過）
- **依存 API**: DU-13: resolve()／DU-14: get_credential()／DU-14: check_endpoint()／DU-16: get()／DU-16: record_success()／DU-16: record_failure()／DU-09: record()／DU-12: get()／DU-10: connect()
- **trace**: AC = AC-42-1 AC-42-2 AC-42-3 ／ TC = TCC-42-1 TCC-42-2 TCC-42-3 TCC-RESUME-1 ／ UT = test_connectors_browser.py::test_launch_failure_retryable test_connectors_browser.py::test_storage_state_profile_scoped_cross_denied test_connectors_browser.py::test_screenshot_url_reachability_and_mismatch_denied test_connectors_browser.py::test_run_playbook_write_interval_uniform_and_seed_logged test_connectors_browser.py::test_x_write_rejected_zero_send test_connectors_browser.py::test_daily_cap_rejected_before_send test_connectors_browser.py::test_sent_reconcile_confirms_without_resend test_connectors_browser.py::test_sent_unverifiable_marked_unknown_no_resend ／ 機能別設計 = external-operations.md、brand-isolation.md

## DU-16 `connectors/playbooks.py`（CMP-09）

### `def get(conn: Connection, service: str, operation: str, route_type: str) -> Playbook`

- **pre**: conn は db.connect() が返す接続／route_type は playbooks DDL の enum（mcp/browser/api/wp_rest/wp_cli）の値
- **post**: UNIQUE(service, operation, route_type) の行を status=active の場合のみ Playbook として返す／procedure_json・selector_json は schema 検証済みで返る（壊れた JSON は FatalError）／セレクタ・手順にブランド固有値を焼き込まない前提を検証（充填は config/profile_json 側 — 隔離設計 §3）
- **raises**: `PlaybookMissing`（該当行なし（kind=absent — 自己修復は FR-43/S2 へ委譲。拒否して書込みを開始しない））／`PlaybookBroken`（status=broken の行参照（kind=absent — 書込みを開始しない）。status=retired も修復・使用対象外として同様に拒否）／`FatalError`（procedure_json/selector_json の schema 不適合（壊れた地図定義の fail-close）） ／ **pure**: no

### `def record_success(conn: Connection, playbook_id: int, agent_id: int, clock: Clock) -> None`

- **pre**: playbook_id は実行に成功した地図の行 id／agent_id は検証を行った active な agent（last_verified_by_agent_id へ記録）
- **post**: last_success_at を clock から更新し、consecutive_failures を 0 に戻し、last_verified_by_agent_id を更新する／永続化はストア副層 `_store` 経由のみ（生 SQL はここだけ — 基本設計 §1 規約 3）
- **raises**: なし ／ **pure**: no

### `def record_failure(conn: Connection, playbook_id: int, clock: Clock) -> None`

- **pre**: playbook_id は実行に失敗した地図の行 id／連続失敗閾値は config.playbook_broken_threshold（ハードコード禁止）
- **post**: consecutive_failures を 1 加算し last_failure_at を clock から更新する／加算後に閾値到達なら同一 transaction 内で status を broken へ降格する（以後の get は PlaybookBroken で拒否）／降格の事実を構造化ログへ記録する（escalate 誘導は呼出元）
- **raises**: なし ／ **pure**: no

- **DTO・値オブジェクト**: Playbook(id: int, service: str, operation: str, route_type: str, procedure: dict, selectors: dict | None, status: str) — frozen。検証済み地図
- **状態遷移**: なし
- **DB read**: playbooks／config ／ **DB write**: playbooks
- **tx 境界**: record_success／record_failure が各々単一 transaction（失敗加算と broken 降格は同一 transaction — 中間状態を外部に見せない）。get は読み取りのみ
- **pure／副作用端点**: schema 検証・閾値判定は pure 関数。playbooks 行の読み書き（ストア副層 `_store`）だけが副作用端点
- **冪等性**: get は決定的。record_success は同値上書きで冪等。record_failure は呼出し 1 回 = 失敗 1 件の加算（呼出元は 1 実行失敗につき 1 回だけ呼ぶ契約 — 再開時は external_operations 照合で二重加算を防ぐ） ／ **retry/resume**: missing/broken は自動リトライなし（kind=absent — フォールバック経路があれば DU-13 の再解決、なければ escalate/failed）。クラッシュ後再開時は playbooks の現 status を読み直して判断（メモリ状態禁止）
- **競合制御**: consecutive_failures の加算は UPDATE ... SET consecutive_failures = consecutive_failures + 1 の相対更新（読み書き競合で失われない）。降格判定は同一 transaction 内の再読で確定
- **ログ・証跡**: get の拒否事由（missing/broken/retired）と降格イベントを構造化ログへ記録し、呼出元が operation_log 証跡（DU-09 経由）へ理由を残す
- **依存 API**: DU-10: connect()／DU-12: get()
- **trace**: AC = AC-42-1 AC-42-2 AC-42-3 AC-43-1 AC-43-2 AC-43-3 ／ TC = TC-042 TCC-42-1 TCC-42-2 TCC-42-3 TCC-43-1 TCC-43-2 TCC-43-3 TCC-RESUME-1 ／ UT = test_connectors_playbooks.py::test_get_active_playbook_validated test_connectors_playbooks.py::test_get_missing_rejected test_connectors_playbooks.py::test_get_broken_and_retired_rejected test_connectors_playbooks.py::test_record_failure_increments_and_demotes_at_threshold test_connectors_playbooks.py::test_record_success_resets_failures_and_verifier test_connectors_playbooks.py::test_broken_schema_json_fatal ／ 機能別設計 = external-operations.md

## DU-17 `connectors/wp.py`（CMP-10）

### `def create_draft(conn: Connection, task_id: int, pair_pass: PairPass, html: str, idempotency_key: str, clock: Clock) -> DraftRef`

- **pre**: pair_pass は DU-05 require_pair／DU-06 check_publishable のみが生成できる検証済み値オブジェクト（偽造は sentinel token で FatalError）／idempotency_key は下書き作成専用の新規 key（公開とは別 key の別 external_operations 行）／base URL が Docker WP allow-list（config）内であることを接続前に検査済み
- **post**: external_operations 行を prepared→sent→confirmed で遷移させ（各々コミット）、confirmed 後に operation_log 証跡（DU-09 経由）を派生記録してから DraftRef を返す／WP 側に決定的な meta key として idempotency key を保存し、再開時のリモート照合キーとする／同 key の既 confirmed 行があれば再送せず結果補完のみ行う（冪等）
- **raises**: `PairRequired`（PairPass 未提示・無効での呼出し（コネクタ入口の前提違反 — WP API を呼ばない。error-taxonomy §5 で PairNotEstablished と役割区別））／`ProductionWriteDenied`（Docker 以外の WP endpoint への書込み設定（kind=blocked — 送信 0 回で接続前拒否。環境契約 §6））／`RateLimitExceeded`（config.rate.wp.daily_write_cap／burst_per_min 到達（kind=rate-limit — 実行前拒否・待機））／`RetryableError`（送信前 timeout・一時的接続失敗（同一 key の無消費再送で回復可））／`OperationUnverifiable`（sent のままリモート照合不能（kind=unknown — unknown 化し FatalError → escalated。再送 0 回）） ／ **pure**: no

### `def publish(conn: Connection, task_id: int, pair_pass: PairPass, approval_pass: ApprovalPass, draft_ref: DraftRef, idempotency_key: str, clock: Clock) -> PublishedRef`

- **pre**: approval_pass は decision=approved かつ binding 3 項目完全一致の照合を通過した検証済み値オブジェクト（承認設計 §6 — 承認照合 API のみが生成）／idempotency_key は公開専用の key（下書き作成の key と別 — 別 external_operations 行）／pair・承認・証跡の再検証（公開直前ゲート）を通過済み — 拒否時はここへ到達しない
- **post**: external_operations 行を prepared→sent→confirmed で遷移させ、confirmed 後に operation_log 証跡を派生記録し、canonical URL・WP post ID を PublishedRef で返す／published_url 証跡は register_asset で asset_id を得てから記録する（s0-contract §2.1 の整合列を先に成立 — WF-WP-2 ステップ 6）／承認なしの公開は operation_log 上 0 件が不変条件（ApprovalRequired で送信 0 回拒否）
- **raises**: `ApprovalRequired`（ApprovalPass 未提示・無効での公開要求（kind=blocked — 外部送信 0 回で拒否し 拒否理由を構造化ログ（FN-704）へ記録））／`PairRequired`（PairPass 未提示・無効（WP API を呼ばない））／`ProductionWriteDenied`（Docker 以外の WP endpoint への公開設定（送信 0 回で拒否））／`RateLimitExceeded`（日次 cap・バースト上限到達（実行前拒否））／`OperationUnverifiable`（公開状態が sent のまま照合不能（unknown → escalated。再送しない）） ／ **pure**: no

### `def upload_media(conn: Connection, task_id: int, pair_pass: PairPass, media_path: Path, idempotency_key: str, clock: Clock) -> MediaRef`

- **pre**: media_path は版管理済みソース由来の成果物（content_hash を事前計算済み）／idempotency_key はメディア登録専用 key（1 外部操作 = 1 key = 1 行）
- **post**: external_operations を prepared→sent→confirmed で遷移させ、wp_media_id を MediaRef で返す／content_hash 一致の既存 WP メディアを事前照合し、再アップロードせず参照登録のみで冪等完了する（AC-51-3）
- **raises**: `PairRequired`（PairPass 未提示・無効）／`ProductionWriteDenied`（Docker 以外の endpoint への書込み設定）／`RateLimitExceeded`（cap・バースト上限到達）／`OperationUnverifiable`（sent 照合不能（unknown・再送なし）） ／ **pure**: no

### `def register_asset(conn: Connection, task_id: int, published: PublishedRef, clock: Clock) -> int`

- **pre**: published は publish が返した confirmed 済みの結果／同一 canonical_url／wp_media_id の assets 行は UNIQUE（重複登録は既存行照合で冪等）
- **post**: assets 行（wp_media_id・canonical_url・content_hash）をストア副層 `_assets_store` で INSERT し asset_id を返す／published_url 証跡（DU-09 経由）はこの asset_id 取得後に記録される順序を呼出しフローとして保証する
- **raises**: `FatalError`（confirmed でない external_operations に紐づく登録要求・FK 不整合（IntegrityError の境界正規化）） ／ **pure**: no

- **DTO・値オブジェクト**: DraftRef(draft_post_id: str, draft_url: str, external_operation_id: int) — frozen／PublishedRef(wp_post_id: str, canonical_url: str, content_hash: str, external_operation_id: int) — frozen／MediaRef(wp_media_id: str, media_url: str, content_hash: str, external_operation_id: int) — frozen／PairPass／ApprovalPass は消費のみ（生成は CMP-03 側 — 本 DU は型で受領を強制）
- **状態遷移**: external_operations.status: prepared→sent→confirmed／rejected／unknown（下書き・公開・メディアは各々別 key の別行 — loop/task の状態機械遷移は呼出元が DU-01 経由で発火）
- **DB read**: external_operations／config／tasks／assets ／ **DB write**: external_operations／assets
- **tx 境界**: external_operations の各 status 遷移を独立 transaction でコミット（送信直後クラッシュの検出窓）。assets INSERT は register_asset の単一 transaction。operation_log／published_url 証跡は DU-09 の transaction
- **pure／副作用端点**: request fingerprint 計算・allow-list 判定・照合ロジックは pure。HTTP I/O（低レベル client は `_client` 非公開）と external_operations/assets 書込みが副作用端点
- **冪等性**: 下書き・公開・メディアは各々専用 idempotency key の別 external_operations 行（UNIQUE で二重送信検出）。実行前に同 key 行を照合し confirmed 済みは再送せず結果補完。WP 側 meta key／content_hash 照合で key 非対応面も決定化 ／ **retry/resume**: prepared は同一 key で再送可、sent はリモート照合（post ID／meta key／idempotency key）で成功確認時のみ confirmed 化＋証跡補完し verifying へ、照合不能は unknown とし再送 0 回で escalate（最危険 kill point — s0-contract §3.3・AC-44-3）
- **競合制御**: status 遷移は現 status を条件に含む UPDATE（更新 0 行 = 競合検出で FatalError）。同 key の並行実行は idempotency_key UNIQUE が最終防衛。assets は canonical_url／wp_media_id UNIQUE で重複吸収
- **ログ・証跡**: 全操作の operation_log 証跡（external_operation_id・request_fingerprint・result — 本文・credential なし）と published_url 証跡（url・wp_post_id・external_operation_id・asset_id）を DU-09 経由で記録。拒否（PairRequired/ApprovalRequired/ProductionWriteDenied/RateLimitExceeded）は送信 0 回で理由を operation_log へ
- **依存 API**: DU-06: check_publishable()／DU-05: require_pair()／DU-09: record()／DU-13: resolve()／DU-14: get_credential()／DU-14: check_endpoint()／DU-12: get()／DU-10: connect()
- **trace**: AC = AC-44-1 AC-44-2 AC-44-3 AC-51-1 AC-51-2 AC-51-3 AC-51-4 AC-51-5 ／ TC = TC-044-A TC-044-R TC-GATE-07 TCC-44-1 TCC-44-2 TCC-44-3 TCC-51-1 TCC-51-2 TCC-51-3 TCC-51-4 TCC-51-5 ／ UT = test_connectors_wp.py::test_draft_and_publish_separate_keys_separate_rows test_connectors_wp.py::test_create_draft_prepared_sent_confirmed_each_commit test_connectors_wp.py::test_pair_required_rejected_zero_http test_connectors_wp.py::test_publish_without_approval_pass_rejected test_connectors_wp.py::test_production_endpoint_denied_before_connect test_connectors_wp.py::test_sent_reconcile_confirms_without_resend test_connectors_wp.py::test_sent_unverifiable_unknown_escalates test_connectors_wp.py::test_upload_media_content_hash_idempotent test_connectors_wp.py::test_register_asset_before_published_url_evidence ／ 機能別設計 = external-operations.md、evidence.md

## DU-18 `connectors/approval.py`（CMP-11）

### `def request(conn: Connection, task_id: int, binding: Binding, transport: ApprovalTransport, clock: Clock) -> int`

- **pre**: binding は subject・operation・at の 3 項目が確定した frozen 値（束縛承認 — glossary 正本）／task_id は公開系・金銭系の対象 task（金銭操作型はオートモード判定より先に常時ここへ来る — 承認設計 §4）／approvals の帰属は task チェーン経由の導出スコープ（ブランド隔離設計 §1 — ストア副層が書込み時に親チェーン検査）
- **post**: approvals 行を decision=pending・channel='claude_code_app' で INSERT（ストア副層 approvals_store 経由 — 生 SQL はここだけ）し approval_id を返す／Claude Code アプリへ binding 3 項目を明記した通知を transport 経由で送出する／同一 (task_id, binding_subject, binding_operation, binding_at) の重複要求は UNIQUE 制約で既存行に照合し新規行を作らない（冪等）／pending の間、親 loop_run を waiting にし task は進行させない（先行公開経路なし — 遷移は呼出元が DU-01 経由）
- **raises**: `FatalError`（binding 3 項目の欠落・空文字（承認要求として不成立 — fail-close）） ／ **pure**: no

### `def poll(conn: Connection, approval_id: int, transport: ApprovalTransport, clock: Clock) -> Decision`

- **pre**: approvals 行が存在する（外部 IF 表 poll_decision の前提）／transport は差替可能 interface（本番: アプリ通知、テスト: mock fixture で approve/reject/timeout を再現）
- **post**: approved（binding 3 項目完全一致）は `_record_decision` で approval 証跡 INSERT（DU-09 経由）と approvals.evidence_id 更新を単一 transaction で行い、相互整合の中間状態を外部に見せない／binding 1 項目でも不一致の応答は無効（ApprovalBindingMismatch を記録し decision は pending のまま waiting 継続 — 部分一致許容なし）。binding_at と実公開時点の乖離も不一致として扱う／rejected は ApprovalRejected として Decision に分類を載せ、呼出元が non_retryable_failure → failed を発火（escalate に含めない）。expired は再要求系へ、pending は wait（親 loop_run waiting 維持）／decision の書換え・削除は行わない（approvals は証跡 — 変更は新規要求の別行）
- **raises**: なし ／ **pure**: no

### `def rerequest_on_expired(conn: Connection, approval_id: int, transport: ApprovalTransport, clock: Clock) -> int`

- **pre**: 対象 approvals 行の decision=expired／再要求上限は config.approval_retry_limit（ハードコード禁止）
- **post**: 同一 binding 3 項目の新規 approvals 行として再要求を INSERT し、系列（要求・再要求・応答の全履歴）を証跡に残す／再要求で待機継続（waiting）。上限未到達の間は無限待機しない再要求ループとして進む
- **raises**: `ApprovalRetryExhausted`（expired 再要求が config.approval_retry_limit 到達（escalate → escalated — 呼出元が DU-01 経由で発火。AC-46-3）） ／ **pure**: no

- **DTO・値オブジェクト**: Binding(subject: str, operation: str, at: str) — frozen（束縛承認の 3 項目。at は UTC ISO 8601）／Decision(kind: Literal['pending','approved','rejected','expired'], approval_id: int, evidence_id: int | None, classification: str | None) — frozen。classification は ApprovalRejected 等の正規名／ApprovalTransport — 通知送出・応答取得の差替可能 interface（mock で approve/reject/timeout/binding 不一致を再現）
- **状態遷移**: approvals.decision: pending→approved／rejected／expired（decision 列の一方向確定 — loop_run の waiting/resume、task の failed/escalated への遷移は呼出元が DU-01 transition() 経由で発火）
- **DB read**: approvals／config／tasks ／ **DB write**: approvals／evidence
- **tx 境界**: request の INSERT＋（transport 送出は transaction 外 — 一時失敗は状態を巻き戻さず通知のみ再送）。approved 確定時は approval 証跡 INSERT と approvals.evidence_id 更新を単一 transaction（`_record_decision`）
- **pure／副作用端点**: binding 照合（3 項目完全一致）・decision→分類写像（承認設計 §3）は pure 関数。approvals/evidence 書込みと transport I/O が副作用端点
- **冪等性**: 同一 binding の要求は UNIQUE (task_id, binding_subject, binding_operation, binding_at) で既存行に収束。poll の再実行は approvals.decision の現在値から決定的に同じ Decision を返す（クラッシュ後は decision から再開 — 「承認されたはず」の推測禁止） ／ **retry/resume**: transport 一時失敗は通知のみ再送（状態不変 — FR-16）。再起動後は approvals.decision を正本に再開: pending=待機継続、approved=evidence 整合確認後に公開へ、rejected/expired=写像適用（s0-contract §3.3 waiting 行・承認設計 §6）
- **競合制御**: decision 更新は decision='pending' を条件に含む UPDATE（更新 0 行 = 既確定として現在値を再読 — 二重確定なし）。UNIQUE 制約が並行要求の最終防衛
- **ログ・証跡**: approval 証跡（approval_id・decision=approved・binding 3 項目 — approvals.evidence_id と相互整合）を DU-09 経由で記録。binding 不一致・rejected・expired・再要求系列は operation_log／構造化ログへ理由を記録
- **依存 API**: DU-09: record()／DU-01: transition()／DU-12: get()／DU-10: connect()
- **trace**: AC = AC-46-1 AC-46-2 AC-46-3 AC-46-4 ／ TC = TC-046 TC-GATE-06 TCC-46-1 TCC-46-2 TCC-46-3 TCC-46-4 ／ UT = test_connectors_approval.py::test_request_inserts_pending_and_notifies_binding test_connectors_approval.py::test_duplicate_request_unique_idempotent test_connectors_approval.py::test_poll_approved_records_evidence_atomically test_connectors_approval.py::test_binding_mismatch_response_invalid_keeps_waiting test_connectors_approval.py::test_rejected_classified_non_retryable_failure test_connectors_approval.py::test_rerequest_on_expired_new_row_series test_connectors_approval.py::test_rerequest_limit_reached_escalates ／ 機能別設計 = approval.md、external-operations.md、brand-isolation.md

## DU-19 `content/generate.py`（CMP-12）

### `def generate(plan: PlanInput, workspace: Path, rng_seed: int) -> GeneratedSource`

- **pre**: plan は承認済み企画（訴求・ターゲット・狙い）から組み立てた検証済み入力（plan_record 証跡と整合）／plan が参照する素材・テンプレートはすべて版管理済み（commit 固定）ソースのみ（FR-51 — 版管理外参照は拒否）／workspace は git workspace のパス（書出し先。外部ネットワーク I/O なし）／rng_seed は注入値（モジュール内 random 直呼び禁止 — 基本設計 §4）
- **post**: テンプレート＋種固定で決定的に生成し、同一入力＋同一 seed → 同一 SHA-256 の出力が得られる（AC-51-1・TC-NFR-02）／生成物は workspace 配下のファイルとしてのみ書き出され、DB・外部サービスへは一切書かない／GeneratedSource は出力パス一覧と出力 SHA-256 を持ち、後続の commit 固定（DU-20）へ渡る／失敗時は部分出力を残さない（temp へ生成→完成後に rename）
- **raises**: `UnversionedSourceRejected`（版管理外ソース・未 commit 参照からの生成要求（FR-51 — 成果物を一切作らず拒否））／`FatalError`（テンプレート欠落・plan 入力の型不整合（自動回復不可 — 局所失敗として代替発行可）） ／ **pure**: no

- **DTO・値オブジェクト**: PlanInput(plan_id: int, appeal: str, target: str, intent: str, template_ref: str, source_refs: tuple) — frozen。source_refs は commit 固定参照のみ／GeneratedSource(paths: tuple, sha256: str, rng_seed: int) — frozen。同一入力の再生成で同値
- **状態遷移**: なし
- **DB read**: なし ／ **DB write**: なし
- **tx 境界**: なし（DB 接触なし — ファイル書出しは temp→rename の原子的置換）
- **pure／副作用端点**: 生成本体（テンプレート展開・種固定乱数・hash 計算）は pure（同一入力→同一バイト列）。workspace へのファイル書出しだけが副作用端点。外部 I/O なし
- **冪等性**: 同一 plan・同一 seed の再実行は同一 SHA-256 の同一出力に収束（上書きは同値 — 差分ゼロ）。部分生成はコミットされない（temp 破棄） ／ **retry/resume**: クラッシュ後は再実行のみで復旧（決定性により前回と同一出力を再生成 — temp 断片は採用されず破棄）。リトライ判断は呼出元 microloop（verify_fail 系とは区別）
- **競合制御**: workspace は task 単位で専有（オーケストレータの lease が保証）。同一 workspace への並行生成は行わない前提を precondition で宣言
- **ログ・証跡**: 生成入力の fingerprint・rng_seed・出力 SHA-256 を構造化ログへ記録（NFR-2 — seed から再現可能）。commit_hash 証跡化は DU-20 link が担う
- **依存 API**: なし
- **trace**: AC = AC-51-1 AC-51-2 AC-51-3 AC-51-4 AC-51-5 ／ TC = TC-051 TC-NFR-02 TCC-51-1 TCC-51-2 TCC-51-3 TCC-51-4 TCC-51-5 ／ UT = test_content_generate.py::test_same_input_same_seed_same_sha256 test_content_generate.py::test_different_seed_different_output test_content_generate.py::test_unversioned_source_rejected_no_output test_content_generate.py::test_no_external_io_and_no_db_touch test_content_generate.py::test_crash_leaves_no_partial_output ／ 機能別設計 = campaign.md

## DU-20 `content/versioning.py`（CMP-12）

### `def commit_workspace(workspace: Path, repo: Path, message: str) -> str`

- **pre**: workspace は DU-19 の生成物を含む git workspace／repo は初期化済みリポジトリ（credential を含まない — 平文格納禁止）
- **post**: commit を実行し、40 又は 64 桁の 16 進 hash を検証して返す／commit 後の workspace 内容と hash は一対一（後続の review_pass はこの hash に束縛される）
- **raises**: `InvalidCommitHash`（得られた hash が 40/64 桁の 16 進でない（AC-54-3 — 拒否））／`FatalError`（git 実行失敗・repo 不整合（commit 不可は failed — WF-WP-1 ステップ 3）） ／ **pure**: no

### `def link(conn: Connection, task_id: int, repository: str, commit_hash: str, paths: list[str], clock: Clock) -> int`

- **pre**: commit_hash は 40 又は 64 桁（列 CHECK と二重検証）／repository・paths は payload_json の必須キーとして非空（s0-contract §2.1 commit_hash 行）
- **post**: commit_hash 証跡（kind=commit_hash、value=hash、payload={repository, commit_hash, paths}、commit_hash 列同値）を DU-09 record() 経由で INSERT し evidence_id を返す／同一 (task_id, kind, value) の再実行は UNIQUE により 1 行に収束する（AC-54-3 — 冪等）
- **raises**: `InvalidCommitHash`（40/64 桁以外の hash（例: 39 桁）での証跡化要求）／`GateRejected`（payload 必須キー欠落・kind 規則違反（DU-09 の検証で拒否 — 状態・DB 不変）） ／ **pure**: no

### `def restore(repo: Path, commit_hash: str, dest: Path) -> Path`

- **pre**: commit_hash は審査記録（review_pass 証跡）に束縛された hash／dest は空又は新規の復元先ディレクトリ
- **post**: commit_hash の checkout により審査時と同一内容のソースを dest へ復元しパスを返す（AC-54-1 — 審査記録からの成果物ソース復元）／repo 本体の作業ツリーを変更しない（read-only 抽出）
- **raises**: `InvalidCommitHash`（不正桁・16 進以外の hash 指定）／`FatalError`（hash が repo に存在しない・抽出失敗（復元不能の fail-close）） ／ **pure**: no

- **DTO・値オブジェクト**: なし
- **状態遷移**: なし
- **DB read**: evidence ／ **DB write**: evidence
- **tx 境界**: link の証跡 INSERT は DU-09 record() の単一 transaction。commit_workspace／restore は DB 接触なし（git I/O のみ）
- **pure／副作用端点**: hash 桁数・16 進検証は pure 関数。git 実行・ファイル復元・証跡 INSERT が副作用端点
- **冪等性**: 同一内容の commit_workspace 再実行は同一 tree の commit（no-op なら既存 hash 返却）。link は UNIQUE(task_id, kind, value) で 1 行に収束。restore は決定的（同一 hash → 同一内容） ／ **retry/resume**: クラッシュ後は commit の存在（git）と evidence 行（DB）を照合して未完了段のみ再実行（推測禁止 — 双方の実在確認が根拠）。git 一時失敗は再実行で回復
- **競合制御**: workspace/repo は task 単位で専有（lease が保証）。evidence は append-only＋UNIQUE で並行 link を吸収
- **ログ・証跡**: commit_hash 証跡（repository・commit_hash・paths）を DU-09 経由で記録。restore の実行（hash・dest）を構造化ログへ記録し、審査⇔ソースの追跡可能性（AC-54）を成立させる
- **依存 API**: DU-09: record()／DU-10: connect()
- **trace**: AC = AC-54-1 AC-54-2 AC-54-3 AC-54-4 AC-54-5 AC-55-1 AC-55-2 AC-55-3 AC-55-4 ／ TC = TC-054 TCC-54-1 TCC-54-2 TCC-54-3 TCC-54-4 TCC-54-5 TCC-55-1 TCC-55-2 TCC-55-3 TCC-55-4 ／ UT = test_content_versioning.py::test_commit_returns_valid_40_or_64_hex_hash test_content_versioning.py::test_link_records_commit_hash_evidence test_content_versioning.py::test_link_39_digit_hash_rejected test_content_versioning.py::test_link_rerun_converges_to_single_row test_content_versioning.py::test_restore_reproduces_reviewed_source ／ 機能別設計 = evidence.md、campaign.md

## DU-21 `measure/kpi.py`（CMP-13）

### `def create_node(conn: Connection, node: KpiNodeInput) -> int`

- **pre**: node.layer は 5 階層（exposure/micro_cv/conversion/relationship/revenue）のいずれか／node.metric_type は DU-07 check_metric_type を通過済みでも本 API 内で再度通す（DB CHECK と三重防御）／parent_node_id 指定時は同一 business_profile 内の既存ノード（越境親は拒否 — ブランド隔離設計 §3: KPI ツリーはプロファイル内で独立）
- **post**: 階層・媒体タグ・集計式（aggregation_formula の構文検証）を通過した kpi_nodes 行を INSERT し id を返す／node_key はプロファイル内一意（UNIQUE (business_profile_id, node_key)）／拒否時は行を一切作らない（AC-61-2）
- **raises**: `PaidMetricRejected`（metric_type が cac/roas/ad_spend（FR-23/61 — DB CHECK と二重））／`KpiNodeInvalid`（重複 node_key・越境親・未知 layer・集計式不整合（登録拒否 — 行を作らない）） ／ **pure**: no

### `def tree(conn: Connection, business_profile_id: int) -> list[KpiNode]`

- **pre**: business_profile_id は存在するプロファイル（スコープはこの引数で明示 — 横断集計 API は公開しない）
- **post**: 当該プロファイルの親子解決済みツリー（layer×medium の断面クエリ可能な形）を返す／最小ツリー（根ノードのみ）でも決定的に返る（AC-61-3）。他プロファイルのノードは含まれない
- **raises**: なし ／ **pure**: no

### `def archive_node(conn: Connection, node_id: int) -> None`

- **pre**: node_id は既存の kpi_nodes 行（DELETE は提供しない — 参照行は FK RESTRICT が保護）
- **post**: status を archived へ更新し、measurements・子ノードからの参照整合を保ったまま集計対象から外す（AC-61-3）
- **raises**: `FatalError`（node_id 不在（IntegrityError の境界正規化 — 業務層で IntegrityError 名は使わない）） ／ **pure**: no

- **DTO・値オブジェクト**: KpiNodeInput(business_profile_id: int, parent_node_id: int | None, node_key: str, name: str, layer: str, medium: str, metric_type: str, aggregation_formula: str, target: dict | None) — frozen／KpiNode(id: int, node_key: str, layer: str, medium: str, metric_type: str, children: tuple) — frozen。親子解決済み
- **状態遷移**: なし
- **DB read**: kpi_nodes／business_profiles／config ／ **DB write**: kpi_nodes
- **tx 境界**: create_node／archive_node は各々単一 transaction（検証→INSERT/UPDATE→コミット）。tree は読み取りのみ
- **pure／副作用端点**: layer・metric_type・集計式・親子整合の検証は pure 関数。kpi_nodes の読み書きだけが副作用端点
- **冪等性**: 同一 (business_profile_id, node_key) の再登録は UNIQUE で拒否（既存行の再利用は呼出元判断 — 黙って上書きしない）。archive_node は再実行で同値（冪等） ／ **retry/resume**: 登録拒否は状態を残さないため再開不要。クラッシュ後は kpi_nodes の実在で判断（transaction 単位で全て入るか入らないか）
- **競合制御**: UNIQUE (business_profile_id, node_key) が並行登録の最終防衛。archive は status 列のみの UPDATE で FK 競合なし
- **ログ・証跡**: 登録・拒否（PaidMetricRejected/KpiNodeInvalid の事由）・archive を構造化ログへ記録。KPI 目標↔計測ペア（pair_kpi_measure）の成立は S1 のレビュー系が担い、本 DU は登録正本のみ
- **依存 API**: DU-07: check_metric_type()／DU-10: connect()
- **trace**: AC = AC-61-1 AC-61-2 AC-61-3 AC-61-4 AC-61-5 AC-61-6 ／ TC = TC-023 TCC-61-1 TCC-61-2 TCC-61-3 TCC-61-4 TCC-61-5 TCC-61-6 ／ UT = test_measure_kpi.py::test_create_node_all_five_layers_grounded test_measure_kpi.py::test_paid_metric_type_rejected test_measure_kpi.py::test_duplicate_node_key_invalid test_measure_kpi.py::test_cross_profile_parent_rejected test_measure_kpi.py::test_tree_resolves_hierarchy_per_profile test_measure_kpi.py::test_archive_keeps_reference_integrity ／ 機能別設計 = kpi-handoff.md、brand-isolation.md

## DU-22 `measure/fetch.py`（CMP-13）

### `def fetch(conn: Connection, task_id: int, route: Route, property_id: str, period: Period, out_dir: Path, clock: Clock) -> FetchResult`

- **pre**: route は DU-13 resolve() が返した経路（GA4 Data API 第一 — ADR-006。API 阻害時のみブラウザエクスポートへ一時フォールバック）／credential は読取専用（DU-14 get_credential）で、check_endpoint により property/endpoint 突合済み／property_id は config の非秘匿値と一致（対象 property 一致ゲート — WF-MEAS-1 ステップ 1）／書込み系 operation は組み立て時点で拒否される（read-only 保証）
- **post**: 取得物（CSV/xlsx 又は API 応答）を out_dir へ保存し、即 SHA-256 で固定する（投入前の改竄検出基準値）／operation_log 証跡（service/operation/external_operation_id 又は mock operation ID/request_fingerprint/result）を投入より先に DU-09 経由で記録する（AC-62-1 — 取得証跡が投入前に記録）／ブラウザフォールバック時は screenshot 証跡も取得する（DU-15 経由）。いずれの経路も同一の evidence 契約に収束／読取り系のためレート節度（NFR-7）の対象外・external_operations 行は作らない。mock/dry-run は fixture を返し予定 request の fingerprint を operation_log に残す／実 GA4 への書込みは存在しない（環境契約 §6 — 読取専用 API のみ組み立て可能）
- **raises**: `GateRejected`（書込み系 operation の組立要求・property 不一致（read-only 保証の fail-close — 外部呼出 0 回））／`RetryableError`（接続・応答 timeout、外部 429（読取り再試行可 — retry 上限は呼出元））／`SecretUnavailable`（読取 credential 未投入・失効（外部操作を開始せず escalate 誘導 — DU-14 から透過））／`CredentialEndpointMismatch`（credential と property/endpoint の不正組合せ（接続前拒否 — DU-14 から透過））／`FatalError`（本番取得不能の確定（公開を巻き戻さず当該 T-MEAS を failed — WF-MEAS-1 ステップ 1）） ／ **pure**: no

- **DTO・値オブジェクト**: Period(start: str, end: str) — frozen。UTC ISO 8601、end >= start／FetchResult(file_path: Path, file_hash: str, route_used: str, operation_log_evidence_id: int, screenshot_evidence_id: int | None) — frozen。file_hash は取得直後に固定した SHA-256
- **状態遷移**: なし
- **DB read**: config／tasks ／ **DB write**: evidence
- **tx 境界**: operation_log／screenshot 証跡の INSERT は DU-09 record() の各単一 transaction（取得ファイル保存はファイル系 — temp→rename）。業務状態の遷移は行わない
- **pure／副作用端点**: request 組み立て・read-only 判定・fingerprint/hash 計算は pure 関数。GA4 I/O・ファイル保存・証跡 INSERT が副作用端点
- **冪等性**: 読取のみで外部副作用なし — 同一 property・同一 period の再取得は安全。file_hash 固定により同一エクスポートの再取得は同一 hash に収束し、下流 ingest の UNIQUE が重複投入を防ぐ（AC-62-1） ／ **retry/resume**: timeout・429 は再試行可（読取りのため送信後照合は不要）。クラッシュ後は out_dir の取得物と operation_log 証跡の実在を照合し、証跡未記録なら取得からやり直す（推測禁止）
- **競合制御**: 取得は task 単位で専有（lease が保証）。out_dir への書出しは temp→rename で部分ファイルを公開しない
- **ログ・証跡**: operation_log 証跡（投入前に必ず記録 — 秘匿値なし・読取専用の result）と、フォールバック時の screenshot 証跡を DU-09 経由で記録。経路選択（api/browser）と拒否事由を構造化ログへ記録
- **依存 API**: DU-13: resolve()／DU-14: get_credential()／DU-14: check_endpoint()／DU-15: launch()／DU-15: screenshot()／DU-09: record()／DU-12: get()／DU-10: connect()
- **trace**: AC = AC-62-1 AC-62-2 AC-62-3 AC-62-4 AC-62-5 AC-62-6 AC-62-7 ／ TC = TCC-62-1 TCC-62-2 TCC-62-3 TCC-62-4 TCC-62-5 TCC-62-6 TCC-62-7 ／ UT = test_measure_fetch.py::test_api_first_route_selected test_measure_fetch.py::test_browser_fallback_converges_same_evidence_contract test_measure_fetch.py::test_write_operation_assembly_rejected test_measure_fetch.py::test_property_mismatch_rejected_before_call test_measure_fetch.py::test_hash_fixed_and_operation_log_before_ingest test_measure_fetch.py::test_dry_run_records_fingerprint_only ／ 機能別設計 = kpi-handoff.md、external-operations.md

## DU-23 `measure/parse.py`（CMP-13）

### `def parse(raw: Path, schema: SourceSchema) -> ParseResult`

- **pre**: raw は DU-22 で SHA-256 固定済みの取得物／schema は取得元（GA4 CSV/xlsx/API 応答）の列・型定義
- **post**: schema/type 検証を通過した正常行と、壊れた行の隔離ファイル（正常行と分離）を返す（AC-62-2 — 部分破損は正常行のみ継続）／隔離件数・正常件数を ParseResult に含め、件数は証跡化（measurement 証跡 payload の row_count）に使う／PV 以外・有料指標系の列は取り込まない（S0 スコープ — 有料指標型は下流 DU-21/DU-07 でも拒否）
- **raises**: `ImportSourceInvalid`（取得物の全行破損・schema 全不適合（全体拒否 — non_retryable_failure → failed。部分破損は隔離＋正常継続で raise しない）） ／ **pure**: no

### `def ingest(conn: Connection, rows: list[MeasurementRow], raw: Path, expected_hash: str, kpi_node_id: int, task_id: int, evidence_id: int, clock: Clock) -> int`

- **pre**: expected_hash は取得時に固定済みの証跡値（measurement 証跡の file_hash）／kpi_node_id・task_id・evidence_id は実在行（FK 不能は投入前に検査して拒否）／kpi_node の metric_type は非有料（DU-07 check_metric_type で投入前に再検査 — DB CHECK と二重）／clock は注入（imported_at の供給源 — datetime.now() 直呼び禁止）
- **post**: 投入前に raw の SHA-256 を再計算し expected_hash と一致する場合のみ投入する（改竄・取り違えの fail-close）／全行を単一 transaction で measurements へ INSERT し、投入行数を返す。途中失敗は全 rollback（部分コミットを残さない — AC-62-3）／UNIQUE (kpi_node_id, period_start, period_end, dimensions_json) により同一エクスポートの再投入は差分ゼロで冪等完了する（AC-62-1）／空エクスポートは 0 行投入・証跡のみ残して正常終了する（AC-62-3）
- **raises**: `FatalError`（raw の再計算 hash が expected_hash と不一致（証跡固定値との乖離 — 投入せず拒否））／`GateRejected`（FK 不能（kpi_node/task/evidence 不在）・有料指標ノードへの投入要求（投入前拒否 — DB 不変）） ／ **pure**: no

- **DTO・値オブジェクト**: SourceSchema(columns: tuple, types: dict, source_kind: str) — frozen。取得元別の列・型定義／MeasurementRow(period_start: str, period_end: str, value: float, unit: str, dimensions: dict) — frozen。検証済み正常行／ParseResult(rows: tuple, quarantined_path: Path | None, quarantined_count: int, total_count: int) — frozen。正常行と隔離の分離結果
- **状態遷移**: なし
- **DB read**: kpi_nodes／evidence／tasks ／ **DB write**: measurements
- **tx 境界**: ingest は BEGIN → 事前検査（hash 再計算・FK・metric_type）→ 全行 INSERT → COMMIT の単一 transaction。途中失敗は全 rollback。parse は DB 接触なし
- **pure／副作用端点**: 行検証・型変換・hash 再計算は pure 関数。隔離ファイル書出しと measurements INSERT が副作用端点
- **冪等性**: parse は決定的（同一 raw・schema → 同一結果）。ingest は UNIQUE (kpi_node_id, period_start, period_end, dimensions_json) により再実行が差分ゼロに収束（クラッシュ後の再実行で一括投入 — AC-62-3） ／ **retry/resume**: クラッシュ分は transaction rollback で吸収され部分コミットが残らない。再開は同一 raw（hash 一致確認済み）の再 parse→再 ingest のみで復旧し、リモート照合は不要（外部書込みなし）
- **競合制御**: 投入は task 単位で直列（lease が保証）。UNIQUE 制約が並行投入の最終防衛。隔離ファイルは task 別パスで衝突しない
- **ログ・証跡**: measurement 証跡（source・file_hash・period_start/end・row_count — DU-09 経由は取得側で記録済みの evidence_id と FK 接続）。隔離件数・投入件数・rollback 事由を構造化ログへ記録し、imported_at は clock から供給
- **依存 API**: DU-07: check_metric_type()／DU-09: record()／DU-10: connect()
- **trace**: AC = AC-62-1 AC-62-2 AC-62-3 AC-62-4 AC-62-5 AC-62-6 AC-62-7 ／ TC = TC-061 TC-062 TCC-62-1 TCC-62-2 TCC-62-3 TCC-62-4 TCC-62-5 TCC-62-6 TCC-62-7 ／ UT = test_measure_parse.py::test_partial_corruption_quarantined_normal_rows_continue test_measure_parse.py::test_all_rows_corrupt_import_source_invalid test_measure_parse.py::test_ingest_hash_mismatch_rejected_no_insert test_measure_parse.py::test_ingest_single_transaction_full_rollback test_measure_parse.py::test_ingest_rerun_idempotent_zero_delta test_measure_parse.py::test_fk_missing_rejected_before_insert test_measure_parse.py::test_empty_export_zero_rows_evidence_only test_measure_parse.py::test_imported_at_supplied_by_clock ／ 機能別設計 = kpi-handoff.md、evidence.md
