
-- sqlite_v7_parity.sql — V7 schema for dev SQLite (idempotent)
DROP TABLE IF EXISTS prompt_results;
DROP TABLE IF EXISTS prompt_versions;
DROP TABLE IF EXISTS prompt_templates;

CREATE TABLE prompt_templates (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  workspace_id TEXT NOT NULL,
  name TEXT NOT NULL,
  provider TEXT,
  system_instructions TEXT,
  user_prompt_template TEXT NOT NULL,
  country_set TEXT NOT NULL,
  model_id TEXT NOT NULL,
  inference_params TEXT NOT NULL,
  tools_spec TEXT,
  response_format TEXT,
  grounding_profile_id TEXT,
  grounding_snapshot_id TEXT,
  retrieval_params TEXT,
  config_hash TEXT NOT NULL,
  config_canonical_json TEXT NOT NULL,
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  deleted_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_tpl_org_ws_confighash_active
  ON prompt_templates (org_id, workspace_id, config_hash)
  WHERE deleted_at IS NULL;

CREATE TABLE prompt_versions (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  workspace_id TEXT NOT NULL,
  template_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  provider_version_key TEXT NOT NULL,
  model_id TEXT NOT NULL,
  fingerprint_captured_at TEXT,
  first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (org_id, workspace_id, template_id, provider_version_key),
  FOREIGN KEY (template_id) REFERENCES prompt_templates(id)
);

CREATE TABLE prompt_results (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  workspace_id TEXT NOT NULL,
  template_id TEXT NOT NULL,
  version_id TEXT,
  provider_version_key TEXT,
  system_fingerprint TEXT,
  request TEXT NOT NULL,
  response TEXT NOT NULL,
  analysis_config TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (template_id) REFERENCES prompt_templates(id),
  FOREIGN KEY (version_id) REFERENCES prompt_versions(id)
);

CREATE INDEX IF NOT EXISTS ix_results_tpl_time
  ON prompt_results (template_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_results_workspace
  ON prompt_results (workspace_id, created_at DESC);
