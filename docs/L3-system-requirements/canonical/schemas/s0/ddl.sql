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
