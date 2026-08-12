---
artifact_id: L3-S0-CONTRACT
lifecycle_status: confirmed
slice: S0
---

# S0 実行契約 v0.1

> status: **confirmed**（2026-07-31 PO 承認 — 要件定義完遂指示。AI 起草）
> pair: [verification-design_v0.1.md §2〜§5](../verification/verification-design_v0.1.md)（検証設計③ — HELIX 式 ①↔③ 文書ペア）
> 上位文書: [requirements_v0.1.md](functional/requirements_v0.1.md)（FR/NFR/AC/S0）／[loop-task-workflow_v0.1.md](../../L1-business-requirements/canonical/loop-task-workflow_v0.1.md)（LP/T/WF）／[br-backbone_v0.1.md](../../L1-business-requirements/canonical/br-backbone_v0.1.md)（BR 背骨）
> 位置づけ: S0 の実装者・テスト・運用者が共通に従う、SQLite 正準スキーマ、状態機械、WF 実行、移行および環境の契約。
> **DDL・evidence 型契約・状態遷移表は本書が正準**（上位文書は要約参照）。それ以外の要求内容で
> 上位文書と矛盾した場合は上位文書を優先し、本書を改訂する。

---

## 1. 適用範囲と共通規約

- DB 正本は SQLite である。接続開始時に必ず `PRAGMA foreign_keys = ON` を実行する。SQLite の FK は接続単位で有効化するため、これを省略した接続は不正な実行環境とする。
- 接続開始時に `PRAGMA journal_mode = WAL` と `PRAGMA busy_timeout`（値は `config.sqlite_busy_timeout_ms`）を設定する。書込みは kernel の単一 writer 経由とし、`SQLITE_BUSY` は busy_timeout 内の待機→タイムアウトで retryable_failure として扱う（書込み競合方針）。
- 時刻は UTC の ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`) 文字列、ハッシュは SHA-256 の 64 桁 16 進文字列、JSON は UTF-8 の RFC 8259 JSON とする。
- `*_id` は `INTEGER` の不透明な主キーであり、外部サービス ID・credential・secret を格納しない。外部 I/O のローカル正本 ID は `external_operations.id`、`operation_log` 側の束縛は `evidence.external_operation_row_id` とする。provider が返す ID は `external_operations.external_operation_id` / `evidence.external_operation_id` に秘匿情報を除いて任意記録し、存在時だけ両行の一致を強制する。
- `external_operations` は実行した外部 `read` / `write` だけの操作台帳である。pre-call ガード拒否、mock、dry-run は process logger のみとし、`external_operations` / `operation_log` とも 0 行とする。`policy_category` は `external_read` / `content_publish` / `review_sync` / `approval_notification` / `approved_paid_operation` の閉集合で、`external_read` だけが read、他は write とする。read の `rate_scope` は NULL、write は空でない lowercase `[a-z0-9_]+` の canonical policy key を必須とし、provider 名や大小文字・記号を含む alias を使わない。実 I/O は `execution_mode = actual` の prepared 行を作り、**prepared → sent → confirmed / rejected / unknown** の順で遷移させる。prepared・sent は外部 call 前に各々コミットし、call 後は sent 行の結果メタデータを NULL から一度だけ記録する。対応 `operation_log` の INSERT trigger が全束縛を検証し、その INSERT 文の中で final status + `evidence_id` を更新するため、片側だけを commit できない。write は `request_sequence=1` と一意 idempotency key を必須とし correlation key にも同値を用いる。read は idempotency key を持たず、同一 `(task_id, operation, request_hash)` の初回を sequence 1、直前回が final の場合だけ `MAX+1` とし、`read:<task_id>:<request_hash>:<request_sequence>` の決定的 correlation key を用いる。gap・再利用・未確定前回を飛ばす新規 read は拒否する。request/response hash は lowercase 64 桁 hex、prepared/sent/confirmed 時刻は実在日時の UTC `YYYY-MM-DDTHH:MM:SSZ` に固定する。1 実 I/O = 1 external row = 1 operation_log を双方向 FK と両側 UNIQUE で束縛し、final 行は UPDATE / DELETE しない。
- 「秘匿化済み構造化拒否ログ／実行ログ」は DB の業務証跡型ではなく process logger が出力する JSON event とする。必須キーは `error_type`、`target_id`、`reason`、`occurred_at`、`correlation_id`。secret、credential、本文実体、未マスク PII を含めない。CI では job log artifact、runtime では所定の runtime log sink に保存し、状態遷移拒否は別途 `state_transitions.guard_result = rejected`、外部操作は `operation_log` に記録する。
- `tasks.verifier_agent_id` は全タスクで必須とする。T-REVIEW の verifier は critic 以外の `gate-engine` 等を割り当てる。これにより自己審査禁止を NULL の三値論理に委ねない。
- 上流戦略正本（`strategic_briefs`。S1 以降に追加する上流モデル群も同様）は **上流ループの改善工程のみが新版 INSERT で更新できる**。下流ループ・媒体コネクタ・計測処理は上流戦略正本へ書き込めず、下流からの還流は `tactical_learning_packets`（append-only）の提出のみとする。上流正本の変更は上書きではなく `supersedes_id` を持つ新版行の作成とし、内容列の UPDATE と DELETE は保護トリガが常時拒否する。下流 loop_run（`loop_kind = 'lower'`）は有効な strategic_brief の id と digest を保持しない限り開始できない（[strategy-learning-contract_v0.1.md](strategy/strategy-learning-contract_v0.1.md) が契約正本）。
- 自己審査禁止の判定単位は **principal**（`agents.principal` = 実体となるモデル・人・サービス）である。author と verifier は agent 行の差だけでなく principal が異なることを kernel が claim ガードで検査する。実行の系譜は `agent_executions`（execution = セッション/run、親子関係）に記録し、`agent_executions.principal` は複合 FK `(agent_id, principal)` で `agents` と一致を強制する。lease は execution 単位で保持し、**task を claim できる execution は当該 task の `author_agent_id` に属するものに限る**（lease 失効後の再 claim も author agent の新 execution のみ。kernel がガードで拒否）。

## 2. 正準 DDL（FR-71）

以下の順序で適用する。`schema_version`（FR-72 の移行管理）と `state_transitions`（NFR-5 の状態遷移ログ）は
FR-71 の 23 業務テーブル（当初 19 ＋レビュー是正で追加した `agent_executions`・`external_operations`
＋上流戦略再強化で追加した `strategic_briefs`・`tactical_learning_packets`）とは
別のインフラテーブルである。append-only テーブル（`config`・`evidence`・`state_transitions`・
`strategic_briefs`（内容列）・`tactical_learning_packets`）は
保護トリガで UPDATE/DELETE を拒否し、migration 0001 はトリガ込みで本 DDL と等価とする。
`external_operations` は policy/rate/sequence を含む束縛列の不変、合法遷移、final 時の双方向 1:1 operation_log、final 不変、DELETE 禁止を保護トリガで強制する。`published_url` は同じ task の confirmed `content_publish` operation とその operation_log へローカル ID で 1:1 束縛し、`spend_ledger` は approved paid operation の charge と厳密 reversal だけを append-only で受理する。
一部の FK は後続テーブルへの前方参照を含む（SQLite は DML 時に検証するため適用は成功する）。
適用後の `PRAGMA foreign_key_check` 成功を契約検証（§8）で必須とする。

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE schema_version (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL,
  migration_name TEXT NOT NULL UNIQUE,
  checksum_sha256 TEXT NOT NULL CHECK (length(checksum_sha256) = 64),
  applied_by TEXT NOT NULL
);

CREATE TABLE state_transitions (
  id INTEGER PRIMARY KEY,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('loop_run', 'task')),
  entity_id INTEGER NOT NULL,
  from_state TEXT NOT NULL,
  event TEXT NOT NULL,
  to_state TEXT NOT NULL,
  guard_result TEXT NOT NULL CHECK (guard_result IN ('passed', 'rejected')),
  details_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(details_json)),
  created_at TEXT NOT NULL,
  created_by_agent_id INTEGER,
  FOREIGN KEY (created_by_agent_id) REFERENCES agents(id) ON DELETE RESTRICT
);

CREATE TABLE business_profiles (
  id INTEGER PRIMARY KEY,
  profile_key TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'archived')),
  profile_json TEXT NOT NULL CHECK (json_valid(profile_json)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE agents (
  id INTEGER PRIMARY KEY,
  agent_key TEXT NOT NULL UNIQUE,
  principal TEXT NOT NULL,
  role TEXT NOT NULL,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'disabled')),
  created_at TEXT NOT NULL,
  UNIQUE (id, principal)
);

CREATE TABLE agent_executions (
  id INTEGER PRIMARY KEY,
  agent_id INTEGER NOT NULL,
  principal TEXT NOT NULL,
  model_version TEXT,
  session_ref TEXT,
  parent_execution_id INTEGER,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  FOREIGN KEY (agent_id, principal) REFERENCES agents(id, principal) ON DELETE RESTRICT,
  FOREIGN KEY (parent_execution_id) REFERENCES agent_executions(id) ON DELETE RESTRICT
);

CREATE TABLE brand_plans (
  id INTEGER PRIMARY KEY,
  business_profile_id INTEGER NOT NULL,
  version INTEGER NOT NULL,
  horizon_start TEXT NOT NULL,
  horizon_end TEXT NOT NULL,
  north_star_kpi TEXT NOT NULL,
  plan_json TEXT NOT NULL CHECK (json_valid(plan_json)),
  status TEXT NOT NULL CHECK (status IN ('draft', 'approved', 'superseded')),
  created_at TEXT NOT NULL,
  created_by_agent_id INTEGER NOT NULL,
  FOREIGN KEY (business_profile_id) REFERENCES business_profiles(id) ON DELETE RESTRICT,
  FOREIGN KEY (created_by_agent_id) REFERENCES agents(id) ON DELETE RESTRICT,
  UNIQUE (business_profile_id, version)
);

CREATE TABLE action_plans (
  id INTEGER PRIMARY KEY,
  brand_plan_id INTEGER NOT NULL,
  business_profile_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  medium TEXT NOT NULL,
  objective TEXT NOT NULL,
  target_json TEXT NOT NULL CHECK (json_valid(target_json)),
  status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'completed', 'archived')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (brand_plan_id) REFERENCES brand_plans(id) ON DELETE RESTRICT,
  FOREIGN KEY (business_profile_id) REFERENCES business_profiles(id) ON DELETE RESTRICT
);

CREATE TABLE sprints (
  id INTEGER PRIMARY KEY,
  action_plan_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  medium TEXT NOT NULL,
  starts_at TEXT NOT NULL,
  ends_at TEXT NOT NULL,
  kpi_target_json TEXT NOT NULL CHECK (json_valid(kpi_target_json)),
  status TEXT NOT NULL CHECK (status IN ('planned', 'active', 'reviewing', 'completed', 'blocked')),
  created_at TEXT NOT NULL,
  FOREIGN KEY (action_plan_id) REFERENCES action_plans(id) ON DELETE RESTRICT,
  CHECK (ends_at >= starts_at)
);

CREATE TABLE workflows (
  id INTEGER PRIMARY KEY,
  workflow_key TEXT NOT NULL,
  name TEXT NOT NULL,
  task_type TEXT NOT NULL CHECK (
    length(task_type) > 0
    AND task_type NOT GLOB '*[^A-Za-z0-9_-]*'),
  version INTEGER NOT NULL,
  definition_json TEXT NOT NULL CHECK (json_valid(definition_json)),
  required_evidence_json TEXT NOT NULL CHECK (json_valid(required_evidence_json)),
  status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'retired')),
  created_at TEXT NOT NULL,
  UNIQUE (workflow_key, version)
);

CREATE TABLE strategic_briefs (
  id INTEGER PRIMARY KEY,
  brief_key TEXT NOT NULL,
  version INTEGER NOT NULL CHECK (version >= 1),
  strategic_choice_id TEXT NOT NULL,
  segment_context_id TEXT NOT NULL,
  value_hypothesis_id TEXT NOT NULL,
  desired_recognition_change TEXT NOT NULL,
  tactical_objective TEXT NOT NULL,
  media_role TEXT NOT NULL,
  message_hypothesis TEXT NOT NULL,
  prohibited_patterns_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(prohibited_patterns_json)),
  measurement_plan_json TEXT NOT NULL CHECK (json_valid(measurement_plan_json)),
  valid_from TEXT NOT NULL,
  valid_until TEXT,
  digest TEXT NOT NULL CHECK (length(digest) = 64),
  status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'superseded', 'retired')),
  supersedes_id INTEGER,
  created_at TEXT NOT NULL,
  FOREIGN KEY (supersedes_id) REFERENCES strategic_briefs(id) ON DELETE RESTRICT,
  UNIQUE (brief_key, version)
);

CREATE TABLE loop_runs (
  id INTEGER PRIMARY KEY,
  parent_loop_run_id INTEGER,
  sprint_id INTEGER,
  workflow_id INTEGER,
  strategic_brief_id INTEGER,
  strategic_brief_digest TEXT CHECK (strategic_brief_digest IS NULL OR length(strategic_brief_digest) = 64),
  loop_kind TEXT NOT NULL CHECK (loop_kind IN ('upper', 'lower', 'micro')),
  loop_type TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('pending', 'running', 'waiting', 'completed', 'failed', 'escalated', 'cancelled')),
  retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
  idempotency_key TEXT NOT NULL UNIQUE,
  resume_token TEXT,
  started_at TEXT,
  completed_at TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (parent_loop_run_id) REFERENCES loop_runs(id) ON DELETE RESTRICT,
  FOREIGN KEY (sprint_id) REFERENCES sprints(id) ON DELETE RESTRICT,
  FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE RESTRICT,
  FOREIGN KEY (strategic_brief_id) REFERENCES strategic_briefs(id) ON DELETE RESTRICT,
  CHECK ((loop_kind = 'upper' AND parent_loop_run_id IS NULL)
      OR (loop_kind IN ('lower', 'micro') AND parent_loop_run_id IS NOT NULL)),
  CHECK (loop_kind != 'lower'
      OR (strategic_brief_id IS NOT NULL AND strategic_brief_digest IS NOT NULL))
);

CREATE TABLE tactical_learning_packets (
  id INTEGER PRIMARY KEY,
  packet_key TEXT NOT NULL UNIQUE,
  packet_kind TEXT NOT NULL CHECK (packet_kind IN ('learning', 'failure')),
  loop_run_id INTEGER NOT NULL UNIQUE,
  strategic_brief_id INTEGER NOT NULL,
  strategic_brief_digest TEXT NOT NULL CHECK (length(strategic_brief_digest) = 64),
  observations_json TEXT NOT NULL CHECK (json_valid(observations_json)),
  metrics_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(metrics_json)),
  qualitative_signals_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(qualitative_signals_json)),
  anomalies_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(anomalies_json)),
  hypothesis_result TEXT CHECK (hypothesis_result IS NULL OR hypothesis_result IN ('supported', 'weakened', 'rejected', 'inconclusive')),
  target_hypothesis_ids_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(target_hypothesis_ids_json)),
  assessment_reason TEXT,
  causal_interpretation TEXT,
  alternative_explanations_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(alternative_explanations_json)),
  failure_fact TEXT,
  reproduction_conditions TEXT,
  recovery_conditions TEXT,
  confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
  evidence_ids_json TEXT NOT NULL CHECK (json_valid(evidence_ids_json)),
  proposed_revision_targets_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(proposed_revision_targets_json)),
  recommended_next_action TEXT NOT NULL CHECK (recommended_next_action IN ('continue', 'modify_tactic', 'request_strategy_review', 'stop')),
  created_at TEXT NOT NULL,
  FOREIGN KEY (loop_run_id) REFERENCES loop_runs(id) ON DELETE RESTRICT,
  FOREIGN KEY (strategic_brief_id) REFERENCES strategic_briefs(id) ON DELETE RESTRICT,
  CHECK ((packet_kind = 'learning'
          AND causal_interpretation IS NOT NULL AND hypothesis_result IS NOT NULL
          AND assessment_reason IS NOT NULL)
      OR (packet_kind = 'failure'
          AND failure_fact IS NOT NULL AND reproduction_conditions IS NOT NULL
          AND recovery_conditions IS NOT NULL AND causal_interpretation IS NULL))
);

CREATE TABLE tasks (
  id INTEGER PRIMARY KEY,
  loop_run_id INTEGER NOT NULL,
  parent_task_id INTEGER,
  workflow_id INTEGER NOT NULL,
  task_type TEXT NOT NULL CHECK (
    length(task_type) > 0
    AND task_type NOT GLOB '*[^A-Za-z0-9_-]*'),
  author_agent_id INTEGER NOT NULL,
  verifier_agent_id INTEGER NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('pending', 'in_progress', 'verifying', 'done', 'failed', 'escalated')),
  step_key TEXT NOT NULL,
  attempt INTEGER NOT NULL DEFAULT 1 CHECK (attempt >= 1),
  retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
  idempotency_key TEXT NOT NULL UNIQUE,
  lease_owner_execution_id INTEGER,
  lease_expires_at TEXT,
  heartbeat_at TEXT,
  row_version INTEGER NOT NULL DEFAULT 0 CHECK (row_version >= 0),
  expected_output_kind TEXT NOT NULL,
  input_json TEXT NOT NULL CHECK (json_valid(input_json)),
  output_json TEXT CHECK (output_json IS NULL OR json_valid(output_json)),
  failure_code TEXT,
  failure_detail TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  FOREIGN KEY (loop_run_id) REFERENCES loop_runs(id) ON DELETE RESTRICT,
  FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE RESTRICT,
  FOREIGN KEY (author_agent_id) REFERENCES agents(id) ON DELETE RESTRICT,
  FOREIGN KEY (verifier_agent_id) REFERENCES agents(id) ON DELETE RESTRICT,
  FOREIGN KEY (lease_owner_execution_id) REFERENCES agent_executions(id) ON DELETE RESTRICT,
  CHECK (author_agent_id != verifier_agent_id),
  UNIQUE (loop_run_id, step_key, attempt)
);

CREATE TABLE external_operations (
  id INTEGER PRIMARY KEY,
  task_id INTEGER NOT NULL,
  service TEXT NOT NULL,
  operation TEXT NOT NULL,
  effect TEXT NOT NULL CHECK (effect IN ('read', 'write')),
  policy_category TEXT NOT NULL CHECK (policy_category IN (
    'external_read', 'content_publish', 'review_sync',
    'approval_notification', 'approved_paid_operation')),
  rate_scope TEXT,
  execution_mode TEXT NOT NULL CHECK (execution_mode = 'actual'),
  target_endpoint TEXT NOT NULL,
  idempotency_key TEXT UNIQUE,
  correlation_key TEXT NOT NULL UNIQUE,
  request_hash TEXT NOT NULL CHECK (
    length(request_hash) = 64 AND request_hash NOT GLOB '*[^0-9a-f]*'),
  request_sequence INTEGER NOT NULL CHECK (request_sequence >= 1),
  status TEXT NOT NULL CHECK (status IN ('prepared', 'sent', 'confirmed', 'rejected', 'unknown')),
  external_operation_id TEXT,
  remote_object_id TEXT,
  response_hash TEXT CHECK (response_hash IS NULL OR (
    length(response_hash) = 64 AND response_hash NOT GLOB '*[^0-9a-f]*')),
  evidence_id INTEGER UNIQUE,
  prepared_at TEXT NOT NULL,
  sent_at TEXT,
  finalized_at TEXT,
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE RESTRICT,
  UNIQUE (task_id, effect, operation, request_hash, request_sequence),
  CHECK ((policy_category = 'external_read' AND effect = 'read')
      OR (policy_category IN ('content_publish', 'review_sync',
                              'approval_notification', 'approved_paid_operation')
          AND effect = 'write')),
  CHECK ((effect = 'read' AND rate_scope IS NULL)
      OR (effect = 'write'
          AND rate_scope IS NOT NULL
          AND length(rate_scope) > 0
          AND rate_scope NOT GLOB '*[^a-z0-9_]*')),
  CHECK ((effect = 'write'
          AND idempotency_key IS NOT NULL
          AND length(idempotency_key) > 0
          AND request_sequence = 1
          AND correlation_key = idempotency_key)
      OR (effect = 'read'
          AND idempotency_key IS NULL
          AND correlation_key = printf('read:%d:%s:%d', task_id, request_hash, request_sequence))),
  CHECK (length(prepared_at) = 20
      AND prepared_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'
      AND COALESCE(strftime('%Y-%m-%dT%H:%M:%SZ', prepared_at, '+0 seconds') = prepared_at, 0)),
  CHECK (sent_at IS NULL OR (
      length(sent_at) = 20
      AND sent_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'
      AND COALESCE(strftime('%Y-%m-%dT%H:%M:%SZ', sent_at, '+0 seconds') = sent_at, 0)
      AND sent_at >= prepared_at)),
  CHECK (finalized_at IS NULL OR (
      sent_at IS NOT NULL
      AND length(finalized_at) = 20
      AND finalized_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'
      AND COALESCE(strftime('%Y-%m-%dT%H:%M:%SZ', finalized_at, '+0 seconds') = finalized_at, 0)
      AND finalized_at >= sent_at))
);

CREATE TABLE pair_plan_quality (
  id INTEGER PRIMARY KEY,
  plan_id INTEGER NOT NULL,
  review_task_id INTEGER NOT NULL,
  review_evidence_id INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('passed', 'revoked')),
  created_at TEXT NOT NULL,
  FOREIGN KEY (plan_id) REFERENCES action_plans(id) ON DELETE RESTRICT,
  FOREIGN KEY (review_task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  FOREIGN KEY (review_evidence_id) REFERENCES evidence(id) ON DELETE RESTRICT,
  UNIQUE (plan_id, review_evidence_id)
);

CREATE TABLE evidence (
  id INTEGER PRIMARY KEY,
  task_id INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('plan_record', 'commit_hash', 'review_pass', 'published_url', 'measurement', 'screenshot', 'file_hash', 'approval', 'operation_log', 'dashboard')),
  value TEXT NOT NULL,
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
  asset_id INTEGER,
  commit_hash TEXT,
  external_operation_row_id INTEGER,
  operation_log_evidence_id INTEGER UNIQUE,
  external_operation_id TEXT,
  file_path TEXT,
  file_hash TEXT,
  created_at TEXT NOT NULL,
  created_by_agent_id INTEGER,
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE RESTRICT,
  FOREIGN KEY (external_operation_row_id) REFERENCES external_operations(id) ON DELETE RESTRICT,
  FOREIGN KEY (operation_log_evidence_id) REFERENCES evidence(id) ON DELETE RESTRICT,
  FOREIGN KEY (created_by_agent_id) REFERENCES agents(id) ON DELETE RESTRICT,
  UNIQUE (task_id, kind, value),
  CHECK ((kind = 'operation_log'
          AND external_operation_row_id IS NOT NULL
          AND operation_log_evidence_id IS NULL)
      OR (kind = 'published_url'
          AND external_operation_row_id IS NOT NULL
          AND operation_log_evidence_id IS NOT NULL
          AND asset_id IS NOT NULL)
      OR (kind NOT IN ('operation_log', 'published_url')
          AND external_operation_row_id IS NULL
          AND operation_log_evidence_id IS NULL)),
  CHECK (commit_hash IS NULL OR length(commit_hash) IN (40, 64)),
  CHECK (file_hash IS NULL OR length(file_hash) = 64)
);

CREATE UNIQUE INDEX evidence_operation_log_external_row_one
ON evidence(external_operation_row_id)
WHERE kind = 'operation_log';

CREATE UNIQUE INDEX evidence_published_url_external_row_one
ON evidence(external_operation_row_id)
WHERE kind = 'published_url';

CREATE TABLE kpi_nodes (
  id INTEGER PRIMARY KEY,
  business_profile_id INTEGER NOT NULL,
  parent_node_id INTEGER,
  node_key TEXT NOT NULL,
  name TEXT NOT NULL,
  layer TEXT NOT NULL CHECK (layer IN ('exposure', 'micro_cv', 'conversion', 'relationship', 'revenue')),
  medium TEXT NOT NULL,
  metric_type TEXT NOT NULL CHECK (metric_type NOT IN ('cac', 'roas', 'ad_spend')),
  aggregation_formula TEXT NOT NULL,
  target_json TEXT CHECK (target_json IS NULL OR json_valid(target_json)),
  status TEXT NOT NULL CHECK (status IN ('active', 'archived')),
  FOREIGN KEY (business_profile_id) REFERENCES business_profiles(id) ON DELETE RESTRICT,
  FOREIGN KEY (parent_node_id) REFERENCES kpi_nodes(id) ON DELETE RESTRICT,
  UNIQUE (business_profile_id, node_key)
);

CREATE TABLE measurements (
  id INTEGER PRIMARY KEY,
  kpi_node_id INTEGER NOT NULL,
  task_id INTEGER NOT NULL,
  evidence_id INTEGER NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  value REAL NOT NULL,
  unit TEXT NOT NULL,
  dimensions_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(dimensions_json)),
  imported_at TEXT NOT NULL,
  FOREIGN KEY (kpi_node_id) REFERENCES kpi_nodes(id) ON DELETE RESTRICT,
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE RESTRICT,
  UNIQUE (kpi_node_id, period_start, period_end, dimensions_json),
  CHECK (period_end >= period_start)
);

CREATE TABLE pair_kpi_measure (
  id INTEGER PRIMARY KEY,
  sprint_id INTEGER NOT NULL,
  kpi_node_id INTEGER NOT NULL,
  measurement_id INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('passed', 'revoked')),
  created_at TEXT NOT NULL,
  FOREIGN KEY (sprint_id) REFERENCES sprints(id) ON DELETE RESTRICT,
  FOREIGN KEY (kpi_node_id) REFERENCES kpi_nodes(id) ON DELETE RESTRICT,
  FOREIGN KEY (measurement_id) REFERENCES measurements(id) ON DELETE RESTRICT,
  UNIQUE (sprint_id, kpi_node_id, measurement_id)
);

CREATE TABLE learnings (
  id INTEGER PRIMARY KEY,
  sprint_id INTEGER NOT NULL,
  source_pair_id INTEGER,
  summary TEXT NOT NULL,
  learning_json TEXT NOT NULL CHECK (json_valid(learning_json)),
  status TEXT NOT NULL CHECK (status IN ('draft', 'accepted', 'superseded')),
  created_at TEXT NOT NULL,
  FOREIGN KEY (sprint_id) REFERENCES sprints(id) ON DELETE RESTRICT,
  FOREIGN KEY (source_pair_id) REFERENCES pair_kpi_measure(id) ON DELETE RESTRICT
);

CREATE TABLE playbooks (
  id INTEGER PRIMARY KEY,
  service TEXT NOT NULL,
  operation TEXT NOT NULL,
  route_type TEXT NOT NULL CHECK (route_type IN ('mcp', 'browser', 'api', 'wp_rest', 'wp_cli')),
  version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
  supersedes_playbook_id INTEGER,
  created_by_task_id INTEGER NOT NULL,
  procedure_json TEXT NOT NULL CHECK (json_valid(procedure_json)),
  selector_json TEXT CHECK (selector_json IS NULL OR json_valid(selector_json)),
  status TEXT NOT NULL CHECK (status IN ('active', 'broken', 'retired')),
  consecutive_failures INTEGER NOT NULL DEFAULT 0 CHECK (consecutive_failures >= 0),
  last_failure_at TEXT,
  last_success_at TEXT,
  last_verified_by_agent_id INTEGER,
  created_at TEXT NOT NULL,
  FOREIGN KEY (last_verified_by_agent_id) REFERENCES agents(id) ON DELETE RESTRICT,
  FOREIGN KEY (supersedes_playbook_id) REFERENCES playbooks(id) ON DELETE RESTRICT,
  FOREIGN KEY (created_by_task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  CHECK ((version = 1 AND supersedes_playbook_id IS NULL)
      OR (version > 1 AND supersedes_playbook_id IS NOT NULL)),
  UNIQUE (service, operation, route_type, version),
  UNIQUE (supersedes_playbook_id)
);

CREATE UNIQUE INDEX playbooks_one_current
ON playbooks(service, operation, route_type)
WHERE status IN ('active', 'broken');

CREATE UNIQUE INDEX playbook_repair_one_per_episode
ON tasks(json_extract(input_json, '$.playbook_id'))
WHERE task_type = 'playbook_repair';

CREATE TABLE assets (
  id INTEGER PRIMARY KEY,
  parent_asset_id INTEGER,
  source_task_id INTEGER NOT NULL,
  asset_type TEXT NOT NULL,
  name TEXT NOT NULL,
  wp_media_id TEXT,
  canonical_url TEXT,
  content_hash TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
  created_at TEXT NOT NULL,
  FOREIGN KEY (parent_asset_id) REFERENCES assets(id) ON DELETE RESTRICT,
  FOREIGN KEY (source_task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  UNIQUE (canonical_url),
  UNIQUE (wp_media_id)
);

CREATE TABLE approvals (
  id INTEGER PRIMARY KEY,
  task_id INTEGER NOT NULL,
  requested_by_agent_id INTEGER NOT NULL,
  channel TEXT NOT NULL CHECK (channel = 'discord'),
  binding_subject TEXT NOT NULL,
  binding_operation TEXT NOT NULL,
  binding_at TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('pending', 'approved', 'rejected', 'expired')),
  decided_at TEXT,
  responder_ref TEXT,
  evidence_id INTEGER,
  created_at TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  FOREIGN KEY (requested_by_agent_id) REFERENCES agents(id) ON DELETE RESTRICT,
  FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE RESTRICT,
  UNIQUE (task_id, binding_subject, binding_operation, binding_at)
);

CREATE TABLE config (
  id INTEGER PRIMARY KEY,
  key TEXT NOT NULL,
  value_json TEXT NOT NULL CHECK (json_valid(value_json)),
  value_type TEXT NOT NULL CHECK (value_type IN ('string', 'integer', 'number', 'boolean', 'json')),
  changed_at TEXT NOT NULL,
  changed_by_agent_id INTEGER,
  reason TEXT NOT NULL,
  supersedes_config_id INTEGER,
  FOREIGN KEY (changed_by_agent_id) REFERENCES agents(id) ON DELETE RESTRICT,
  FOREIGN KEY (supersedes_config_id) REFERENCES config(id) ON DELETE RESTRICT,
  UNIQUE (key, changed_at),
  CHECK (supersedes_config_id IS NULL OR supersedes_config_id != id)
);

CREATE TABLE spend_ledger (
  id INTEGER PRIMARY KEY,
  task_id INTEGER NOT NULL,
  entry_type TEXT NOT NULL CHECK (entry_type IN ('charge', 'reversal')),
  approval_id INTEGER NOT NULL,
  service TEXT NOT NULL,
  amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
  currency TEXT NOT NULL DEFAULT 'JPY' CHECK (currency = 'JPY'),
  purpose TEXT NOT NULL CHECK (length(purpose) > 0),
  external_operation_row_id INTEGER UNIQUE,
  external_operation_id TEXT,
  reverses_spend_ledger_id INTEGER UNIQUE,
  occurred_at TEXT NOT NULL CHECK (
    length(occurred_at) = 20
    AND occurred_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'
    AND COALESCE(strftime('%Y-%m-%dT%H:%M:%SZ', occurred_at, '+0 seconds') = occurred_at, 0)),
  created_at TEXT NOT NULL CHECK (
    length(created_at) = 20
    AND created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'
    AND COALESCE(strftime('%Y-%m-%dT%H:%M:%SZ', created_at, '+0 seconds') = created_at, 0)),
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  FOREIGN KEY (approval_id) REFERENCES approvals(id) ON DELETE RESTRICT,
  FOREIGN KEY (external_operation_row_id) REFERENCES external_operations(id) ON DELETE RESTRICT,
  FOREIGN KEY (reverses_spend_ledger_id) REFERENCES spend_ledger(id) ON DELETE RESTRICT,
  CHECK ((entry_type = 'charge'
          AND external_operation_row_id IS NOT NULL
          AND reverses_spend_ledger_id IS NULL)
      OR (entry_type = 'reversal'
          AND external_operation_row_id IS NULL
          AND external_operation_id IS NULL
          AND reverses_spend_ledger_id IS NOT NULL))
);

CREATE TRIGGER config_no_update BEFORE UPDATE ON config
BEGIN SELECT RAISE(ABORT, 'config is append-only'); END;
CREATE TRIGGER config_no_delete BEFORE DELETE ON config
BEGIN SELECT RAISE(ABORT, 'config is append-only'); END;
CREATE TRIGGER evidence_no_update BEFORE UPDATE ON evidence
BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
CREATE TRIGGER evidence_no_delete BEFORE DELETE ON evidence
BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
CREATE TRIGGER state_transitions_no_update BEFORE UPDATE ON state_transitions
BEGIN SELECT RAISE(ABORT, 'state_transitions is append-only'); END;
CREATE TRIGGER state_transitions_no_delete BEFORE DELETE ON state_transitions
BEGIN SELECT RAISE(ABORT, 'state_transitions is append-only'); END;
CREATE TRIGGER approvals_decision_pending_only BEFORE UPDATE ON approvals
WHEN OLD.decision != 'pending'
BEGIN SELECT RAISE(ABORT, 'approval decision is final'); END;
CREATE TRIGGER approvals_final_no_delete BEFORE DELETE ON approvals
WHEN OLD.decision != 'pending'
BEGIN SELECT RAISE(ABORT, 'final approval cannot be deleted'); END;
CREATE TRIGGER external_operations_insert_prepared BEFORE INSERT ON external_operations
WHEN NEW.status != 'prepared'
  OR NEW.evidence_id IS NOT NULL
  OR NEW.sent_at IS NOT NULL
  OR NEW.finalized_at IS NOT NULL
  OR NEW.external_operation_id IS NOT NULL
  OR NEW.remote_object_id IS NOT NULL
  OR NEW.response_hash IS NOT NULL
  OR (NEW.effect = 'read' AND (
      NEW.request_sequence != COALESCE((
        SELECT MAX(prior.request_sequence) + 1
        FROM external_operations AS prior
        WHERE prior.task_id = NEW.task_id
          AND prior.operation = NEW.operation
          AND prior.request_hash = NEW.request_hash
          AND prior.effect = 'read'
      ), 1)
      OR EXISTS (
        SELECT 1 FROM external_operations AS prior
        WHERE prior.task_id = NEW.task_id
          AND prior.operation = NEW.operation
          AND prior.request_hash = NEW.request_hash
          AND prior.effect = 'read'
          AND prior.request_sequence = (
            SELECT MAX(latest.request_sequence)
            FROM external_operations AS latest
            WHERE latest.task_id = NEW.task_id
              AND latest.operation = NEW.operation
              AND latest.request_hash = NEW.request_hash
              AND latest.effect = 'read'
          )
          AND prior.status NOT IN ('confirmed', 'rejected', 'unknown')
      )))
BEGIN SELECT RAISE(ABORT, 'external operation must be an empty prepared actual-I/O row; reads start at sequence 1 and advance only after final'); END;
CREATE TRIGGER external_operations_binding_immutable BEFORE UPDATE OF
  id, task_id, service, operation, effect, policy_category, rate_scope,
  execution_mode, target_endpoint,
  idempotency_key, correlation_key, request_hash, request_sequence, prepared_at ON external_operations
WHEN NEW.id IS NOT OLD.id
  OR NEW.task_id IS NOT OLD.task_id
  OR NEW.service IS NOT OLD.service
  OR NEW.operation IS NOT OLD.operation
  OR NEW.effect IS NOT OLD.effect
  OR NEW.policy_category IS NOT OLD.policy_category
  OR NEW.rate_scope IS NOT OLD.rate_scope
  OR NEW.execution_mode IS NOT OLD.execution_mode
  OR NEW.target_endpoint IS NOT OLD.target_endpoint
  OR NEW.idempotency_key IS NOT OLD.idempotency_key
  OR NEW.correlation_key IS NOT OLD.correlation_key
  OR NEW.request_hash IS NOT OLD.request_hash
  OR NEW.request_sequence IS NOT OLD.request_sequence
  OR NEW.prepared_at IS NOT OLD.prepared_at
BEGIN SELECT RAISE(ABORT, 'external operation binding is immutable'); END;
CREATE TRIGGER external_operations_result_sent_only BEFORE UPDATE OF
  external_operation_id, remote_object_id, response_hash ON external_operations
WHEN OLD.status != 'sent' OR NEW.status != 'sent'
  OR (OLD.external_operation_id IS NOT NULL
      AND NEW.external_operation_id IS NOT OLD.external_operation_id)
  OR (OLD.remote_object_id IS NOT NULL
      AND NEW.remote_object_id IS NOT OLD.remote_object_id)
  OR (OLD.response_hash IS NOT NULL
      AND NEW.response_hash IS NOT OLD.response_hash)
BEGIN SELECT RAISE(ABORT, 'external operation result metadata is write-once while sent'); END;
CREATE TRIGGER external_operations_lifecycle BEFORE UPDATE OF
  status, evidence_id, sent_at, finalized_at ON external_operations
WHEN NOT (
  (OLD.status = 'prepared'
    AND NEW.status = 'sent'
    AND OLD.evidence_id IS NULL AND NEW.evidence_id IS NULL
    AND OLD.sent_at IS NULL AND NEW.sent_at IS NOT NULL
    AND OLD.finalized_at IS NULL AND NEW.finalized_at IS NULL)
  OR
  (OLD.status = 'sent'
    AND NEW.status IN ('confirmed', 'rejected', 'unknown')
    AND OLD.evidence_id IS NULL AND NEW.evidence_id IS NOT NULL
    AND NEW.sent_at IS OLD.sent_at
    AND OLD.finalized_at IS NULL AND NEW.finalized_at IS NOT NULL
    AND EXISTS (
      SELECT 1 FROM evidence AS ev
      WHERE ev.id = NEW.evidence_id
        AND ev.kind = 'operation_log'
        AND ev.external_operation_row_id = NEW.id
        AND ev.task_id = NEW.task_id
        AND ev.value = printf('external-operation:%d', NEW.id)
        AND (ev.external_operation_id IS NULL
             OR ev.external_operation_id IS NEW.external_operation_id)
        AND json_extract(ev.payload_json, '$.external_operation_row_id') IS NEW.id
        AND json_extract(ev.payload_json, '$.effect') IS NEW.effect
        AND json_extract(ev.payload_json, '$.policy_category') IS NEW.policy_category
        AND json_type(ev.payload_json, '$.rate_scope') IS NOT NULL
        AND json_extract(ev.payload_json, '$.rate_scope') IS NEW.rate_scope
        AND json_extract(ev.payload_json, '$.service') IS NEW.service
        AND json_extract(ev.payload_json, '$.operation') IS NEW.operation
        AND json_extract(ev.payload_json, '$.correlation_key') IS NEW.correlation_key
        AND json_extract(ev.payload_json, '$.request_hash') IS NEW.request_hash
        AND json_extract(ev.payload_json, '$.request_sequence') IS NEW.request_sequence
        AND json_extract(ev.payload_json, '$.result') IS NEW.status
        AND (json_type(ev.payload_json, '$.provider_operation_id') IS NULL
             OR json_extract(ev.payload_json, '$.provider_operation_id') IS NEW.external_operation_id)
    ))
)
BEGIN SELECT RAISE(ABORT, 'external operation lifecycle must be prepared->sent->final with one matching operation_log'); END;
CREATE TRIGGER external_operations_final_immutable BEFORE UPDATE ON external_operations
WHEN OLD.status IN ('confirmed', 'rejected', 'unknown')
BEGIN SELECT RAISE(ABORT, 'final external operation is immutable'); END;
CREATE TRIGGER external_operations_no_delete BEFORE DELETE ON external_operations
BEGIN SELECT RAISE(ABORT, 'external_operations is append-only'); END;
CREATE TRIGGER evidence_operation_log_insert AFTER INSERT ON evidence
WHEN NEW.kind = 'operation_log'
BEGIN
  SELECT RAISE(ABORT, 'operation_log created_at must be canonical UTC RFC3339')
  WHERE length(NEW.created_at) != 20
     OR NEW.created_at NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'
     OR NOT COALESCE(strftime('%Y-%m-%dT%H:%M:%SZ', NEW.created_at, '+0 seconds') = NEW.created_at, 0);
  SELECT RAISE(ABORT, 'operation_log must match one sent external operation by row, task, binding, request, result, and optional provider ID')
  WHERE NOT EXISTS (
    SELECT 1 FROM external_operations AS op
    WHERE op.id = NEW.external_operation_row_id
      AND op.status = 'sent'
      AND op.evidence_id IS NULL
      AND op.task_id = NEW.task_id
      AND NEW.value = printf('external-operation:%d', op.id)
      AND (NEW.external_operation_id IS NULL
           OR NEW.external_operation_id IS op.external_operation_id)
      AND json_extract(NEW.payload_json, '$.external_operation_row_id') IS op.id
      AND json_extract(NEW.payload_json, '$.effect') IS op.effect
      AND json_extract(NEW.payload_json, '$.policy_category') IS op.policy_category
      AND json_type(NEW.payload_json, '$.rate_scope') IS NOT NULL
      AND json_extract(NEW.payload_json, '$.rate_scope') IS op.rate_scope
      AND json_extract(NEW.payload_json, '$.service') IS op.service
      AND json_extract(NEW.payload_json, '$.operation') IS op.operation
      AND json_extract(NEW.payload_json, '$.correlation_key') IS op.correlation_key
      AND json_extract(NEW.payload_json, '$.request_hash') IS op.request_hash
      AND json_extract(NEW.payload_json, '$.request_sequence') IS op.request_sequence
      AND json_extract(NEW.payload_json, '$.result') IN ('confirmed', 'rejected', 'unknown')
      AND (json_type(NEW.payload_json, '$.provider_operation_id') IS NULL
           OR json_extract(NEW.payload_json, '$.provider_operation_id') IS op.external_operation_id)
      AND (op.policy_category != 'approved_paid_operation' OR (
        json_type(NEW.payload_json, '$.approval_id') = 'integer'
        AND json_type(NEW.payload_json, '$.amount_minor') = 'integer'
        AND json_extract(NEW.payload_json, '$.amount_minor') > 0
        AND json_extract(NEW.payload_json, '$.currency') = 'JPY'
        AND json_type(NEW.payload_json, '$.purpose') = 'text'
        AND length(json_extract(NEW.payload_json, '$.purpose')) > 0
        AND json_type(NEW.payload_json, '$.occurred_at') = 'text'
      ))
  );
  UPDATE external_operations
  SET status = json_extract(NEW.payload_json, '$.result'),
      evidence_id = NEW.id,
      finalized_at = NEW.created_at
  WHERE id = NEW.external_operation_row_id;
  INSERT INTO spend_ledger (
    task_id, entry_type, approval_id, service, amount_minor, currency, purpose,
    external_operation_row_id, external_operation_id, occurred_at, created_at
  )
  SELECT
    op.task_id, 'charge', json_extract(NEW.payload_json, '$.approval_id'), op.service,
    json_extract(NEW.payload_json, '$.amount_minor'),
    json_extract(NEW.payload_json, '$.currency'),
    json_extract(NEW.payload_json, '$.purpose'), op.id, op.external_operation_id,
    json_extract(NEW.payload_json, '$.occurred_at'), NEW.created_at
  FROM external_operations AS op
  WHERE op.id = NEW.external_operation_row_id
    AND op.policy_category = 'approved_paid_operation'
    AND op.status = 'confirmed';
END;
CREATE TRIGGER evidence_published_url_insert BEFORE INSERT ON evidence
WHEN NEW.kind = 'published_url'
BEGIN
  SELECT RAISE(ABORT, 'published_url must bind one same-task confirmed content_publish write, its operation_log, asset URL, local IDs, and optional provider ID')
  WHERE NOT EXISTS (
    SELECT 1
    FROM external_operations AS op
    JOIN evidence AS operation_log
      ON operation_log.id = NEW.operation_log_evidence_id
     AND operation_log.kind = 'operation_log'
     AND operation_log.task_id = NEW.task_id
     AND operation_log.external_operation_row_id = op.id
    JOIN assets AS asset
      ON asset.id = NEW.asset_id
     AND asset.source_task_id = NEW.task_id
     AND asset.canonical_url = NEW.value
    WHERE op.id = NEW.external_operation_row_id
      AND op.evidence_id = operation_log.id
      AND op.task_id = NEW.task_id
      AND op.execution_mode = 'actual'
      AND op.status = 'confirmed'
      AND op.policy_category = 'content_publish'
      AND op.effect = 'write'
      AND json_extract(NEW.payload_json, '$.external_operation_row_id') IS op.id
      AND json_extract(NEW.payload_json, '$.operation_log_evidence_id') IS operation_log.id
      AND json_extract(NEW.payload_json, '$.asset_id') IS asset.id
      AND json_extract(NEW.payload_json, '$.url') IS NEW.value
      AND op.remote_object_id IS NOT NULL
      AND json_extract(NEW.payload_json, '$.wp_post_id') IS op.remote_object_id
      AND (NEW.external_operation_id IS NULL
           OR NEW.external_operation_id IS op.external_operation_id)
      AND (json_type(NEW.payload_json, '$.provider_operation_id') IS NULL
           OR json_extract(NEW.payload_json, '$.provider_operation_id') IS op.external_operation_id)
  );
END;
CREATE TRIGGER spend_ledger_binding_insert BEFORE INSERT ON spend_ledger
WHEN NOT EXISTS (
    SELECT 1 FROM approvals AS approval
    WHERE approval.id = NEW.approval_id
      AND approval.task_id = NEW.task_id
      AND approval.decision = 'approved'
  )
  OR NOT (
    (NEW.entry_type = 'charge'
      AND NEW.reverses_spend_ledger_id IS NULL
      AND EXISTS (
        SELECT 1 FROM external_operations AS op
        WHERE op.id = NEW.external_operation_row_id
          AND op.task_id = NEW.task_id
          AND op.service = NEW.service
          AND op.external_operation_id IS NEW.external_operation_id
          AND op.execution_mode = 'actual'
          AND op.status = 'confirmed'
          AND op.policy_category = 'approved_paid_operation'
          AND op.effect = 'write'
      ))
    OR
    (NEW.entry_type = 'reversal'
      AND NEW.external_operation_row_id IS NULL
      AND NEW.external_operation_id IS NULL
      AND EXISTS (
        SELECT 1 FROM spend_ledger AS original
        JOIN tasks AS correction ON correction.id = NEW.task_id
        JOIN tasks AS source ON source.id = original.task_id
        WHERE original.id = NEW.reverses_spend_ledger_id
          AND original.entry_type = 'charge'
          AND original.amount_minor = NEW.amount_minor
          AND original.service = NEW.service
          AND original.currency = NEW.currency
          AND correction.task_type = 'spend_correction'
          AND correction.parent_task_id = source.id
          AND correction.loop_run_id = source.loop_run_id
          AND correction.id != source.id
          AND json_type(correction.input_json, '$.original_spend_ledger_id') = 'integer'
          AND json_extract(correction.input_json, '$.original_spend_ledger_id') = original.id
      ))
  )
BEGIN SELECT RAISE(ABORT, 'spend entry must be an approved paid-operation charge or one exact reversal from its bound approved correction task'); END;
CREATE TRIGGER spend_ledger_no_update BEFORE UPDATE ON spend_ledger
BEGIN SELECT RAISE(ABORT, 'spend_ledger is append-only'); END;
CREATE TRIGGER spend_ledger_no_delete BEFORE DELETE ON spend_ledger
BEGIN SELECT RAISE(ABORT, 'spend_ledger is append-only'); END;
CREATE TRIGGER playbook_repair_task_insert BEFORE INSERT ON tasks
WHEN NEW.task_type = 'playbook_repair'
  AND (NEW.state != 'pending'
    OR NEW.expected_output_kind != 'playbook_version'
    OR NEW.attempt != 1
    OR NEW.retry_count != 0
    OR NEW.parent_task_id IS NULL
    OR json_type(NEW.input_json, '$.playbook_id') IS NOT 'integer'
    OR json_type(NEW.input_json, '$.source_task_id') IS NOT 'integer'
    OR json_extract(NEW.input_json, '$.source_task_id') IS NOT NEW.parent_task_id
    OR json_type(NEW.input_json, '$.failure_fingerprint') IS NOT 'text'
    OR length(COALESCE(json_extract(NEW.input_json, '$.failure_fingerprint'), '')) != 64
    OR json_extract(NEW.input_json, '$.failure_fingerprint') GLOB '*[^0-9a-f]*'
    OR NEW.step_key != printf('playbook_repair:%d', json_extract(NEW.input_json, '$.playbook_id'))
    OR NEW.idempotency_key != printf('playbook-repair:%d', json_extract(NEW.input_json, '$.playbook_id'))
    OR NOT EXISTS (
      SELECT 1 FROM playbooks AS broken
      JOIN tasks AS source ON source.id = NEW.parent_task_id
      WHERE broken.id = json_extract(NEW.input_json, '$.playbook_id')
        AND broken.status = 'broken'
        AND source.loop_run_id = NEW.loop_run_id
    ))
BEGIN SELECT RAISE(ABORT, 'playbook repair task must start pending, output playbook_version, and bind one source task and broken episode with attempt=1/retry_count=0'); END;
CREATE TRIGGER playbook_repair_task_no_retry BEFORE UPDATE OF
  loop_run_id, parent_task_id, workflow_id, task_type, step_key,
  attempt, retry_count, idempotency_key, input_json ON tasks
WHEN OLD.task_type = 'playbook_repair'
  AND (NEW.loop_run_id IS NOT OLD.loop_run_id
    OR NEW.parent_task_id IS NOT OLD.parent_task_id
    OR NEW.workflow_id IS NOT OLD.workflow_id
    OR NEW.task_type IS NOT OLD.task_type
    OR NEW.step_key IS NOT OLD.step_key
    OR NEW.attempt IS NOT OLD.attempt
    OR NEW.retry_count IS NOT OLD.retry_count
    OR NEW.idempotency_key IS NOT OLD.idempotency_key
    OR NEW.input_json IS NOT OLD.input_json)
BEGIN SELECT RAISE(ABORT, 'playbook repair task binding is immutable and non-retryable'); END;
CREATE TRIGGER playbook_repair_no_verify_retry BEFORE INSERT ON state_transitions
WHEN NEW.entity_type = 'task'
  AND NEW.event IN ('verify_fail', 'verify_fail_exhausted')
  AND EXISTS (SELECT 1 FROM tasks WHERE id = NEW.entity_id AND task_type = 'playbook_repair')
BEGIN SELECT RAISE(ABORT, 'playbook repair task cannot consume verification retry'); END;
CREATE TRIGGER playbooks_initial_insert BEFORE INSERT ON playbooks
WHEN NEW.version = 1 AND NEW.status != 'active'
BEGIN SELECT RAISE(ABORT, 'initial playbook version must be active'); END;
CREATE TRIGGER playbooks_version_insert BEFORE INSERT ON playbooks
WHEN NEW.version > 1 AND (NEW.status != 'active' OR NOT EXISTS (
  SELECT 1 FROM playbooks AS previous
  JOIN tasks AS creator ON creator.id = NEW.created_by_task_id
  WHERE previous.id = NEW.supersedes_playbook_id
    AND previous.service = NEW.service
    AND previous.operation = NEW.operation
    AND previous.route_type = NEW.route_type
    AND previous.version + 1 = NEW.version
    AND previous.status = 'retired'
    AND creator.state = 'done'
    AND ((creator.task_type = 'playbook_repair'
          AND creator.attempt = 1
          AND creator.retry_count = 0
          AND json_extract(creator.input_json, '$.playbook_id') = previous.id)
      OR creator.task_type = 'playbook_manual_revision')
))
BEGIN SELECT RAISE(ABORT, 'playbook version must supersede the retired previous version of the same route'); END;
CREATE TRIGGER playbooks_content_no_update BEFORE UPDATE OF
  service, operation, route_type, version, supersedes_playbook_id,
  created_by_task_id, procedure_json, selector_json, created_at ON playbooks
WHEN NEW.service IS NOT OLD.service
  OR NEW.operation IS NOT OLD.operation
  OR NEW.route_type IS NOT OLD.route_type
  OR NEW.version IS NOT OLD.version
  OR NEW.supersedes_playbook_id IS NOT OLD.supersedes_playbook_id
  OR NEW.created_by_task_id IS NOT OLD.created_by_task_id
  OR NEW.procedure_json IS NOT OLD.procedure_json
  OR NEW.selector_json IS NOT OLD.selector_json
  OR NEW.created_at IS NOT OLD.created_at
BEGIN SELECT RAISE(ABORT, 'playbook version content is append-only; issue a superseding version'); END;
CREATE TRIGGER playbooks_status_transition BEFORE UPDATE OF status ON playbooks
WHEN NEW.status IS NOT OLD.status
  AND NOT ((OLD.status = 'active' AND NEW.status IN ('broken', 'retired'))
        OR (OLD.status = 'broken' AND NEW.status = 'retired'))
BEGIN SELECT RAISE(ABORT, 'playbook status transition denied'); END;
CREATE TRIGGER playbooks_health_active_only BEFORE UPDATE OF
  consecutive_failures, last_failure_at, last_success_at, last_verified_by_agent_id ON playbooks
WHEN OLD.status != 'active'
  AND (NEW.consecutive_failures IS NOT OLD.consecutive_failures
    OR NEW.last_failure_at IS NOT OLD.last_failure_at
    OR NEW.last_success_at IS NOT OLD.last_success_at
    OR NEW.last_verified_by_agent_id IS NOT OLD.last_verified_by_agent_id)
BEGIN SELECT RAISE(ABORT, 'only active playbook health fields may change'); END;
CREATE TRIGGER playbooks_retired_no_update BEFORE UPDATE ON playbooks
WHEN OLD.status = 'retired'
BEGIN SELECT RAISE(ABORT, 'retired playbook version is immutable'); END;
CREATE TRIGGER playbooks_no_delete BEFORE DELETE ON playbooks
BEGIN SELECT RAISE(ABORT, 'playbook versions are append-only'); END;
CREATE TRIGGER strategic_briefs_no_update BEFORE UPDATE ON strategic_briefs
WHEN OLD.brief_key != NEW.brief_key OR OLD.version != NEW.version
  OR OLD.strategic_choice_id != NEW.strategic_choice_id
  OR OLD.segment_context_id != NEW.segment_context_id
  OR OLD.value_hypothesis_id != NEW.value_hypothesis_id
  OR OLD.desired_recognition_change != NEW.desired_recognition_change
  OR OLD.tactical_objective != NEW.tactical_objective
  OR OLD.media_role != NEW.media_role
  OR OLD.message_hypothesis != NEW.message_hypothesis
  OR OLD.prohibited_patterns_json != NEW.prohibited_patterns_json
  OR OLD.measurement_plan_json != NEW.measurement_plan_json
  OR OLD.valid_from != NEW.valid_from
  OR OLD.digest != NEW.digest
  OR OLD.supersedes_id IS NOT NEW.supersedes_id
  OR OLD.created_at != NEW.created_at
BEGIN SELECT RAISE(ABORT, 'strategic_briefs content is append-only (status/valid_until のみ遷移可。変更は supersedes_id で新版)'); END;
CREATE TRIGGER strategic_briefs_no_delete BEFORE DELETE ON strategic_briefs
BEGIN SELECT RAISE(ABORT, 'strategic_briefs is append-only'); END;
CREATE TRIGGER strategic_briefs_status_transition BEFORE UPDATE OF status ON strategic_briefs
WHEN NEW.status IS NOT OLD.status
  AND NOT ((OLD.status = 'draft' AND NEW.status = 'active')
        OR (OLD.status = 'active' AND NEW.status IN ('superseded', 'retired')))
BEGIN SELECT RAISE(ABORT,
  'strategic_briefs status transition denied: draft->active / active->superseded|retired only (superseded/retired are terminal)'); END;
CREATE TRIGGER strategic_briefs_valid_until_no_extend BEFORE UPDATE OF valid_until ON strategic_briefs
WHEN NEW.valid_until IS NOT OLD.valid_until
  AND OLD.valid_until IS NOT NULL
  AND (NEW.valid_until IS NULL OR NEW.valid_until > OLD.valid_until)
BEGIN SELECT RAISE(ABORT,
  'strategic_briefs valid_until cannot be extended (issue a new version via supersedes_id)'); END;
CREATE TRIGGER tactical_learning_packets_no_update BEFORE UPDATE ON tactical_learning_packets
BEGIN SELECT RAISE(ABORT, 'tactical_learning_packets is append-only'); END;
CREATE TRIGGER tactical_learning_packets_no_delete BEFORE DELETE ON tactical_learning_packets
BEGIN SELECT RAISE(ABORT, 'tactical_learning_packets is append-only'); END;
CREATE TRIGGER tactical_learning_packets_integrity BEFORE INSERT ON tactical_learning_packets
WHEN (SELECT loop_kind FROM loop_runs WHERE id = NEW.loop_run_id) IS NOT 'lower'
  OR (SELECT state FROM loop_runs WHERE id = NEW.loop_run_id)
      NOT IN ('completed', 'failed', 'escalated', 'cancelled')
  OR (SELECT strategic_brief_id FROM loop_runs WHERE id = NEW.loop_run_id)
      IS NOT NEW.strategic_brief_id
  OR (SELECT strategic_brief_digest FROM loop_runs WHERE id = NEW.loop_run_id)
      IS NOT NEW.strategic_brief_digest
  OR (SELECT digest FROM strategic_briefs WHERE id = NEW.strategic_brief_id)
      IS NOT NEW.strategic_brief_digest
BEGIN SELECT RAISE(ABORT, 'tlp integrity: run must be lower+terminal and brief/digest must match'); END;
CREATE TRIGGER loop_runs_brief_immutable BEFORE UPDATE OF strategic_brief_id, strategic_brief_digest
  ON loop_runs
WHEN NEW.strategic_brief_id IS NOT OLD.strategic_brief_id
  OR NEW.strategic_brief_digest IS NOT OLD.strategic_brief_digest
BEGIN SELECT RAISE(ABORT, 'loop_runs brief binding is immutable after insert'); END;
CREATE TRIGGER tlp_kind_matches_terminal_state BEFORE INSERT ON tactical_learning_packets
WHEN (NEW.packet_kind = 'learning'
      AND (SELECT state FROM loop_runs WHERE id = NEW.loop_run_id) IS NOT 'completed')
  OR (NEW.packet_kind = 'failure'
      AND (SELECT state FROM loop_runs WHERE id = NEW.loop_run_id)
          NOT IN ('failed', 'escalated', 'cancelled'))
BEGIN SELECT RAISE(ABORT,
  'tlp kind must match terminal state: completed=learning, failed/escalated/cancelled=failure'); END;
CREATE TRIGGER tlp_kind_field_rules BEFORE INSERT ON tactical_learning_packets
WHEN (NEW.packet_kind = 'failure'
      AND (NEW.causal_interpretation IS NOT NULL
           OR NEW.hypothesis_result IS NOT NULL
           OR NEW.assessment_reason IS NOT NULL
           OR json_array_length(NEW.alternative_explanations_json) != 0
           OR json_array_length(NEW.proposed_revision_targets_json) != 0))
  OR (NEW.packet_kind = 'learning'
      AND (NEW.causal_interpretation IS NULL
           OR NEW.hypothesis_result IS NULL
           OR NEW.assessment_reason IS NULL
           OR json_array_length(NEW.observations_json) = 0
           OR json_array_length(NEW.alternative_explanations_json) = 0))
BEGIN SELECT RAISE(ABORT,
  'tlp field rules: failure must not carry interpretation; learning requires observations/assessment/causal/alternatives'); END;
```

