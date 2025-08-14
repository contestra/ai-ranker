
# apply_sqlite_v7.py — apply sqlite_v7_parity.sql to the SQLite DB in DB_URL
import os, sqlite3

DB_URL = os.getenv("DB_URL", "sqlite:///./dev.db")
SQLITE_PATH = DB_URL.split("sqlite:///", 1)[-1]
SQL_FILE = os.getenv("SQLITE_V7_FILE", "db/sqlite_v7_parity.sql")

def main():
    if not SQL_FILE or not os.path.exists(SQL_FILE):
        raise FileNotFoundError(f"SQL file not found: {SQL_FILE}")
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        with open(SQL_FILE, "r", encoding="utf-8") as f:
            script = f.read()
        conn.executescript(script)
        conn.commit()
        print(f"Applied {SQL_FILE} to {SQLITE_PATH}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
