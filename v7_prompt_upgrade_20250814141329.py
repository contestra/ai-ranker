
"""Prompt De-dup + Provider-Versioned Runs (V7)

Revision ID: v7_prompt_upgrade_20250814141329
Revises: <SET_YOUR_PREV_REVISION_ID>
Create Date: 2025-08-14T14:13:29.369314Z

This migration creates:
- prompt_templates (brand-scoped; active-only unique index on (org_id, workspace_id, config_hash) where deleted_at is null)
- prompt_versions (provider-version keyed with unique constraint)
- prompt_results (audit trail) + useful indices

Notes:
- Uses gen_random_uuid() -> requires pgcrypto extension.
- Adjust `Revises` to your previous revision ID before applying.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

# revision identifiers, used by Alembic.
revision = "v7_prompt_upgrade_20250814141329"
down_revision = "<SET_YOUR_PREV_REVISION_ID>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgcrypto for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # ---------- prompt_templates ----------
    op.create_table(
        "prompt_templates",
        sa.Column("id", psql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", psql.UUID(as_uuid=False), nullable=False),
        sa.Column("workspace_id", psql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=True),  # optional; not part of hash
        sa.Column("system_instructions", sa.Text(), nullable=True),
        sa.Column("user_prompt_template", sa.Text(), nullable=False),
        sa.Column("country_set", psql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("inference_params", psql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tools_spec", psql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_format", psql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("grounding_profile_id", psql.UUID(as_uuid=False), nullable=True),
        sa.Column("grounding_snapshot_id", sa.Text(), nullable=True),
        sa.Column("retrieval_params", psql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("config_hash", sa.Text(), nullable=False),
        sa.Column("config_canonical_json", psql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", psql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    # Active-only unique index
    op.create_index(
        "ux_tpl_org_ws_confighash_active",
        "prompt_templates",
        ["org_id", "workspace_id", "config_hash"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ---------- prompt_versions ----------
    op.create_table(
        "prompt_versions",
        sa.Column("id", psql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", psql.UUID(as_uuid=False), nullable=False),
        sa.Column("workspace_id", psql.UUID(as_uuid=False), nullable=False),
        sa.Column("template_id", psql.UUID(as_uuid=False), sa.ForeignKey("prompt_templates.id"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_version_key", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("fingerprint_captured_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("org_id", "workspace_id", "template_id", "provider_version_key", name="ux_versions_org_ws_tpl_pvk"),
    )

    # ---------- prompt_results ----------
    op.create_table(
        "prompt_results",
        sa.Column("id", psql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", psql.UUID(as_uuid=False), nullable=False),
        sa.Column("workspace_id", psql.UUID(as_uuid=False), nullable=False),
        sa.Column("template_id", psql.UUID(as_uuid=False), sa.ForeignKey("prompt_templates.id"), nullable=False),
        sa.Column("version_id", psql.UUID(as_uuid=False), sa.ForeignKey("prompt_versions.id"), nullable=True),
        sa.Column("provider_version_key", sa.Text(), nullable=True),
        sa.Column("system_fingerprint", sa.Text(), nullable=True),
        sa.Column("request", psql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response", psql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("analysis_config", psql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_results_tpl_time", "prompt_results", ["template_id", sa.text("created_at DESC")])
    op.create_index("ix_results_workspace", "prompt_results", ["workspace_id", sa.text("created_at DESC")])


def downgrade() -> None:
    # Drop indexes then tables in reverse dep order
    op.drop_index("ix_results_workspace", table_name="prompt_results")
    op.drop_index("ix_results_tpl_time", table_name="prompt_results")
    op.drop_table("prompt_results")

    op.drop_table("prompt_versions")  # drops unique constraint implicitly

    op.drop_index("ux_tpl_org_ws_confighash_active", table_name="prompt_templates")
    op.drop_table("prompt_templates")