### 2.1 evidence の型契約（FR-28）

`payload_json` は kind 固有の必須キーを格納する。DDL の `json_valid` は構文だけを保証するため、下表の検証は証跡ストア（FN-703）が INSERT 前に実施し、満たさなければ fail-close で拒否する。`value` は kind 内での安定した同一性キーであり、`UNIQUE(task_id, kind, value)` により同一証跡の重複投入を防ぐ。

| kind | `value` | payload_json の必須キー | 列への対応・追加検証 |
|---|---|---|---|
| plan_record | action plan ID | `plan_id`, `appeal`, `target`, `intent` | `plan_id` は `pair_plan_quality.plan_id` と整合 |
| commit_hash | commit hash | `repository`, `commit_hash`, `paths` | `commit_hash` 列も同値。40 又は 64 桁 hash |
| review_pass | review ID | `result`, `checked_items`, `commit_hash`, `reviewer` | `result = PASS`、`commit_hash` 列必須。`reviewer` は author と別 agent |
| published_url | canonical URL | `url`, `wp_post_id`, `external_operation_row_id`, `operation_log_evidence_id`, `asset_id` | 同じ task の confirmed `content_publish` write、対応 operation_log、`assets.canonical_url` へローカル ID で 1:1 束縛。provider ID は任意で、記録時だけ `provider_operation_id` payload／`external_operation_id` 列を外部行と一致 |
| measurement | source hash | `source`, `file_hash`, `period_start`, `period_end`, `row_count` | `file_hash` 列必須。`measurements.evidence_id` が参照 |
| screenshot | file hash | `file_path`, `file_hash`, `captured_at` | `file_path`・`file_hash` 列必須 |
| file_hash | file hash | `file_path`, `file_hash`, `algorithm` | `algorithm = SHA-256`、両列必須 |
| approval | approval ID | `approval_id`, `decision`, `binding_subject`, `binding_operation`, `binding_at` | `decision = approved`、`approvals.evidence_id` と相互整合 |
| operation_log | `external-operation:<external_operations.id>` | `external_operation_row_id`, `effect`, `policy_category`, `rate_scope`, `service`, `operation`, `correlation_key`, `request_hash`, `request_sequence`, `result` | ローカル row ID は必須・UNIQUE・FK。task/effect/policy/rate/service/operation/correlation/request/request_sequence/result は外部行と一致し、read の rate_scope は JSON null。provider ID は存在時だけ一致。`approved_paid_operation` では追加で `approval_id`, `amount_minor`, `currency`, `purpose`, `occurred_at` が必須。secret・本文・credential は禁止 |
| dashboard | output hash | `file_path`, `file_hash`, `period_end` | `file_path`・`file_hash` 列必須 |

