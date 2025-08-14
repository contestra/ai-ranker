
import os
import pytest
from sqlalchemy import create_engine, text, inspect
from alembic import command
from alembic.config import Config

PG_DSN = os.getenv("TEST_PG_DSN") or os.getenv("DATABASE_URL") or os.getenv("DB_URL")

pytestmark = pytest.mark.skipif(
    not (PG_DSN and PG_DSN.startswith("postgres")),
    reason="Postgres DSN not provided; set TEST_PG_DSN or DATABASE_URL to run this test."
)

def _alembic_cfg():
    cfg = Config()
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", PG_DSN)
    return cfg

def test_v7_migration_upgrade_downgrade_roundtrip():
    cfg = _alembic_cfg()
    engine = create_engine(PG_DSN, future=True)
    # Upgrade to head (should include V7)
    command.upgrade(cfg, "head")

    insp = inspect(engine)
    # Tables should exist
    for t in ("prompt_templates", "prompt_versions", "prompt_results"):
        assert insp.has_table(t), f"Expected table {t} after upgrade"

    # Partial unique index should be present with WHERE deleted_at IS NULL
    with engine.connect() as conn:
        idx = conn.execute(text("""
            SELECT indexdef
            FROM pg_indexes
            WHERE tablename='prompt_templates'
              AND indexname='ux_tpl_org_ws_confighash_active'
        """)).scalar()
        assert idx and "WHERE deleted_at IS NULL" in idx, idx

    # Downgrade one step (back before V7)
    command.downgrade(cfg, "-1")

    insp2 = inspect(engine)
    for t in ("prompt_templates", "prompt_versions", "prompt_results"):
        assert not insp2.has_table(t), f"Table {t} should be dropped after downgrade -1"

    # Re-upgrade to head to leave DB in good state
    command.upgrade(cfg, "head")
