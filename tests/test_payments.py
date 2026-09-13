from datetime import date

from parking_subscriptions import subscriptions


def test_mark_paid_defaults_to_today(conn):
    sub = subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")
    updated = subscriptions.mark_paid(conn, sub["id"])
    assert updated["last_paid_date"] == date.today().isoformat()


def test_mark_paid_records_explicit_date(conn):
    sub = subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")
    updated = subscriptions.mark_paid(conn, sub["id"], "2026-09-05")
    assert updated["last_paid_date"] == "2026-09-05"


def test_check_payments_respects_the_today_override(conn):
    # Regression test: check_payments used to compute paid_current_month
    # against the real date.today() regardless of the `today` argument,
    # because it forgot to forward it into list_subscriptions().
    sub = subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")
    subscriptions.mark_paid(conn, sub["id"], "2026-09-01")  # next due: 2026-10-01

    still_paid_up = subscriptions.check_payments(conn, today=date(2026, 9, 15))
    assert still_paid_up["queued"] == 0

    past_due = subscriptions.check_payments(conn, today=date(2026, 10, 2))
    assert past_due["queued"] == 1


def test_check_payments_queues_one_reminder_until_paid(conn):
    subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")

    first = subscriptions.check_payments(conn, today=date(2026, 9, 2))
    assert first["queued"] == 1

    # Same due date still missed: no duplicate reminder.
    second = subscriptions.check_payments(conn, today=date(2026, 9, 3))
    assert second["queued"] == 0


def test_check_payments_no_reminder_when_paid_up(conn):
    sub = subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")
    subscriptions.mark_paid(conn, sub["id"], "2026-09-01")

    result = subscriptions.check_payments(conn, today=date(2026, 9, 15))
    assert result["queued"] == 0
