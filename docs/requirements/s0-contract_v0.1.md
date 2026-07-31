# S0 実行契約 v0.1

> status: **confirmed**（2026-07-31 PO 承認 — 要件定義完遂指示。AI 起草）
> pair: [verification-design_v0.1.md §2〜§5](verification-design_v0.1.md)（検証設計③ — HELIX 式 ①↔③ 文書ペア）
> 上位文書: [requirements_v0.1.md](requirements_v0.1.md)（FR/NFR/AC/S0）／[loop-task-workflow_v0.1.md](loop-task-workflow_v0.1.md)（LP/T/WF）／[br-backbone_v0.1.md](br-backbone_v0.1.md)（BR 背骨）
> 位置づけ: S0 の実装者・テスト・運用者が共通に従う、SQLite 正準スキーマ、状態機械、WF 実行、移行および環境の契約。
> **DDL・evidence 型契約・状態遷移表は本書が正準**（上位文書は要約参照）。それ以外の要求内容で
> 上位文書と矛盾した場合は上位文書を優先し、本書を改訂する。

---

## 1. 適用範囲と共通規約

- DB 正本は SQLite である。接続開始時に必ず `PRAGMA foreign_keys = ON` を実行する。SQLite の FK は接続単位で有効化するため、これを省略した接続は不正な実行環境とする。
- 接続開始時に `PRAGMA journal_mode = WAL` と `PRAGMA busy_timeout`（値は `config.sqlite_busy_timeout_ms`）を設定する。書込みは kernel の単一 writer 経由とし、`SQLITE_BUSY` は busy_timeout 内の待機→タイムアウトで retryable_failure として扱う（書込み競合方針）。
- 時刻は UTC の ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`) 文字列、ハッシュは SHA-256 の 64 桁 16 進文字列、JSON は UTF-8 の RFC 8259 JSON とする。
- `*_id` は `INTEGER` の不透明な主キーであり、外部サービス ID・credential・secret を格納しない。外部操作の識別子は `evidence.external_operation_id` のみへ、秘匿情報を除いて記録する。
- 外部書込みは操作単位の idempotency key を必須とし、`external_operations` 行を **prepared → sent → confirmed / rejected / unknown** の順で遷移させる。送信前に prepared・sent を各々コミットし（送信直後クラッシュの検出窓）、結果確定後に confirmed/rejected とし `operation_log` 証跡を派生させる。状態遷移はその後に行う（NFR-3）。1 外部操作 = 1 行であり、下書き作成と公開は別 idempotency key の別行とする。
- `tasks.verifier_agent_id` は全タスクで必須とする。T-REVIEW の verifier は critic 以外の `gate-engine` 等を割り当てる。これにより自己審査禁止を NULL の三値論理に委ねない。
- 上流戦略正本（`strategic_briefs`。S1 以降に追加する上流モデル群も同様）は **上流ループの改善工程のみが新版 INSERT で更新できる**。下流ループ・媒体コネクタ・計測処理は上流戦略正本へ書き込めず、下流からの還流は `tactical_learning_packets`（append-only）の提出のみとする。上流正本の変更は上書きではなく `supersedes_id` を持つ新版行の作成とし、内容列の UPDATE と DELETE は保護トリガが常時拒否する。下流 loop_run（`loop_kind = 'lower'`）は有効な strategic_brief の id と digest を保持しない限り開始できない（[strategy-learning-contract_v0.1.md](strategy-learning-contract_v0.1.md) が契約正本）。
- 自己審査禁止の判定単位は **principal**（`agents.principal` = 実体となるモデル・人・サービス）である。author と verifier は agent 行の差だけでなく principal が異なることを kernel が claim ガードで検査する。実行の系譜は `agent_executions`（execution = セッション/run、親子関係）に記録し、`agent_executions.principal` は複合 FK `(agent_id, principal)` で `agents` と一致を強制する。lease は execution 単位で保持し、**task を claim できる execution は当該 task の `author_agent_id` に属するものに限る**（lease 失効後の再 claim も author agent の新 execution のみ。kernel がガードで拒否）。

## 2. 正準 DDL（FR-71）

以下の順序で適用する。`schema_version`（FR-72 の移行管理）と `state_transitions`（NFR-5 の状態遷移ログ）は
FR-71 の 23 業務テーブル（当初 19 ＋レビュー是正で追加した `agent_executions`・`external_operations`
＋上流戦略再強化で追加した `strategic_briefs`・`tactical_learning_packets`）とは
別のインフラテーブルである。append-only テーブル（`config`・`evidence`・`state_transitions`・
`strategic_briefs`（内容列）・`tactical_learning_packets`）は
保護トリガで UPDATE/DELETE を拒否し、migration 0001 はトリガ込みで本 DDL と等価とする。
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
  task_type TEXT NOT NULL,
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
  loop_run_id INTEGER NOT NULL,
  strategic_brief_id INTEGER NOT NULL,
  strategic_brief_digest TEXT NOT NULL CHECK (length(strategic_brief_digest) = 64),
  observations_json TEXT NOT NULL CHECK (json_valid(observations_json)),
  metrics_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(metrics_json)),
  qualitative_signals_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(qualitative_signals_json)),
  anomalies_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(anomalies_json)),
  hypothesis_result TEXT NOT NULL CHECK (hypothesis_result IN ('supported', 'weakened', 'rejected', 'inconclusive')),
  target_hypothesis_ids_json TEXT NOT NULL CHECK (json_valid(target_hypothesis_ids_json)),
  assessment_reason TEXT NOT NULL,
  causal_interpretation TEXT NOT NULL,
  alternative_explanations_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(alternative_explanations_json)),
  confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
  evidence_ids_json TEXT NOT NULL CHECK (json_valid(evidence_ids_json)),
  proposed_revision_targets_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(proposed_revision_targets_json)),
  recommended_next_action TEXT NOT NULL CHECK (recommended_next_action IN ('continue', 'modify_tactic', 'request_strategy_review', 'stop')),
  created_at TEXT NOT NULL,
  FOREIGN KEY (loop_run_id) REFERENCES loop_runs(id) ON DELETE RESTRICT,
  FOREIGN KEY (strategic_brief_id) REFERENCES strategic_briefs(id) ON DELETE RESTRICT
);

CREATE TABLE tasks (
  id INTEGER PRIMARY KEY,
  loop_run_id INTEGER NOT NULL,
  parent_task_id INTEGER,
  workflow_id INTEGER NOT NULL,
  task_type TEXT NOT NULL,
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
  target_endpoint TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  request_hash TEXT NOT NULL CHECK (length(request_hash) = 64),
  status TEXT NOT NULL CHECK (status IN ('prepared', 'sent', 'confirmed', 'rejected', 'unknown')),
  external_operation_id TEXT,
  remote_object_id TEXT,
  response_hash TEXT CHECK (response_hash IS NULL OR length(response_hash) = 64),
  evidence_id INTEGER,
  prepared_at TEXT NOT NULL,
  sent_at TEXT,
  confirmed_at TEXT,
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE RESTRICT
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
  external_operation_id TEXT,
  file_path TEXT,
  file_hash TEXT,
  created_at TEXT NOT NULL,
  created_by_agent_id INTEGER,
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE RESTRICT,
  FOREIGN KEY (created_by_agent_id) REFERENCES agents(id) ON DELETE RESTRICT,
  UNIQUE (task_id, kind, value),
  CHECK (commit_hash IS NULL OR length(commit_hash) IN (40, 64)),
  CHECK (file_hash IS NULL OR length(file_hash) = 64)
);

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
  procedure_json TEXT NOT NULL CHECK (json_valid(procedure_json)),
  selector_json TEXT CHECK (selector_json IS NULL OR json_valid(selector_json)),
  status TEXT NOT NULL CHECK (status IN ('active', 'broken', 'retired')),
  consecutive_failures INTEGER NOT NULL DEFAULT 0 CHECK (consecutive_failures >= 0),
  last_failure_at TEXT,
  last_success_at TEXT,
  last_verified_by_agent_id INTEGER,
  FOREIGN KEY (last_verified_by_agent_id) REFERENCES agents(id) ON DELETE RESTRICT,
  UNIQUE (service, operation, route_type)
);

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
  channel TEXT NOT NULL CHECK (channel = 'claude_code_app'),
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
  approval_id INTEGER,
  service TEXT NOT NULL,
  amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
  currency TEXT NOT NULL DEFAULT 'JPY' CHECK (length(currency) = 3),
  purpose TEXT NOT NULL,
  external_operation_id TEXT,
  occurred_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
  FOREIGN KEY (approval_id) REFERENCES approvals(id) ON DELETE RESTRICT,
  UNIQUE (service, external_operation_id)
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
CREATE TRIGGER tactical_learning_packets_no_update BEFORE UPDATE ON tactical_learning_packets
BEGIN SELECT RAISE(ABORT, 'tactical_learning_packets is append-only'); END;
CREATE TRIGGER tactical_learning_packets_no_delete BEFORE DELETE ON tactical_learning_packets
BEGIN SELECT RAISE(ABORT, 'tactical_learning_packets is append-only'); END;
```

