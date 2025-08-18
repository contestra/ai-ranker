"""Initial schema with Postgres-only support

Revision ID: 001
Revises: 
Create Date: 2025-01-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types for PostgreSQL
    provider_enum = postgresql.ENUM('openai', 'google', 'anthropic', name='provider_enum', create_type=True)
    requested_mode_enum = postgresql.ENUM('REQUIRED', 'PREFERRED', 'OFF', name='requested_mode_enum', create_type=True)
    
    # Organizations table
    op.create_table('organizations',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Workspaces table  
    op.create_table('workspaces',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('org_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('brand_name', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Prompt templates table
    op.create_table('prompt_templates',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('org_id', sa.String(100), nullable=False),
        sa.Column('workspace_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('template_text', sa.Text(), nullable=False),
        sa.Column('config_hash', sa.String(64), nullable=False),
        sa.Column('template_sha256', sa.String(64), nullable=False),
        sa.Column('canonical_json', sa.Text(), nullable=True),
        sa.Column('provider', provider_enum, nullable=True),
        sa.Column('model_name', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id', 'workspace_id', 'config_hash', name='uq_template_config')
    )
    
    # Prompt runs table
    op.create_table('prompt_runs',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('org_id', sa.String(100), nullable=False),
        sa.Column('workspace_id', sa.String(100), nullable=False),
        sa.Column('template_id', sa.String(100), nullable=False),
        sa.Column('provider', provider_enum, nullable=False),
        sa.Column('model_alias', sa.String(100), nullable=False),
        sa.Column('requested_mode', requested_mode_enum, nullable=False),
        sa.Column('inputs_snapshot', sa.JSON(), nullable=True),
        sa.Column('tool_choice_sent', sa.String(50), nullable=True),
        sa.Column('grounding_tool', sa.String(100), nullable=True),
        sa.Column('display_label', sa.String(200), nullable=True),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Prompt results table
    op.create_table('prompt_results',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('run_id', sa.String(100), nullable=False),
        sa.Column('provider', provider_enum, nullable=False),
        sa.Column('model_version', sa.String(100), nullable=True),
        sa.Column('system_fingerprint', sa.String(200), nullable=True),
        sa.Column('grounded_effective', sa.Boolean(), nullable=False),
        sa.Column('tool_call_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('citations_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('why_not_grounded', sa.String(500), nullable=True),
        sa.Column('enforcement_failed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('grounding_binding_note', sa.Text(), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['prompt_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Prompt versions table
    op.create_table('prompt_versions',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('provider', provider_enum, nullable=False),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('system_fingerprint', sa.String(200), nullable=False),
        sa.Column('first_seen', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_seen', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('invocation_count', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'system_fingerprint', name='uq_provider_fingerprint')
    )
    
    # Create indexes for performance
    op.create_index('idx_runs_provider_model_time', 'prompt_runs', ['provider', 'model_alias', 'completed_at'])
    op.create_index('idx_templates_provider_sha', 'prompt_templates', ['provider', 'template_sha256'])
    op.create_index('idx_results_run_id', 'prompt_results', ['run_id'])
    op.create_index('idx_runs_template_id', 'prompt_runs', ['template_id'])
    op.create_index('idx_workspaces_org_id', 'workspaces', ['org_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_workspaces_org_id', table_name='workspaces')
    op.drop_index('idx_runs_template_id', table_name='prompt_runs')
    op.drop_index('idx_results_run_id', table_name='prompt_results')
    op.drop_index('idx_templates_provider_sha', table_name='prompt_templates')
    op.drop_index('idx_runs_provider_model_time', table_name='prompt_runs')
    
    # Drop tables
    op.drop_table('prompt_versions')
    op.drop_table('prompt_results')
    op.drop_table('prompt_runs')
    op.drop_table('prompt_templates')
    op.drop_table('workspaces')
    op.drop_table('organizations')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS provider_enum")
    op.execute("DROP TYPE IF EXISTS requested_mode_enum")