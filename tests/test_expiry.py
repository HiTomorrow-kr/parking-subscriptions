from datetime import date

from parking_subscriptions import subscriptions


def test_check_expiry_queues_soon_notification_at_each_threshold(conn):
    subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", end_date="2026-10-01", room="101")

    result = subscriptions.check_expiry(conn, today=date(2026, 9, 24))  # 7 days before
    assert result == {"checked": 1, "queued": 1}


def test_check_expiry_does_not_duplicate_the_same_threshold(conn):
    subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", end_date="2026-10-01", room="101")

    subscriptions.check_expiry(conn, today=date(2026, 9, 24))
    second = subscriptions.check_expiry(conn, today=date(2026, 9, 24))
    assert second["queued"] == 0


def test_check_expiry_flips_status_and_queues_expired_notice_once_past_due(conn):
    sub = subscriptions.register(
        conn, plate_number="12가3456", start_date="2026-09-01", end_date="2026-10-01", room="101"
    )

    result = subscriptions.check_expiry(conn, today=date(2026, 10, 2))
    assert result["queued"] == 1
    assert subscriptions.get(conn, sub["id"])["status"] == "expired"


def test_check_expiry_skips_open_ended_subscriptions(conn):
    subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")

    result = subscriptions.check_expiry(conn, today=date(2030, 1, 1))
    assert result == {"checked": 1, "queued": 0}


def test_check_expiry_ignores_subscriptions_far_from_any_threshold(conn):
    subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", end_date="2026-10-01", room="101")

    result = subscriptions.check_expiry(conn, today=date(2026, 9, 15))
    assert result == {"checked": 1, "queued": 0}
