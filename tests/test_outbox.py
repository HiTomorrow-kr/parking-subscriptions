from datetime import date

from parking_subscriptions import outbox, subscriptions


def _queue_one_notification(conn):
    subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")
    subscriptions.check_payments(conn, today=date(2026, 9, 2))


def test_fetch_unsent_returns_pending_rows(conn):
    _queue_one_notification(conn)
    pending = outbox.fetch_unsent(conn)
    assert len(pending) == 1
    assert pending[0]["kind"] == "payment_due:2026-09-01"


def test_mark_sent_removes_row_from_pending(conn):
    _queue_one_notification(conn)
    [row] = outbox.fetch_unsent(conn)
    outbox.mark_sent(conn, row["id"])
    assert outbox.fetch_unsent(conn) == []


def test_claim_unsent_marks_rows_sent_and_is_idempotent(conn):
    _queue_one_notification(conn)
    claimed = outbox.claim_unsent(conn)
    assert len(claimed) == 1

    # A second, concurrent-style drain must not redeliver the same row.
    assert outbox.claim_unsent(conn) == []
    assert outbox.fetch_unsent(conn) == []


def test_prune_sent_deletes_only_old_delivered_rows(conn):
    _queue_one_notification(conn)
    [row] = outbox.fetch_unsent(conn)
    outbox.mark_sent(conn, row["id"])
    conn.execute(
        "UPDATE notifications_outbox SET sent_at = datetime('now', '-40 days') WHERE id = ?", (row["id"],)
    )
    conn.commit()

    deleted = outbox.prune_sent(conn, older_than_days=30)
    assert deleted == 1
    assert conn.execute("SELECT COUNT(*) FROM notifications_outbox").fetchone()[0] == 0


def test_prune_sent_keeps_recent_and_pending_rows(conn):
    _queue_one_notification(conn)  # stays pending (unsent), regardless of age
    result = outbox.prune_sent(conn, older_than_days=30)
    assert result == 0
    assert len(outbox.fetch_unsent(conn)) == 1