必須 kind は `workflows.required_evidence_json` に JSON 配列で宣言する。S0 の基準は T-PLAN: `plan_record`、T-PROD: `commit_hash`、T-REVIEW: `review_pass`、T-PUB: `published_url`・`screenshot`・`approval`、T-MEAS: `measurement`・`file_hash`・`screenshot` とする。`done` 遷移では、現在の workflow の全 kind が当該 task に存在し、各 kind 規則を再検証してからのみ遷移する。

`operation_log` は sent の `external_operations` 行が先に存在しなければ INSERT できない。call 後は sent 行の任意 provider ID / remote object ID / lowercase response hash をそれぞれ NULL から一度だけ記録し、結果を payload に持つ `operation_log` を INSERT する。`prepared_at`／`sent_at`／`finalized_at` と operation_log の `created_at` は実在する秒精度の canonical UTC RFC3339（`YYYY-MM-DDTHH:MM:SSZ`）だけを受理する。`evidence_operation_log_insert` AFTER trigger は INSERT 文の内部で全束縛を検証してから、同じ外部行を `status=<payload.result>, evidence_id=<NEW.id>, finalized_at=<NEW.created_at>` へ更新する。`approved_paid_operation + confirmed` では続けて payload の承認・正額・JPY・非空目的・発生時刻から charge を自動 INSERT する。lifecycle／spend trigger が反対向 FK と全束縛を再検証するため、成功時は operation_log・final 化・charge が同じ statement/transaction で成立し、どれかの失敗時は3者とも rollback される。rejected/unknown は charge 0 行とする。アプリケーションが別の final UPDATE や初回 charge を発行してはならない。不一致・孤児・重複・証跡なし final・final 後の変更を ABORT する。

