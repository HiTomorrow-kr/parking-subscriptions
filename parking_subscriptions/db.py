import os
import sqlite3

from .config import get_db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    room TEXT,
    guest_name TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT,
    monthly_fee INTEGER,
    status TEXT NOT NULL DEFAULT 'active',
    created_by TEXT,
    created_at TEXT NOT NULL,
    last_paid_date TEXT
);

CREATE TABLE IF NOT EXISTS notifications_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id),
    kind TEXT NOT NULL,
    days_before INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    sent_at TEXT,
    UNIQUE(subscription_id, kind, days_before)
);

-- One active subscription per room, enforced at the DB level (not just in
-- register()'s pre-check) so two concurrent registrations can't both slip
-- past a SELECT-then-INSERT race. NULLs (no room assigned) are exempt —
-- SQLite treats each NULL as distinct, so any number of roomless rows coexist.
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_subscription_per_room
    ON subscriptions(room) WHERE status = 'active';
"""


def connect() -> sqlite3.Connection:
    """Opens a connection to the shared SQLite database, creating the schema if needed.

    Returns:
        sqlite3.Connection: Connection with WAL mode enabled and row access by name.
    """
    db_path = get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # A cron-driven check-expiry/check-payments run and an orchestrator's
    # outbox drain can land on the DB at nearly the same moment; without a
    # busy timeout, whichever one loses the race gets an immediate
    # "database is locked" error instead of just waiting its turn.
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Adds columns introduced after a database file already existed.

    CREATE TABLE IF NOT EXISTS only helps brand-new files; a physical
    sqlite file created before a schema change stays on the old shape
    forever otherwise (this bit us once already with end_date NOT NULL).
    """
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(subscriptions)")}
    if "last_paid_date" not in existing:
        conn.execute("ALTER TABLE subscriptions ADD COLUMN last_paid_date TEXT")
        conn.commit()