### 2.1 evidence の型契約（FR-28）

`payload_json` は kind 固有の必須キーを格納する。DDL の `json_valid` は構文だけを保証するため、下表の検証は証跡ストア（FN-703）が INSERT 前に実施し、満たさなければ fail-close で拒否する。`value` は kind 内での安定した同一性キーであり、`UNIQUE(task_id, kind, value)` により同一証跡の重複投入を防ぐ。

| kind | `value` | payload_json の必須キー | 列への対応・追加検証 |
|---|---|---|---|
| plan_record | action plan ID | `plan_id`, `appeal`, `target`, `intent` | `plan_id` は `pair_plan_quality.plan_id` と整合 |
| commit_hash | commit hash | `repository`, `commit_hash`, `paths` | `commit_hash` 列も同値。40 又は 64 桁 hash |
| review_pass | review ID | `result`, `checked_items`, `commit_hash`, `reviewer` | `result = PASS`、`commit_hash` 列必須。`reviewer` は author と別 agent |
| published_url | canonical URL | `url`, `wp_post_id`, `external_operation_id`, `asset_id` | `asset_id`、`external_operation_id` 列必須。URL は `assets.canonical_url` と整合 |
| measurement | source hash | `source`, `file_hash`, `period_start`, `period_end`, `row_count` | `file_hash` 列必須。`measurements.evidence_id` が参照 |
| screenshot | file hash | `file_path`, `file_hash`, `captured_at` | `file_path`・`file_hash` 列必須 |
| file_hash | file hash | `file_path`, `file_hash`, `algorithm` | `algorithm = SHA-256`、両列必須 |
| approval | approval ID | `approval_id`, `decision`, `binding_subject`, `binding_operation`, `binding_at` | `decision = approved`、`approvals.evidence_id` と相互整合 |
| operation_log | external operation ID | `service`, `operation`, `external_operation_id`, `request_fingerprint`, `result` | `external_operation_id` 列必須。secret・本文・credential は禁止 |
| dashboard | output hash | `file_path`, `file_hash`, `period_end` | `file_path`・`file_hash` 列必須 |

