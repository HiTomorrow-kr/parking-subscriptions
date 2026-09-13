import pytest

from parking_subscriptions import subscriptions


def test_update_changes_only_given_fields(conn):
    sub = subscriptions.register(
        conn, plate_number="12가3456", start_date="2026-09-01", end_date="2026-10-01",
        room="101", guest_name="홍길동", monthly_fee=150000,
    )
    updated = subscriptions.update(conn, sub["id"], monthly_fee=160000)
    assert updated["monthly_fee"] == 160000
    assert updated["guest_name"] == "홍길동"
    assert updated["end_date"] == "2026-10-01"


def test_update_preserves_payment_history(conn):
    sub = subscriptions.register(
        conn, plate_number="12가3456", start_date="2026-09-01", end_date="2026-10-01", room="101"
    )
    subscriptions.mark_paid(conn, sub["id"], "2026-09-05")
    updated = subscriptions.update(conn, sub["id"], end_date="2026-11-01")
    assert updated["end_date"] == "2026-11-01"
    assert updated["last_paid_date"] == "2026-09-05"
    assert updated["status"] == "active"


def test_update_rejects_end_date_not_after_start_date(conn):
    sub = subscriptions.register(
        conn, plate_number="12가3456", start_date="2026-09-01", end_date="2026-10-01", room="101"
    )
    with pytest.raises(ValueError, match="end_date"):
        subscriptions.update(conn, sub["id"], end_date="2026-08-01")


def test_update_requires_at_least_one_field(conn):
    sub = subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")
    with pytest.raises(ValueError, match="Nothing to update"):
        subscriptions.update(conn, sub["id"])


def test_update_raises_for_missing_subscription(conn):
    with pytest.raises(ValueError, match="No subscription"):
        subscriptions.update(conn, 999, guest_name="누구")
