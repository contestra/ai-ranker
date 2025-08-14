
import os
import sqlite3
import pytest

SQL_FILE = "db/sqlite_v7_parity.sql"
DB_URL = "sqlite:///./test_sqlite_v7.db"
DB_PATH = DB_URL.split("sqlite:///", 1)[-1]

def test_sqlite_v7_parity_schema():
    os.makedirs("db", exist_ok=True)
    # copy file path is assumed; test will use the file present in repo
    # For this artifact test, we generate it alongside.
    assert os.path.exists(SQL_FILE), "sqlite_v7_parity.sql must be present"

    # fresh DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    try:
        with open(SQL_FILE, "r", encoding="utf-8") as f:
            script = f.read()
        conn.executescript(script)
        # tables exist
        cur = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ('prompt_templates','prompt_versions','prompt_results')")
        rows = cur.fetchall()
        names = {r[0] for r in rows}
        assert {'prompt_templates','prompt_versions','prompt_results'}.issubset(names)
        # partial unique index exists with WHERE clause
        cur = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND name='ux_tpl_org_ws_confighash_active'")
        idx = cur.fetchone()
        assert idx and 'WHERE deleted_at IS NULL' in (idx[1] or '')
    finally:
        conn.close()