必須 kind は `workflows.required_evidence_json` に JSON 配列で宣言する。S0 の基準は T-PLAN: `plan_record`、T-PROD: `commit_hash`、T-REVIEW: `review_pass`、T-PUB: `published_url`・`screenshot`・`approval`、T-MEAS: `measurement`・`file_hash`・`screenshot` とする。`done` 遷移では、現在の workflow の全 kind が当該 task に存在し、各 kind 規則を再検証してからのみ遷移する。

### 2.2 config の履歴契約（FR-33）

`config` は append-only である。変更は旧行を UPDATE/DELETE せず、新行を INSERT して `supersedes_config_id` に直前の有効行を指定する。読み取り側は、key ごとに `changed_at` が最大の行を有効値とする。`changed_at` の衝突を避けるため、同一 key の同一時刻 INSERT は拒否する。config への UPDATE/DELETE は §2 の保護トリガが常時拒否する（evidence・state_transitions も同様）。

## 3. 状態遷移契約（FR-11〜13、NFR-3）

遷移表にない組合せは拒否し、状態・retry_count・証跡を変更しない（拒否も `state_transitions` に guard_result = `rejected` で記録する）。各遷移は単一 SQLite transaction で、ガード判定、状態更新、遷移ログ（`state_transitions` 行）をコミットする。`operation_log` 証跡は外部操作専用であり、状態遷移の記録には使わない。`done`、`failed`、`escalated`、`completed`、`cancelled` は終端状態である。

