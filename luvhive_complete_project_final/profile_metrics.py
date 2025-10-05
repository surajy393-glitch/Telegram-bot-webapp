
# profile_metrics.py
import os
import psycopg2
from datetime import date

def _dsn() -> str:
    dsn = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL / DB_URL is not set")
    return dsn

def _exec(sql: str, params=()):
    with psycopg2.connect(_dsn(), sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()

def ensure_metric_columns():
    """Safe to call every boot. Uses valid Postgres syntax."""
    with psycopg2.connect(_dsn(), sslmode="require") as conn:
        with conn.cursor() as cur:
            # daily tracking helper
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_dialog_date DATE")
            # counters
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS dialogs_total  INTEGER DEFAULT 0")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS dialogs_today  INTEGER DEFAULT 0")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS messages_sent  INTEGER DEFAULT 0")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS messages_recv  INTEGER DEFAULT 0")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS rating_up     INTEGER DEFAULT 0")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS rating_down   INTEGER DEFAULT 0")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS report_count  INTEGER DEFAULT 0")
        conn.commit()

def dialog_started(user_id: int):
    """+1 total, +1 today (with daily reset)"""
    today = date.today()
    with psycopg2.connect(_dsn(), sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                   SET dialogs_total = COALESCE(dialogs_total,0) + 1,
                       dialogs_today = CASE
                           WHEN last_dialog_date = %s THEN COALESCE(dialogs_today,0) + 1
                           ELSE 1
                       END,
                       last_dialog_date = %s
                 WHERE id = %s
                """,
                (today, today, user_id),
            )
        conn.commit()

def message_sent(user_id: int):
    _exec("UPDATE users SET messages_sent = COALESCE(messages_sent,0)+1 WHERE id = %s", (user_id,))

def message_received(user_id: int):
    _exec("UPDATE users SET messages_recv = COALESCE(messages_recv,0)+1 WHERE id = %s", (user_id,))