`published_url` は provider operation ID を同一性キーにしない。`external_operation_row_id` と `operation_log_evidence_id` を必須とし、同じ task の actual・confirmed・`content_publish`・write 外部行、その行を final 化した operation_log、同じ canonical URL の asset に束縛する。各ローカル ID は published_url 側でも UNIQUE とし、他 evidence kind による占有、別 task、非confirmed／非publish、URL・WP post ID・asset 不一致を拒否する。

### 2.2 config の履歴契約（FR-33）

`config` は append-only である。変更は旧行を UPDATE/DELETE せず、新行を INSERT して `supersedes_config_id` に直前の有効行を指定する。読み取り側は、key ごとに `changed_at` が最大の行を有効値とする。`changed_at` の衝突を避けるため、同一 key の同一時刻 INSERT は拒否する。config への UPDATE/DELETE は §2 の保護トリガが常時拒否する（evidence・state_transitions も同様）。

`config.external_operation.sent_recovery_timeout_sec` は必須の integer かつ 1 以上とし、現行承認値は `300` 秒である。欠落・型不一致・0以下は sent recovery を fail-close で escalated とする。timeout 超過は新規 external row、read sequence の前進、write 再送、日次 cap の別 `rate_scope` への付替えを許可する条件ではなく、既存 sent 行を provider と照合して final 化するか unknown に固定するための期限である。

