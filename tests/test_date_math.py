from datetime import date

import pytest

from parking_subscriptions.subscriptions import _add_one_month, _is_paid_up, _next_due_date


@pytest.mark.parametrize(
    "start, expected",
    [
        (date(2026, 1, 15), date(2026, 2, 15)),
        (date(2026, 12, 15), date(2027, 1, 15)),  # year rollover
        (date(2026, 1, 31), date(2026, 2, 28)),  # clamps to shorter month
        (date(2024, 1, 31), date(2024, 2, 29)),  # clamps into a leap February
        (date(2026, 5, 31), date(2026, 6, 30)),
    ],
)
def test_add_one_month(start, expected):
    assert _add_one_month(start) == expected


def test_next_due_date_before_any_payment_is_start_date():
    sub = {"start_date": "2026-09-01", "last_paid_date": None}
    assert _next_due_date(sub) == date(2026, 9, 1)


def test_next_due_date_rolls_forward_from_last_payment_not_a_fixed_grid():
    # Paying a few days early still covers exactly one month from the
    # payment date, not the original contract-date grid.
    sub = {"start_date": "2026-09-01", "last_paid_date": "2026-09-28"}
    assert _next_due_date(sub) == date(2026, 10, 28)


@pytest.mark.parametrize(
    "today, due, expected",
    [
        (date(2026, 9, 27), date(2026, 9, 28), True),
        (date(2026, 9, 28), date(2026, 9, 28), False),
        (date(2026, 9, 29), date(2026, 9, 28), False),
    ],
)
def test_is_paid_up_boundary(today, due, expected):
    sub = {"start_date": due.isoformat(), "last_paid_date": None}
    assert _is_paid_up(sub, today) is expected
