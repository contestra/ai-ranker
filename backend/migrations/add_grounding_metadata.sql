-- Add new columns as NULLABLE for backward compatibility
-- Templates table
ALTER TABLE prompt_templates ADD COLUMN provider TEXT;
ALTER TABLE prompt_templates ADD COLUMN system_temperature REAL;
ALTER TABLE prompt_templates ADD COLUMN system_seed INTEGER;
ALTER TABLE prompt_templates ADD COLUMN system_top_p REAL;
ALTER TABLE prompt_templates ADD COLUMN max_output_tokens INTEGER;
ALTER TABLE prompt_templates ADD COLUMN als_mode TEXT;
ALTER TABLE prompt_templates ADD COLUMN als_hash TEXT;
ALTER TABLE prompt_templates ADD COLUMN safety_profile TEXT;
ALTER TABLE prompt_templates ADD COLUMN request_timeout_ms INTEGER;
ALTER TABLE prompt_templates ADD COLUMN max_retries INTEGER;
ALTER TABLE prompt_templates ADD COLUMN grounding_binding_note TEXT;
ALTER TABLE prompt_templates ADD COLUMN canonical_json TEXT;
ALTER TABLE prompt_templates ADD COLUMN template_sha256 TEXT;
ALTER TABLE prompt_templates ADD COLUMN last_run_at TIMESTAMP;
ALTER TABLE prompt_templates ADD COLUMN total_runs INTEGER DEFAULT 0;

-- Runs table
ALTER TABLE prompt_runs ADD COLUMN provider TEXT;
ALTER TABLE prompt_runs ADD COLUMN grounding_mode_requested TEXT;
ALTER TABLE prompt_runs ADD COLUMN inputs_snapshot TEXT;
ALTER TABLE prompt_runs ADD COLUMN tool_choice_sent TEXT;
ALTER TABLE prompt_runs ADD COLUMN grounding_tool TEXT;
ALTER TABLE prompt_runs ADD COLUMN display_label TEXT;
ALTER TABLE prompt_runs ADD COLUMN grounded_effective INTEGER;
ALTER TABLE prompt_runs ADD COLUMN tool_call_count INTEGER;
ALTER TABLE prompt_runs ADD COLUMN response_api TEXT;
ALTER TABLE prompt_runs ADD COLUMN system_temperature REAL;
ALTER TABLE prompt_runs ADD COLUMN system_seed INTEGER;
ALTER TABLE prompt_runs ADD COLUMN system_top_p REAL;
ALTER TABLE prompt_runs ADD COLUMN max_output_tokens INTEGER;

-- Results table  
ALTER TABLE prompt_results ADD COLUMN citations TEXT;
ALTER TABLE prompt_results ADD COLUMN citations_count INTEGER;
ALTER TABLE prompt_results ADD COLUMN why_not_grounded TEXT;
ALTER TABLE prompt_results ADD COLUMN enforcement_failed INTEGER DEFAULT 0;
ALTER TABLE prompt_results ADD COLUMN model_version TEXT;
ALTER TABLE prompt_results ADD COLUMN system_fingerprint TEXT;

-- Create indices for performance (SQLite-compatible)
CREATE INDEX IF NOT EXISTS idx_runs_composite 
ON prompt_runs(provider, model_name, grounding_mode_requested, created_at);

CREATE INDEX IF NOT EXISTS idx_templates_provider 
ON prompt_templates(provider);

CREATE INDEX IF NOT EXISTS idx_templates_sha256 
ON prompt_templates(template_sha256);