`playbooks` は版付き行である。`procedure_json`／`selector_json` と版束縛列は UPDATE せず、修復成功時は旧 `broken` 版を `retired` にして、同一 transaction で `version + 1` の新 `active` 版を INSERT する。新版は `supersedes_playbook_id` で直前版、`created_by_task_id` で `done` の `playbook_repair` task（人手修正時だけ `playbook_manual_revision` task）に束縛する。同一路線の現役版（`active` 又は `broken`）は最大 1 行、1 版を複数新版が置換することはできない。破損検知時は、旧版の `active→broken` と、破損版 ID・起点 task・failure fingerprint を input に束縛した `state=pending`／`expected_output_kind=playbook_version`／`step_key=playbook_repair:<playbook_id>`／`idempotency_key=playbook-repair:<playbook_id>` の修復子 task 1 行の発行を、条件付き更新の同一 transaction で行う。破損版 ID 自体を episode ID とするため、通知元や fingerprint が違っても同じ版へ修復 task を複数発行できない。`config.playbook_repair_limit` の現行承認値は 1 とし、欠落・1以外は fail-close、変更は要件改訂を伴う。同一破損イベントの終端 task を再発行してはならない。

### 2.3 支出台帳の会計契約（NFR-6）

`spend_ledger` は append-only の正規化会計台帳である。`charge` は正額・JPY・approved approval・非空 purpose を必須とし、同じ task/service/provider ID の actual・confirmed・`approved_paid_operation` write 外部行へ `external_operation_row_id` で一意に束縛する。`occurred_at`／`created_at` は実在する秒精度の canonical UTC RFC3339 だけを受理する。初回 charge は operation_log trigger だけが同じ statement 内で発行する。無料分類、0 円、外部行を持たない手入力、非confirmed、有償以外の policy、未承認、外貨、空目的、不正時刻は拒否する。