遷移表は **決定的** である: 1 行 = 1 現状態（複合表記禁止）、キー `(entity, 現状態, イベント)` は表内で一意、
終端状態を現状態とする行は存在せず、enum の全非初期状態はいずれかの行の次状態として到達可能とする
（G-TRN-UNIQ/REACH/TERM/GUARD が機械検査）。失敗の分類はイベントで区別する:
`non_retryable_failure` は常に `failed`（局所失敗・代替発行可）、人の関与が必要な失敗は `escalate`
（tasks）又は `fatal_failure`（loop_runs）で常に `escalated` へ遷移する。

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
| pending | fatal_failure | 認証失効、ゲート赤、地図破損、予算超過等で自動回復不可・人の関与が必要 | escalated |
| running | fatal_failure | 認証失効、ゲート赤、地図破損、予算超過等で自動回復不可・人の関与が必要 | escalated |
| waiting | fatal_failure | 認証失効、ゲート赤、地図破損、予算超過等で自動回復不可・人の関与が必要 | escalated |
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
| pending | non_retryable_failure | 秘匿違反、予算超過、未定義遷移、回復不能な外部失敗等が局所的で代替 task を発行できる | failed |
| in_progress | non_retryable_failure | 同上 | failed |
| verifying | non_retryable_failure | 同上 | failed |
| pending | escalate | 人の束縛承認・credential 再投入・設計判断等、人の関与がないと進めない（承認拒否を含む） | escalated |
| in_progress | escalate | 同上 | escalated |
| verifying | escalate | 同上 | escalated |

失敗の分類はイベント選択で確定する: `non_retryable_failure` は常に `failed`（局所失敗・代替 task 発行可）、`escalate` は常に `escalated`（人の関与が必要）であり、同一 (現状態, イベント) から複数の次状態は存在しない。分類は失敗を検出した層（ゲート・コネクタ・kernel）が事由コードから決定し、`failure_code` に記録する。再試行は `verify_fail` のみが retry_count を消費し、通信再送は同じ idempotency key による無消費再送とする。

### 3.3 強制終了からの再開規則

| 強制終了時の状態 | 再起動時の扱い | 冪等性・安全条件 |
|---|---|---|
| pending | そのまま再度 claim 可 | task の idempotency key を保持 |
| in_progress（外部操作前） | 同じ author execution で再開又は `lease_expires_at` 失効後に別 execution が再 claim（`lease_owner_execution_id`・`heartbeat_at` を更新） | workspace・入力・既存証跡を再読込 |
| in_progress（外部操作中/後） | `external_operations` の status を先に照合する: `prepared` は未送信として同一 idempotency key で再送可、`sent` はリモート側を external operation ID / remote object ID / idempotency key で照合し、成功確認できれば `confirmed` 化して証跡を補完し verifying へ、`confirmed` は証跡補完のみで verifying へ | `sent` で照合不能なら `unknown` とし、外部書込みを再送せず escalate |
| verifying | verifier が既存出力・証跡を再検証 | PASS/FAIL 証跡が既にあれば同じ結果を採用し二重加算しない |
| waiting | 承認・子 task・外部ジョブを再照合し、充足なら resume、未充足なら待機継続 | 承認は binding subject/operation/at の完全一致のみ有効 |
| done / failed / escalated / completed / cancelled | 終端のまま | 新しい run/task を明示発行するまで遷移不可 |

