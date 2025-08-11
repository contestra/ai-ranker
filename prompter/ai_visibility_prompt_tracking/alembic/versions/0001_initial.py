"""initial schema (GROUNDING: NONE|WEB only), RLS, prompt cap"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    run_status = sa.Enum(
        "QUEUED","RUNNING","SUCCEEDED",
        "FAILED_PROVIDER","FAILED_PROXY","FAILED_VALIDATION",
        "FAILED_GROUNDING","CANCELLED",
        name="run_status",
    )
    grounding_mode = sa.Enum("NONE","WEB", name="grounding_mode")
    prompt_category = sa.Enum("tofu","mofu","bofu", name="prompt_category")
    schedule_cadence = sa.Enum("daily","weekly","monthly", name="schedule_cadence")
    for e in (run_status, grounding_mode, prompt_category, schedule_cadence):
        e.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tenants",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id","email", name="uq_users_tenant_email"),
    )

    op.create_table(
        "models",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("model_key", sa.Text, nullable=False),
        sa.Column("capabilities", pg.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.Text, server_default=sa.text("'active'"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("provider","model_key", name="uq_models_provider_key"),
    )

    op.create_table(
        "brands",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("website_url", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint("tenant_id","name", name="uq_brands_tenant_name"),
    )

    op.create_table(
        "brand_variations",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", pg.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value_raw", sa.Text, nullable=False),
        sa.Column("value_normalized", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint("tenant_id","brand_id","value_normalized", name="uq_brand_variation_norm"),
    )

    op.create_table(
        "brand_canonicalization_map",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variation_id", pg.UUID(as_uuid=True), sa.ForeignKey("brand_variations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canonical_brand_id", pg.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("effective_from", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("effective_to", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id","variation_id","canonical_brand_id","effective_from", name="uq_canon_eff_window"),
    )

    op.create_table(
        "prompts",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", pg.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("prompt_text_normalized", sa.Text, nullable=False),
        sa.Column("category", prompt_category, nullable=False, server_default="mofu"),
        sa.Column("language", sa.Text, nullable=False, server_default="en-US"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_index(
        "uq_prompts_tenant_textnorm",
        "prompts", ["tenant_id","prompt_text_normalized"],
        unique=True, postgresql_where=sa.text("deleted_at IS NULL")
    )

    op.create_table(
        "prompt_countries",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_id", pg.UUID(as_uuid=True), sa.ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_index(
        "uq_prompt_country_unique_active",
        "prompt_countries", ["tenant_id","prompt_id","country_code"],
        unique=True, postgresql_where=sa.text("deleted_at IS NULL")
    )

    op.create_table(
        "prompt_models",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_id", pg.UUID(as_uuid=True), sa.ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_id", pg.UUID(as_uuid=True), sa.ForeignKey("models.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("grounding_mode", grounding_mode, nullable=False, server_default="NONE"),  # NONE|WEB
        sa.Column("grounding_policy", pg.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_index(
        "uq_prompt_model_unique_active",
        "prompt_models", ["tenant_id","prompt_id","model_id"],
        unique=True, postgresql_where=sa.text("deleted_at IS NULL")
    )

    op.create_table(
        "schedules",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_id", pg.UUID(as_uuid=True), sa.ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cadence", schedule_cadence, nullable=False),
        sa.Column("timezone", sa.Text, nullable=False),
        sa.Column("run_at", sa.Time(timezone=True), nullable=False),
        sa.Column("next_run_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "runs",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_id", pg.UUID(as_uuid=True), sa.ForeignKey("prompts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("model_id", pg.UUID(as_uuid=True), sa.ForeignKey("models.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("language", sa.Text, nullable=False, server_default="en-US"),
        sa.Column("grounding_mode", grounding_mode, nullable=False, server_default="NONE"),
        sa.Column("grounding_policy_snapshot", pg.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("brand_variation_id", pg.UUID(as_uuid=True), sa.ForeignKey("brand_variations.id", ondelete="SET NULL")),
        sa.Column("canonical_brand_id", pg.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="SET NULL")),
        sa.Column("idempotency_key", sa.Text, nullable=False),
        sa.Column("location_effective", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("scheduled_for_ts", sa.TIMESTAMP(timezone=True)),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("status", run_status, nullable=False, server_default="QUEUED"),
        sa.Column("cost_estimate", sa.Numeric(12,4)),
        sa.Column("token_usage", pg.JSONB),
        sa.Column("raw_provider_meta", pg.JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "uq_runs_uniqueness_when_scheduled",
        "runs",
        ["prompt_id","model_id","country_code","language","grounding_mode","scheduled_for_ts"],
        unique=True, postgresql_where=sa.text("scheduled_for_ts IS NOT NULL")
    )
    op.create_index("ix_runs_tenant_status_time", "runs", ["tenant_id","status","started_at"])

    op.create_table(
        "answers",
        sa.Column("run_id", pg.UUID(as_uuid=True), sa.ForeignKey("runs.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("answer_text", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("preview", sa.String(length=512)),
        sa.Column("full_raw", pg.JSONB),
        sa.Column("citations", pg.JSONB),
        sa.Column("grounding_mode", grounding_mode, nullable=False, server_default="NONE"),
        sa.Column("citation_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("brand_mentions", pg.JSONB),
        sa.Column("competitors", pg.JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Prompt cap trigger (200 active)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_prompt_cap() RETURNS trigger AS $$
        DECLARE cnt integer;
        BEGIN
          IF (TG_OP = 'INSERT') THEN
            SELECT COUNT(*) INTO cnt FROM prompts WHERE tenant_id = NEW.tenant_id AND deleted_at IS NULL;
            IF cnt >= 200 THEN
              RAISE EXCEPTION 'Prompt cap exceeded (200) for tenant %', NEW.tenant_id USING ERRCODE = 'check_violation';
            END IF;
          ELSIF (TG_OP = 'UPDATE') THEN
            IF NEW.deleted_at IS NULL AND OLD.deleted_at IS NOT NULL THEN
              SELECT COUNT(*) INTO cnt FROM prompts WHERE tenant_id = NEW.tenant_id AND deleted_at IS NULL;
              IF cnt >= 200 THEN
                RAISE EXCEPTION 'Prompt cap exceeded (200) for tenant %', NEW.tenant_id USING ERRCODE = 'check_violation';
              END IF;
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_enforce_prompt_cap
        BEFORE INSERT OR UPDATE OF deleted_at ON prompts
        FOR EACH ROW EXECUTE FUNCTION enforce_prompt_cap();
        """
    )

    # RLS
    rls_tables = [
        "users","brands","brand_variations","brand_canonicalization_map",
        "prompts","prompt_countries","prompt_models","schedules","runs","answers"
    ]
    for tbl in rls_tables:
        op.execute(f'ALTER TABLE "{tbl}" ENABLE ROW LEVEL SECURITY;')
        op.execute(
            f"""
            CREATE POLICY {tbl}_tenant_iso ON "{tbl}"
            USING (tenant_id::uuid = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id::uuid = current_setting('app.tenant_id', true)::uuid);
            """
        )


def downgrade():
    for tbl in ["users","brands","brand_variations","brand_canonicalization_map","prompts","prompt_countries","prompt_models","schedules","runs","answers"]:
        op.execute(f'DROP POLICY IF EXISTS {tbl}_tenant_iso ON "{tbl}";')
        op.execute(f'ALTER TABLE "{tbl}" DISABLE ROW LEVEL SECURITY;')
    op.execute("DROP TRIGGER IF EXISTS trg_enforce_prompt_cap ON prompts;")
    op.execute("DROP FUNCTION IF EXISTS enforce_prompt_cap;")
    for t in ["answers","runs","schedules","prompt_models","prompt_countries","prompts","brand_canonicalization_map","brand_variations","brands","models","users","tenants"]:
        op.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    for t in ["schedule_cadence","prompt_category","grounding_mode","run_status"]:
        op.execute(f"DROP TYPE IF EXISTS {t};")
