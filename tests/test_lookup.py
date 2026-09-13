import pytest

from parking_subscriptions import subscriptions


def test_find_active_by_room_not_found_raises(conn):
    with pytest.raises(ValueError, match="No active subscription"):
        subscriptions.find_active_by_room(conn, "999")


def test_find_active_by_plate_not_found_raises(conn):
    with pytest.raises(ValueError, match="No active subscription"):
        subscriptions.find_active_by_plate(conn, "12가3456")


def test_find_active_by_plate_ambiguous_raises(conn):
    # Room uniqueness doesn't prevent the same plate being registered under
    # two different rooms — find_active_by_plate must refuse to guess.
    subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")
    subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="102")
    with pytest.raises(ValueError, match="Multiple active subscriptions"):
        subscriptions.find_active_by_plate(conn, "12가3456")


def test_find_active_by_room_returns_the_active_row(conn):
    created = subscriptions.register(conn, plate_number="12가3456", start_date="2026-09-01", room="101")
    found = subscriptions.find_active_by_room(conn, "101")
    assert found["id"] == created["id"]