プロセス内メモリだけの lease、未コミットの出力、外部操作の「成功したはず」という推測を再開根拠にしてはならない。lease は `tasks.lease_owner_execution_id`・`lease_expires_at`・`heartbeat_at` を正本とし、更新は `row_version` の楽観ロックで競合検出する。外部サービスが idempotency key を受け付けない場合は、WP 側に決定的な meta key / slug として idempotency key を保存し（又は operation ID / 投稿 URL の事前照合）、照合不能時は fail-close とする。

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
| 3. 束縛承認 | draft URL/ID、対象、公開操作、時点 | approved approval | approval | channel = Claude Code アプリ、decision = approved、binding 3 項目完全一致 | rejected/expired は failed。pending は waiting |
| 4. 公開 | approved approval、draft ID、下書きとは別の専用 idempotency key | canonical URL、WP post ID | published_url, operation_log | 承認・pair・証跡の再検証。`external_operations` を prepared→sent→confirmed で遷移 | 再送前照合。公開状態不明（unknown）は escalated |
| 5. 公開確認 | canonical URL | capture | screenshot | URL 到達・URL 一致 | スクショ失敗は retry、上限到達で escalated |
| 6. 資産登録と完了 | WP post/media ID、URL | assets 行、done | published_url, screenshot, approval | required_evidence_json の全充足 | 欠落は done 拒否 |

本番 WP への書込みは S0 のテスト対象外である。S0 の自動化検証はローカル Docker WP だけに対して行い、本番は契約・接続検証までとする（§6）。

### 4.3 WF-MEAS-1 — GA4 計測取り込み

| ステップ | 入力 | 出力 | 必須証跡 kind | ゲート | 失敗時分岐 |
|---|---|---|---|---|---|
| 1. エクスポート取得 | GA4 property、期間、PV node | CSV/xlsx 又は API 応答 | operation_log | 読取専用、対象 property 一致 | mock/dry-run は fixture を返す。本番取得不能は failed（公開を巻き戻さない） |
| 2. ファイル固定 | 取得物 | SHA-256 と capture | file_hash, screenshot | hash が再計算一致 | 不一致は failed、投入しない |
| 3. パース | 固定済み取得物 | 正常行・隔離エラー | measurement | schema/type 検証、PV のみ | 壊れた行は隔離し、正常行だけ継続 |
| 4. 投入 | 正常 PV 行、kpi node、取得証跡 | measurements 行 | measurement | evidence_id と node の FK、有料指標型拒否 | transaction 失敗は全投入を rollback |
| 5. 完了 | measurements 件数、証跡 | T-MEAS done | measurement, file_hash, screenshot | 必須証跡完備 | 欠落は done 拒否 |

GA4 取り込みの外部 read は正規 Data API を第一経路とする（[ADR-006](../governance/adr/ADR-006-official-api-routes.md) で決定済み。POC-03 は疎通検証）。API 阻害時のみブラウザエクスポートへ一時フォールバックする。いずれも同一の evidence 契約に収束させる。

## 5. マイグレーション規則（FR-72）

### 5.1 基本規律

- 移行は連番・不変の SQL ファイルとして管理し、適用済みの内容を編集しない。ファイル名は `NNNN_description.sql` とし、内容 SHA-256 を `schema_version` に記録する。
- **expand**: 新テーブル、新列（NULL 許容又は既定値付き）、新 index、新しい enum 値の受容、新旧形式を読むコードを先に追加する。既存の列・値・意味を破壊しない。
- **backfill**: 必要時は明示的な task/WF として再開可能・冪等に実行し、件数・hash・失敗を evidence に残す。巨大更新を暗黙の DDL に混ぜない。
- **contract**: 全 reader が新形式へ移行し、バックフィルと復元試験が PASS した次の昇格でのみ、不要な reader を除去する。SQLite の列削除等が必要でも、新テーブル作成→コピー→検証→名前切替は別 migration とする。
- **rename 禁止**: テーブル・列・enum・evidence kind の rename は禁止する。新しい名前を expand で追加し、旧名は deprecated として read 互換を保つ。意味変更も rename と同じ破壊的変更として扱う。

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
| 承認通知 | Claude Code アプリで通知を受け取れる利用者 | binding subject / operation / at を通知・照合し approvals/evidence に記録 | 通知 transport は mock 可。approve/reject/timeout を fixture で検証 |
| credential 全般 | テスト用と本番用を別発行・別保管し、初回投入は人が行う | テスト credential を本番 endpoint に、本番 credential を Docker/mock に使用しない。平文出力禁止 | CI は mock/dry-run と test credential のみ |