取消は元 charge を UPDATE/DELETE せず `reversal` 行を INSERT する。reversal は approved approval と `reverses_spend_ledger_id` を必須とし、外部行／provider ID を持たず、元 charge と amount/service/currency が完全一致する。同じ charge の reversal は最大1行で、reversal の reversal と部分取消は拒否する。UTC 月次純支出は半開区間で次の符号付き集計を用い、単純 `SUM(amount_minor)` は使用しない。

```sql
SELECT COALESCE(SUM(CASE entry_type
  WHEN 'charge' THEN amount_minor
  WHEN 'reversal' THEN -amount_minor
END), 0)
FROM spend_ledger
WHERE currency = 'JPY'
  AND occurred_at >= :month_start_utc
  AND occurred_at < :next_month_start_utc;
```

## 3. 状態遷移契約（FR-11〜13、NFR-3）

遷移表にない組合せは拒否し、状態・retry_count・証跡を変更しない（拒否も `state_transitions` に guard_result = `rejected` で記録する）。各遷移は単一 SQLite transaction で、ガード判定、状態更新、遷移ログ（`state_transitions` 行）をコミットする。`operation_log` 証跡は外部操作専用であり、状態遷移の記録には使わない。`done`、`failed`、`escalated`、`completed`、`cancelled` は終端状態である。

