import sqlite3

# --- Section: Outbox Access ---
# Pure I/O helpers with no business logic (no expiry math, no message
# composition) — safe for an orchestrator to import directly instead of
# going through the CLI, since delivery (who/how to notify) is the
# orchestrator's job, not this program's.


def fetch_unsent(conn: sqlite3.Connection) -> list[dict]:
    """Retrieves all notifications that have not yet been delivered.

    Args:
        conn (sqlite3.Connection): Open connection to the shared database.

    Returns:
        list[dict]: Pending outbox rows, oldest first.
    """
    rows = conn.execute(
        "SELECT id, subscription_id, kind, days_before, message, created_at "
        "FROM notifications_outbox WHERE sent_at IS NULL ORDER BY id ASC"
    ).fetchall()
    return [dict(row) for row in rows]


def mark_sent(conn: sqlite3.Connection, outbox_id: int) -> None:
    """Marks a notification as delivered.

    Args:
        conn (sqlite3.Connection): Open connection to the shared database.
        outbox_id (int): Primary key of the notifications_outbox row.
    """
    conn.execute(
        "UPDATE notifications_outbox SET sent_at = datetime('now') WHERE id = ?",
        (outbox_id,),
    )
    conn.commit()


def prune_sent(conn: sqlite3.Connection, older_than_days: int = 30) -> int:
    """Deletes delivered notifications older than a retention window.

    The outbox otherwise grows forever — nothing else ever removes a row.
    Pending (unsent) notifications are never touched, regardless of age.

    Args:
        conn (sqlite3.Connection): Open connection to the shared database.
        older_than_days (int): Retention window in days.

    Returns:
        int: Number of rows deleted.
    """
    cursor = conn.execute(
        "DELETE FROM notifications_outbox WHERE sent_at IS NOT NULL AND sent_at < datetime('now', ?)",
        (f"-{older_than_days} days",),
    )
    conn.commit()
    return cursor.rowcount


def claim_unsent(conn: sqlite3.Connection) -> list[dict]:
    """Atomically claims all pending notifications for delivery.

    Prefer this over separate fetch_unsent()+mark_sent() calls when more
    than one caller can invoke it concurrently (e.g. an orchestrator's
    periodic drain job and its manual "check now" action firing at nearly
    the same moment): flipping sent_at in the same statement that selects
    the rows means two concurrent callers can't both claim the same row —
    whichever transaction commits first wins, and the other sees an empty
    result for that row instead of delivering it twice.

    Args:
        conn (sqlite3.Connection): Open connection to the shared database.

    Returns:
        list[dict]: The rows that were pending, oldest first, now marked sent.
    """
    rows = conn.execute(
        "UPDATE notifications_outbox SET sent_at = datetime('now') "
        "WHERE sent_at IS NULL "
        "RETURNING id, subscription_id, kind, days_before, message, created_at"
    ).fetchall()
    conn.commit()
    return [dict(row) for row in sorted(rows, key=lambda row: row["id"])]
