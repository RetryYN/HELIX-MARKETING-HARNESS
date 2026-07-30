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
  role TEXT NOT NULL,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'disabled')),
  created_at TEXT NOT NULL
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

CREATE TABLE loop_runs (
  id INTEGER PRIMARY KEY,
  parent_loop_run_id INTEGER,
  sprint_id INTEGER,
  workflow_id INTEGER,
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
  CHECK ((loop_kind = 'upper' AND parent_loop_run_id IS NULL)
      OR (loop_kind IN ('lower', 'micro') AND parent_loop_run_id IS NOT NULL))
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
  retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
  idempotency_key TEXT NOT NULL UNIQUE,
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
  CHECK (author_agent_id != verifier_agent_id)
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