遷移表は **決定的** である: 1 行 = 1 現状態（複合表記禁止）、キー `(entity, 現状態, イベント)` は表内で一意、
終端状態を現状態とする行は存在せず、enum の全非初期状態はいずれかの行の次状態として到達可能とする
（G-TRN-UNIQ/REACH/TERM/GUARD が機械検査）。失敗の分類はイベントで区別する:
`non_retryable_failure` は常に `failed`（局所失敗・代替発行可）、人の関与が必要な失敗は `escalate`
（tasks）又は `fatal_failure`（loop_runs）で常に `escalated` へ遷移する。

**下位 run の終端と TLP（最低 1 件の強制）**: 下位 loop_run（`loop_kind = 'lower'`）の終端遷移
（completed／failed／escalated／cancelled への遷移）は、**同一 transaction で tactical_learning_packet の
INSERT を伴う**（kernel 契約 — completed は `packet_kind = 'learning'`、それ以外は `'failure'`）。
DDL は「最大 1 件」（UNIQUE）と整合（lower・終端・digest 三者一致）を強制し、「最低 1 件」は
この kernel 契約＋DU-11 `verify()`／LP-OPS ヘルスチェックの孤児検査
（**packet を持たない終端 lower run = 0 件**。検出時は escalate）で強制する（AC-SR-03／STC-I-05）。

### 3.1 loop_runs（上位／下位／マイクロ共通）

| 現状態 | イベント | ガード | 次状態 |
|---|---|---|---|
| pending | start | 上位: brand plan が存在／下位: parent が running かつ sprint の KPI target が存在かつ有効な strategic_brief（status = active・digest 一致・有効期間内）を保持／マイクロ: 親 task が in_progress | running |
| running | wait | 外部応答・承認・子 task 完了待ち | waiting |
| waiting | resume | 待機対象の証跡又は承認が充足 | running |
| running | complete | 全子 task が done、必須ゲート PASS、必須証跡完備 | completed |
| running | retryable_failure | 再実行可能で retry_count < `config.retry_limit` | running |
| waiting | retryable_failure | 再実行可能で retry_count < `config.retry_limit` | running |
| running | retry_exhausted | retry_count >= `config.retry_limit` | escalated |
| waiting | retry_exhausted | retry_count >= `config.retry_limit` | escalated |
| running | non_retryable_failure | 自動回復不可だが局所的で、人の関与なく代替 run を発行できる | failed |
| waiting | non_retryable_failure | 自動回復不可だが局所的で、人の関与なく代替 run を発行できる | failed |
| pending | fatal_failure | 認証失効、ゲート／遷移表破損、地図破損、予算超過等により loop_run 全体が自動回復不能で人の関与が必要（局所 task を隔離し安全な代替経路を同じ loop で継続できる場合は対象外） | escalated |
| running | fatal_failure | 同上 | escalated |
| waiting | fatal_failure | 同上 | escalated |
| pending | cancel | 人の明示取消。外部書込み未実行又は補償済み | cancelled |
| running | cancel | 人の明示取消。外部書込み未実行又は補償済み | cancelled |
| waiting | cancel | 人の明示取消。外部書込み未実行又は補償済み | cancelled |

上位は `parent_loop_run_id IS NULL`、下位とマイクロは親 run を必須とする。マイクロ run の retry は親 task の検証 retry と同じ境界で数え、親を超えて独自に回数を増やさない。

### 3.2 tasks

| 現状態 | イベント | ガード | 次状態 |
|---|---|---|---|
| pending | claim | author/verifier が active かつ principal の異なる別 agent、claim する execution が author agent に属する、親 loop が running、入力と workflow が有効 | in_progress |
| in_progress | submit_for_verification | workflow の実行出力が保存済み、author 側必須証跡が有効 | verifying |
| verifying | verify_pass | verifier が author と別 principal、全必須証跡・全ゲートが PASS | done |
| verifying | verify_fail | 差戻し理由と verifier 証跡があり、`retry_count + 1 < config.retry_limit` | in_progress（retry_count を 1 増加） |
| verifying | verify_fail_exhausted | 差戻し理由と verifier 証跡があり、`retry_count + 1 >= config.retry_limit` | escalated（retry_count を 1 増加） |
| pending | non_retryable_failure | 承認 decision = rejected、回復不能な外部失敗、又は秘匿・予算違反のうち、人の関与を要さず局所的で安全な代替 task を発行できるもの。未定義遷移要求は対象外で、業務状態不変の rejected 行にする | failed |
| in_progress | non_retryable_failure | 同上 | failed |
| verifying | non_retryable_failure | 同上 | failed |
| pending | escalate | credential の再投入・失効／再発行、支出 cap/config の是正、ゲート／遷移表の修復、設計判断等、人の関与がないと進めない（承認 decision = rejected は含まない。局所失敗で安全な代替 task を自動発行できる場合は non_retryable_failure） | escalated |
| in_progress | escalate | 同上 | escalated |
| verifying | escalate | 同上 | escalated |

失敗の分類はイベント選択で確定する: `non_retryable_failure` は常に `failed`（局所失敗・代替 task 発行可）、`escalate` は常に `escalated`（人の関与が必要）であり、同一 (現状態, イベント) から複数の次状態は存在しない。分類は失敗を検出した層（ゲート・コネクタ・kernel）が事由コードから決定し、`failure_code` に記録する。再試行は `verify_fail` のみが retry_count を消費し、通信再送は同じ idempotency key による無消費再送とする。

### 3.3 強制終了からの再開規則

| 強制終了時の状態 | 再起動時の扱い | 冪等性・安全条件 |
|---|---|---|
| pending | そのまま再度 claim 可 | task の idempotency key を保持 |
| in_progress（外部操作前） | 同じ author execution で再開又は `lease_expires_at` 失効後に別 execution が再 claim（`lease_owner_execution_id`・`heartbeat_at` を更新） | workspace・入力・既存証跡を再読込 |
| in_progress（外部操作中/後） | `external_operations` の status を先に照合する: `prepared` は未 call とし、write は同一 idempotency key、read は同一 request_sequence の決定的 correlation key で再開。新しい poll/read は直前回 final 後だけ request_sequence を 1 増やした別行にする。`sent` は provider ID / remote object ID / idempotency key / correlation key でリモートを照合し、結果確定時は operation_log INSERT trigger によって同じ文で final 化する。`confirmed`・`rejected`・`unknown` は束縛済み operation_log を再読し、書換えない | sent が 300 秒を超えても再送・sequence前進・rate_scope付替えで cap を迂回しない。照合不能なら write/read とも `unknown` + escalate。paid confirmed は同じ INSERT 文で charge まで成立しなければ全 rollback |
| verifying | verifier が既存出力・証跡を再検証 | PASS/FAIL 証跡が既にあれば同じ結果を採用し二重加算しない |
| waiting | 承認・子 task・外部ジョブを再照合し、充足なら resume、未充足なら待機継続 | 承認は binding subject/operation/at の完全一致のみ有効 |
| done / failed / escalated / completed / cancelled | 終端のまま | 新しい run/task を明示発行するまで遷移不可 |

credential 再投入を含む人手是正は終端 task の状態遷移ではない。元 task は `escalated` のまま保持し、再実行が必要なら人が元 task ID を parent/source とする決定的 idempotency key の replacement task を `pending` で明示発行し、通常の `claim` から開始する。元 task の UPDATE による復活、存在しない task `resume` event、同一 task の再 claim は禁止する。

プロセス内メモリだけの lease、未コミットの出力、外部操作の「成功したはず」という推測を再開根拠にしてはならない。lease は `tasks.lease_owner_execution_id`・`lease_expires_at`・`heartbeat_at` を正本とし、更新は `row_version` の楽観ロックで競合検出する。外部サービスが idempotency key を受け付けない場合は、WP 側に決定的な meta key / slug として idempotency key を保存し（又は operation ID / 投稿 URL の事前照合）、照合不能時は fail-close とする。

pre-call ガード拒否、mock、dry-run には再開対象の外部 I/O が存在しないため、`external_operations` / `operation_log` を作成せず process logger の correlation ID だけを使う。それらを actual として再開対象に昇格してはならない。

## 4. S0 ワークフロー実行契約

S0 で seed する workflow は `WF-WP-1`、`WF-WP-2`、`WF-MEAS-1` である。承認は `WF-WP-2` の独立ゲートとして実行する。各ステップの失敗は task を勝手に `done` にせず、§3 に従って retry、failed 又は escalated とする。

### 4.1 WF-WP-1 — 記事制作→審査

| ステップ | 入力 | 出力 | 必須証跡 kind | ゲート | 失敗時分岐 |
|---|---|---|---|---|---|
| 1. 企画確定 | Notion ネタ又は手動投入、訴求・ターゲット・狙い | action plan と T-PLAN | plan_record | 倫理（S0 は fail-close のルールセット） | 欠損は pending 継続、倫理 FAIL は failed |
| 2. 原稿制作 | 承認済み企画、workflow 定義 | git workspace の記事ソース | commit_hash | 入力型・決定性 | 制作失敗は in_progress のまま再試行 |
| 3. commit 固定 | 記事ソース、repository | commit hash | commit_hash | hash が workspace に実在 | commit 不可は failed |
| 4. 別 agent 審査 | 記事、企画、commit hash | PASS/FAIL と review task | review_pass | author != verifier、倫理 | FAIL は理由を残し verify_fail、上限到達で escalated |
| 5. ペア成立 | action plan、PASS 証跡 | pair_plan_quality（passed） | review_pass | review_pass の hash が制作 hash と一致 | 不一致・証跡不足は公開を拒否 |

