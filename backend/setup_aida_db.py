"""
setup_aida_db.py — Database Setup and Migration Runner for AIDA.

Reads backend/migrations/001_aida_department_schema.sql and applies it against
the Supabase PostgreSQL instance using SUPABASE_DB_URL.
If direct DB URL is not provided, provides helpful diagnostics and status checks.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
DB_URL = os.getenv("SUPABASE_DB_URL")

SQL_MIGRATION_FILE = os.path.join(os.path.dirname(__file__), "migrations", "001_aida_department_schema.sql")

def run_migration():
    if not os.path.exists(SQL_MIGRATION_FILE):
        print(f"Error: Migration file not found: {SQL_MIGRATION_FILE}")
        sys.exit(1)

    with open(SQL_MIGRATION_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    print(f"[AIDA DB Setup] Loaded migration file: {SQL_MIGRATION_FILE} ({len(sql_content)} bytes)")

    if DB_URL:
        try:
            import psycopg2
            print(f"[AIDA DB Setup] Connecting directly via SUPABASE_DB_URL...")
            conn = psycopg2.connect(DB_URL)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(sql_content)
            cur.close()
            conn.close()
            print("[AIDA DB Setup] Successfully executed AIDA department migrations and seed data!")
            return True
        except ImportError:
            print("[AIDA DB Setup] Note: 'psycopg2' not installed. Install via 'pip install psycopg2-binary'.")
        except Exception as e:
            print(f"[AIDA DB Setup] Database execution note: {e}")
    else:
        print("\n[AIDA DB Setup] Notice: SUPABASE_DB_URL is not set in backend/.env.")
        print("To apply migrations automatically via Python, set SUPABASE_DB_URL in backend/.env.")
        print("Alternatively, copy the SQL in backend/migrations/001_aida_department_schema.sql")
        print("and run it directly in your Supabase Dashboard SQL Editor.\n")

    return False

if __name__ == "__main__":
    run_migration()