`dry-run` は外部書込みを行わず、予定 request の fingerprint と mock operation ID を `operation_log` として残す。mock は実サービスの成功・失敗・timeout・重複応答を再現し、外部副作用を持たない。テスト中にローカル Docker 以外の本物 WP を書換える設定を検出した場合、実行を拒否する。

## 7. S0 アップデート分割（25 機能、機能一覧の FN ID）

S0 のスコープと 25 機能を維持したまま、依存順に 3 更新へ分割する。各更新の完了は次更新の開始条件であり、S0.2/S0.3 は前更新の拒否系テストを回帰実行する。

| 更新 | 目的・完了境界 | FN ID（件数） | 受入の要点 |
|---|---|---|---|
| S0.1 | DB、状態機械、ゲート、証跡の基盤を実働化 | FN-101, FN-102, FN-103, FN-104, FN-105, FN-201, FN-202, FN-204, FN-208, FN-305, FN-701, FN-702, FN-703, FN-704（14） | 23 業務テーブル＋インフラ 2 テーブル＋append-only トリガの生成、未定義遷移拒否、principal の異なる author/verifier、pair 未成立公開拒否、必須証跡欠落時の done 拒否、config INSERT 履歴、versioned strategic_brief のシードと digest 保持、有効 brief なしの下位 loop_run 開始拒否、tactical_learning_packet の生成、上流戦略正本への UPDATE/DELETE 拒否（下流からの直接変更不可） |
| S0.2 | 記事制作、審査、束縛承認、ローカル WP 公開を一気通貫化 | FN-401, FN-402, FN-404, FN-406, FN-409, FN-411, FN-501, FN-511（8） | WF-WP-1/2 により commit hash と review PASS を pair 化し、Claude Code アプリ承認後に Docker WP へ公開。URL・スクショ・approval を evidence に収束 |
| S0.3 | GA4 計測、接続レジストリ、攻略地図、最小ダッシュボード用データ面を成立 | FN-601, FN-602, FN-603（3） | WF-MEAS-1 で PV を取得証跡付きで measurements に投入し、registry/playbooks を使う。S0 の DB クエリを最小ダッシュボードのデータソースとして固定（HTML 生成 FN-605 自体は S1） |

合計は **14 + 8 + 3 = 25** 機能である。S0.3 の「ダッシュボード最小」は、SQLite の KPI node・measurement・状態クエリを表示可能なデータ契約までを指し、自己完結 HTML の自動生成は既存のスライス定義どおり S1（FN-605）に残す。

## 8. S0 完了時の契約検証

- 空 DB から §2 の DDL と migration を適用し、`foreign_key_check` と `integrity_check` が成功すること。
- task/loop の全許可・拒否遷移、retry 境界、強制終了後の各再開規則をテストで示すこと。外部操作の
  最危険 kill point（WP 側成功・ローカル `sent` のままクラッシュ）で再送が発生しないことを含む。
- pair 未成立、自己審査（principal 同一を含む）、必須 evidence 欠落、承認 binding 不一致、外部 operation 照合不能をすべて fail-close で拒否すること。
- Docker WP のみを使い、記事 1 本の制作→審査→承認→公開で `commit_hash`、`review_pass`、`published_url`、`screenshot`、`approval` が DB に揃うこと。
- GA4 fixture 又は許可された read 経路で PV を取り込み、`measurements` が `kpi_nodes` と取得証跡へ FK で接続されること。
