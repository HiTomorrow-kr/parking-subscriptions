import pytest

from parking_subscriptions import subscriptions


def test_register_creates_active_subscription(conn):
    sub = subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")
    assert sub["status"] == "active"
    assert sub["plate_number"] == "12가3456"
    assert sub["room"] == "101"
    assert sub["end_date"] is None


def test_register_requires_plate_number(conn):
    with pytest.raises(ValueError, match="plate_number"):
        subscriptions.register(conn, plate_number="  ", start_date="2026-09-01", room="101")


def test_register_requires_room(conn):
    with pytest.raises(ValueError, match="room"):
        subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="  ")


def test_register_rejects_end_date_not_after_start_date(conn):
    with pytest.raises(ValueError, match="end_date"):
        subscriptions.register(
            conn, plate_number="12가3456", start_date="2026-09-01", end_date="2026-09-01", room="101"
        )


def test_register_rejects_second_active_subscription_for_same_room(conn):
    subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")
    with pytest.raises(ValueError, match="already has an active subscription"):
        subscriptions.register(conn, plate_number="34나5678", start_date="2026-09-01", room="101")


def test_register_allows_reregistering_room_after_deactivation(conn):
    first = subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")
    subscriptions.deactivate(conn, first["id"])
    second = subscriptions.register(conn, plate_number="34나5678", start_date="2026-10-01", room="101")
    assert second["status"] == "active"
