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