`review_pass` は T-REVIEW の task に記録し、`pair_plan_quality` が存在し status = `passed` の場合だけ WF-WP-2 を発行できる。企画又は commit を変更した時点で既存 pair は `revoked` とし、再審査を要求する。

### 4.2 WF-WP-2 — WP 下書き→承認→公開

| ステップ | 入力 | 出力 | 必須証跡 kind | ゲート | 失敗時分岐 |
|---|---|---|---|---|---|
| 1. 公開前検証 | pair_plan_quality、commit hash、記事 | 公開可能判定 | review_pass, commit_hash | pair = passed、hash 一致、証跡完備 | 拒否して T-PUB を failed。WP API を呼ばない |
| 2. 下書き作成 | 記事 HTML、WP 接続、専用 idempotency key | WP draft ID | operation_log | ローカル Docker WP のみ書込み可。`external_operations` を prepared→sent→confirmed で遷移 | timeout/クラッシュは §3.3 の sent 照合で再開、照合不能は escalated |
| 3. 束縛承認 | draft URL/ID、対象、公開操作、時点 | approved approval | approval | channel は許可済み ApprovalTransport、decision = approved、binding 3 項目完全一致 | rejected は non_retryable_failure で failed。expired は承認再要求で待機継続し `config.approval_retry_limit` 到達で escalated。pending は waiting |
| 4. 公開 | approved approval、draft ID、下書きとは別の専用 idempotency key | canonical URL、WP post ID | published_url, operation_log | 承認・pair・証跡の再検証。`external_operations` を prepared→sent→confirmed で遷移 | 再送前照合。公開状態不明（unknown）は escalated |
| 5. 公開確認 | canonical URL | capture | screenshot | URL 到達・URL 一致 | スクショ失敗は retry、上限到達で escalated |
| 6. 資産登録と完了 | WP post/media ID、URL | assets 行、done | published_url, screenshot, approval | required_evidence_json の全充足 | 欠落は done 拒否 |

本番 WP への書込みは S0 のテスト対象外である。S0 の自動化検証はローカル Docker WP だけに対して行い、本番は契約・接続検証までとする（§6）。

### 4.3 WF-MEAS-1 — GA4 計測取り込み

| ステップ | 入力 | 出力 | 必須証跡 kind | ゲート | 失敗時分岐 |
|---|---|---|---|---|---|
| 1. エクスポート取得 | GA4 property、期間、PV node | CSV/xlsx 又は API 応答 | operation_log | 読取専用、対象 property 一致。`execution_mode=actual` で sent 到達した取得 read のみ operation_log を作成 | mock/dry-run は fixture を返し、`external_operations`／operation_log とも 0 行。本番取得不能は failed（公開を巻き戻さない） |
| 2. ファイル固定 | 取得物 | SHA-256 と capture | file_hash, screenshot | hash が再計算一致 | 不一致は failed、投入しない |
| 3. パース | 固定済み取得物 | 正常行・隔離エラー | measurement | schema/type 検証、PV のみ | 壊れた行は隔離し、正常行だけ継続 |
| 4. 投入 | 正常 PV 行、kpi node、取得証跡 | measurements 行 | measurement | evidence_id と node の FK、有料指標型拒否 | transaction 失敗は全投入を rollback |
| 5. 完了 | measurements 件数、証跡 | T-MEAS done | measurement, file_hash, screenshot | 必須証跡完備 | 欠落は done 拒否 |

GA4 取り込みの外部 read は正規 Data API を第一経路とする（[ADR-006](../../00-authority/adr/ADR-006-official-api-routes.md) で決定済み。POC-03 は疎通検証）。API 阻害時のみブラウザエクスポートへ一時フォールバックする。いずれも同一の evidence 契約に収束させる。

## 5. マイグレーション規則（FR-72）

### 5.1 基本規律

- 移行は連番・不変の SQL ファイルとして管理し、適用済みの内容を編集しない。ファイル名は `NNNN_description.sql` とし、内容 SHA-256 を `schema_version` に記録する。
- **expand**: 新テーブル、新列（NULL 許容又は既定値付き）、新 index、新しい enum 値の受容、新旧形式を読むコードを先に追加する。既存の列・値・意味を破壊しない。
- **backfill**: 必要時は明示的な task/WF として再開可能・冪等に実行し、件数・hash・失敗を evidence に残す。巨大更新を暗黙の DDL に混ぜない。
- **contract**: 全 reader が新形式へ移行し、バックフィルと復元試験が PASS した次の昇格でのみ、不要な reader を除去する。SQLite の列削除等が必要でも、新テーブル作成→コピー→検証→名前切替は別 migration とする。
- **rename 禁止**: テーブル・列・enum・evidence kind の rename は禁止する。新しい名前を expand で追加し、旧名は deprecated として read 互換を保つ。意味変更も rename と同じ破壊的変更として扱う。
- 本改訂の `playbooks` 版管理は S0.1 実装着手前の migration 0001 正本へ含める。旧形の `playbooks` を適用済みの DB が存在する環境では単純 `ALTER` や旧 `UNIQUE(service,operation,route_type)` の場当たり的削除を禁止し、新版テーブル作成→bootstrap creator taskを伴うversion=1行のcopy→行数/hash/FK検証→切替を独立したexpand/backfill/contract migrationとして実施する。

### 5.2 昇格手順

1. 変更を expand / backfill / contract のいずれかとして設計し、対象 version、前提 version、rollback 方針、検証 SQL をレビュー可能にする。
2. 空の SQLite に全 migration を適用し、§2 の DDL 相当性、FK 有効性、初期 workflow seed を検証する。
3. 旧版 DB のコピーへ transaction 内で昇格を適用する。適用前に SQLite backup を作成し、適用後に `PRAGMA foreign_key_check`、`PRAGMA integrity_check`、行数・hash 比較を実行する。
4. `schema_version` へ version、migration 名、checksum、適用者、時刻を INSERT する。同 version が存在する、又は checksum 不一致なら停止する。
5. state machine、証跡完備、config 履歴、S0 WF の回帰テストを実行する。失敗時は backup から復元し、失敗した migration は同じ version を書換えず次 version で修正する。
6. 本番昇格は人が結果を確認して実施する。credential を migration、backup、evidence に含めない。

## 6. 環境契約（S0）

| 対象 | ユーザーが用意するもの | ハーネスの前提・責務 | テスト時の扱い |
|---|---|---|---|
| ローカル WP | Docker の `wordpress` + `mariadb`、テスト用サイト・管理者 | REST 接続、下書き→公開、URL/スクショ確認 | **唯一の実 WP 書込み先**。E2E はここで行う |
| 本番 WP | 実サイト、Application Password を暗号化ストア経由で投入 | credential は暗号化ストアから実行時注入し、SQLite・repo・ログに保存しない | S0 は read 接続又は設定検証まで。自動テストの書込み禁止 |
| GA4 | 既存 property、読取権限を持つ分離 credential | property ID は config の非秘匿値、認証値は暗号化ストア | fixture/mock 又は dry-run。実 property への書込みは存在しない |
| 承認通知 | 個人 Discord の許可済み利用者（将来 Web UI / PWA の認証利用者を追加） | binding subject / operation / at を通知・照合し approvals/evidence に記録 | transport は mock 可。署名・承認者 ID・approve/reject/timeout を fixture で検証 |
| credential 全般 | テスト用と本番用を別発行・別保管し、初回投入は人が行う | テスト credential を本番 endpoint に、本番 credential を Docker/mock に使用しない。平文出力禁止 | CI は mock/dry-run と test credential のみ |

`dry-run` / mock は外部 I/O を行わず、予定 request の fingerprint と mock 結果は process logger にだけ残す。`external_operations` / `operation_log` はどちらも 0 行とする。mock は実サービスの成功・失敗・timeout・重複応答を再現し、外部副作用を持たない。テスト中にローカル Docker 以外の本物 WP を書換える設定を検出した場合、実行を拒否する。pre-call ガード拒否も同じく DB 行を作らない。

## 7. S0 アップデート分割（25 機能、機能一覧の FN ID）

S0 のスコープと 25 機能を維持したまま、依存順に 3 更新へ分割する。各更新の完了は次更新の開始条件であり、S0.2/S0.3 は前更新の拒否系テストを回帰実行する。

| 更新 | 目的・完了境界 | FN ID（件数） | 受入の要点 |
|---|---|---|---|
| S0.1 | DB、状態機械、ゲート、証跡の基盤を実働化 | FN-101, FN-102, FN-103, FN-104, FN-105, FN-201, FN-202, FN-204, FN-208, FN-305, FN-701, FN-702, FN-703, FN-704（14） | 23 業務テーブル＋インフラ 2 テーブル＋append-only トリガの生成、未定義遷移拒否、principal の異なる author/verifier、pair 未成立公開拒否、必須証跡欠落時の done 拒否、config INSERT 履歴、versioned strategic_brief のシードと digest 決定性、有効 brief なし／失効／digest 不一致の下位 loop_run 開始拒否、learning/failure packet の生成と run/brief/digest 整合、上流戦略正本への UPDATE/DELETE 拒否（下流からの直接変更不可）— 受入は AC-SR-01〜06・検証は **STC-I-01〜06 の pytest green**（python-ci で実行） |
| S0.2 | 記事制作、審査、束縛承認、ローカル WP 公開を一気通貫化 | FN-401, FN-402, FN-404, FN-406, FN-409, FN-411, FN-501, FN-511（8） | WF-WP-1/2 により commit hash と review PASS を pair 化し、許可済み ApprovalTransport（初期 Discord）での承認後に Docker WP へ公開。URL・スクショ・approval を evidence に収束 |
| S0.3 | GA4 計測、接続レジストリ、攻略地図、最小ダッシュボード用データ面を成立 | FN-601, FN-602, FN-603（3） | WF-MEAS-1 で PV を取得証跡付きで measurements に投入し、registry/playbooks を使う。S0 の DB クエリを最小ダッシュボードのデータソースとして固定（HTML 生成 FN-605 自体は S1） |

合計は **14 + 8 + 3 = 25** 機能である。S0.3 の「ダッシュボード最小」は、SQLite の KPI node・measurement・状態クエリを表示可能なデータ契約までを指し、自己完結 HTML の自動生成は既存のスライス定義どおり S1（FN-605）に残す。

## 8. S0 完了時の契約検証

- 空 DB から §2 の DDL と migration を適用し、`foreign_key_check` と `integrity_check` が成功すること。
- task/loop の全許可・拒否遷移、retry 境界、強制終了後の各再開規則をテストで示すこと。外部操作の
  最危険 kill point（WP 側成功・ローカル `sent` のままクラッシュ）で再送が発生しないことを含む。
- pair 未成立、自己審査（principal 同一を含む）、必須 evidence 欠落、承認 binding 不一致、外部 operation 照合不能をすべて fail-close で拒否すること。
- Docker WP のみを使い、記事 1 本の制作→審査→承認→公開で `commit_hash`、`review_pass`、`published_url`、`screenshot`、`approval` が DB に揃うこと。
- GA4 fixture 又は許可された read 経路で PV を取り込み、`measurements` が `kpi_nodes` と取得証跡へ FK で接続されること。
