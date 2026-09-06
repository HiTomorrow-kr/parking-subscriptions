import calendar
import sqlite3
from datetime import datetime, date

# --- Section: Domain Logic ---
# All business rules for monthly parking subscriptions live here. This
# module has no knowledge of Telegram, Discord, or any other bot framework.

DATE_FORMAT = "%Y-%m-%d"
EXPIRY_THRESHOLDS = (7, 3, 1, 0)


def _parse_date(value: str, field: str) -> date:
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {field}, expected YYYY-MM-DD: {value!r}")


def register(
    conn: sqlite3.Connection,
    plate_number: str,
    start_date: str,
    end_date: str | None = None,
    room: str | None = None,
    guest_name: str | None = None,
    monthly_fee: int | None = None,
    created_by: str | None = None,
) -> dict:
    """Registers a new monthly parking subscription.

    Args:
        conn: Open database connection.
        plate_number: Vehicle plate number.
        start_date: Subscription start date (YYYY-MM-DD).
        end_date: Subscription end date (YYYY-MM-DD), or None for an
            open-ended subscription that renews until explicitly cancelled.
        room: Optional room/guest identifier.
        guest_name: Optional guest name.
        monthly_fee: Optional monthly fee amount.
        created_by: Identifier of who registered this (bot-specific user id).

    Returns:
        dict: The newly created subscription record.

    Raises:
        ValueError: If dates are malformed, end_date is not after start_date,
            or room already has an active subscription (one car per room —
            room is a fixed, permanent assignment for monthly parking).
    """
    plate_number = (plate_number or "").strip()
    if not plate_number:
        raise ValueError("plate_number is required")

    room = (room or "").strip() or None
    if room is not None:
        existing = conn.execute(
            "SELECT plate_number FROM subscriptions WHERE room = ? AND status = 'active'", (room,)
        ).fetchone()
        if existing:
            raise ValueError(
                f"Room {room!r} already has an active subscription ({existing['plate_number']})"
            )

    start = _parse_date(start_date, "start_date")
    end_iso = None
    if end_date is not None:
        end = _parse_date(end_date, "end_date")
        if end <= start:
            raise ValueError("end_date must be after start_date")
        end_iso = end.isoformat()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        "INSERT INTO subscriptions "
        "(plate_number, room, guest_name, start_date, end_date, monthly_fee, "
        " status, created_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)",
        (
            plate_number,
            room,
            guest_name,
            start.isoformat(),
            end_iso,
            monthly_fee,
            created_by,
            created_at,
        ),
    )
    conn.commit()
    return get(conn, cursor.lastrowid)


def find_active_by_plate(conn: sqlite3.Connection, plate_number: str) -> dict:
    """Finds the single active subscription for a plate number.

    Lets callers (CLI, bots) identify a subscription by plate instead of by
    id, which nobody has memorized.

    Raises:
        ValueError: If there is no active subscription for that plate, or
            more than one (ambiguous — caller should use the id instead).
    """
    plate_number = (plate_number or "").strip()
    rows = conn.execute(
        "SELECT * FROM subscriptions WHERE plate_number = ? AND status = 'active'",
        (plate_number,),
    ).fetchall()
    if not rows:
        raise ValueError(f"No active subscription for plate {plate_number!r}")
    if len(rows) > 1:
        raise ValueError(f"Multiple active subscriptions for plate {plate_number!r}; use the id instead")
    return dict(rows[0])


def find_active_by_room(conn: sqlite3.Connection, room: str) -> dict:
    """Finds the single active subscription for a room number.

    Raises:
        ValueError: If there is no active subscription for that room, or
            more than one (ambiguous — caller should use the id instead).
    """
    room = (room or "").strip()
    rows = conn.execute(
        "SELECT * FROM subscriptions WHERE room = ? AND status = 'active'", (room,)
    ).fetchall()
    if not rows:
        raise ValueError(f"No active subscription for room {room!r}")
    if len(rows) > 1:
        raise ValueError(f"Multiple active subscriptions for room {room!r}; use the id instead")
    return dict(rows[0])


def get(conn: sqlite3.Connection, subscription_id: int) -> dict:
    """Fetches a single subscription by id.

    Raises:
        ValueError: If no subscription exists with that id.
    """
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE id = ?", (subscription_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"No subscription with id {subscription_id}")
    return dict(row)


def get_with_status(conn: sqlite3.Connection, subscription_id: int, today: date | None = None) -> dict:
    """Fetches a subscription with its computed paid_current_month status.

    For a detail view (as opposed to `get`, used internally by
    deactivate/mark_paid where the extra field isn't relevant).
    """
    sub = get(conn, subscription_id)
    sub["paid_current_month"] = _paid_current_month(sub.get("last_paid_date"), today or date.today())
    return sub


def _paid_current_month(last_paid_date: str | None, today: date) -> bool:
    if not last_paid_date:
        return False
    paid = _parse_date(last_paid_date, "last_paid_date")
    return (paid.year, paid.month) == (today.year, today.month)


def list_subscriptions(
    conn: sqlite3.Connection, status: str | None = None, today: date | None = None
) -> list[dict]:
    """Lists subscriptions, optionally filtered by status.

    Args:
        conn: Open database connection.
        status: One of 'active' / 'expired' / 'cancelled', or None for all.
        today: Override for "today" (used in tests); defaults to date.today().

    Returns:
        list[dict]: Matching subscription records, ordered by room number
            (numerically; rooms are a fixed per-subscription assignment, so
            this is the natural sort for a human scanning the list), with
            subscriptions that have no room listed last. Each record
            includes a computed "paid_current_month" bool: whether
            last_paid_date falls in the current calendar month.
    """
    today = today or date.today()
    order_by = "ORDER BY room IS NULL, CAST(room AS INTEGER), room"
    if status:
        rows = conn.execute(
            f"SELECT * FROM subscriptions WHERE status = ? {order_by}", (status,)
        ).fetchall()
    else:
        rows = conn.execute(f"SELECT * FROM subscriptions {order_by}").fetchall()

    result = [dict(row) for row in rows]
    for r in result:
        r["paid_current_month"] = _paid_current_month(r.get("last_paid_date"), today)
    return result


def mark_paid(conn: sqlite3.Connection, subscription_id: int, paid_date: str | None = None) -> dict:
    """Records a payment for a subscription.

    Args:
        conn: Open database connection.
        subscription_id: The subscription being paid for.
        paid_date: Date the payment was made (YYYY-MM-DD), or None for today.

    Returns:
        dict: The updated subscription record.

    Raises:
        ValueError: If no subscription exists with that id, or paid_date is malformed.
    """
    get(conn, subscription_id)  # raises if missing
    paid = _parse_date(paid_date, "paid_date") if paid_date else date.today()
    conn.execute(
        "UPDATE subscriptions SET last_paid_date = ? WHERE id = ?",
        (paid.isoformat(), subscription_id),
    )
    conn.commit()
    return get(conn, subscription_id)


def deactivate(conn: sqlite3.Connection, subscription_id: int) -> dict:
    """Cancels a subscription so it no longer triggers expiry checks.

    Raises:
        ValueError: If no subscription exists with that id.
    """
    get(conn, subscription_id)  # raises if missing
    conn.execute(
        "UPDATE subscriptions SET status = 'cancelled' WHERE id = ?",
        (subscription_id,),
    )
    conn.commit()
    return get(conn, subscription_id)


def _expiry_soon_message(sub: dict, days_left: int) -> str:
    label = f"{sub['room']}호 " if sub.get("room") else ""
    if days_left == 0:
        return f"[정기 주차 알림] {label}{sub['plate_number']} 정기 주차권이 오늘({sub['end_date']}) 만료됩니다."
    return (
        f"[정기 주차 알림] {label}{sub['plate_number']} 정기 주차권이 "
        f"{sub['end_date']}에 만료됩니다 ({days_left}일 남음)."
    )


def _expired_message(sub: dict) -> str:
    label = f"{sub['room']}호 " if sub.get("room") else ""
    return f"[정기 주차 만료] {label}{sub['plate_number']} 정기 주차권이 만료되었습니다 ({sub['end_date']}). 갱신이 필요합니다."


def check_expiry(conn: sqlite3.Connection, today: date | None = None) -> dict:
    """Scans active subscriptions and queues expiry notifications.

    Queues an 'expiry_soon' notification at 7/3/1/0 days before end_date, and
    an 'expired' notification (plus a status flip to 'expired') once the end
    date has passed. Uses INSERT OR IGNORE against a UNIQUE constraint so
    repeated runs never queue duplicate notifications for the same
    (subscription, kind, days_before).

    Args:
        conn: Open database connection.
        today: Override for "today" (used in tests); defaults to date.today().

    Returns:
        dict: {"checked": <active subscriptions scanned>, "queued": <notifications queued>}
    """
    today = today or date.today()
    active = list_subscriptions(conn, status="active")
    queued = 0
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for sub in active:
        if sub["end_date"] is None:
            continue  # open-ended subscription: renews until cancelled

        end = _parse_date(sub["end_date"], "end_date")
        days_left = (end - today).days

        if days_left in EXPIRY_THRESHOLDS:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO notifications_outbox "
                "(subscription_id, kind, days_before, message, created_at) "
                "VALUES (?, 'expiry_soon', ?, ?, ?)",
                (sub["id"], days_left, _expiry_soon_message(sub, days_left), created_at),
            )
            queued += cursor.rowcount

        if days_left < 0:
            conn.execute(
                "UPDATE subscriptions SET status = 'expired' WHERE id = ?", (sub["id"],)
            )
            cursor = conn.execute(
                "INSERT OR IGNORE INTO notifications_outbox "
                "(subscription_id, kind, days_before, message, created_at) "
                "VALUES (?, 'expired', 0, ?, ?)",
                (sub["id"], _expired_message(sub), created_at),
            )
            queued += cursor.rowcount

    conn.commit()
    return {"checked": len(active), "queued": queued}


def _current_period_start(start: date, today: date) -> date:
    """The most recent monthly billing due date on or before `today`.

    The due date is the contract's own anniversary — the day-of-month of
    `start` — not the calendar month, since billing runs on the contract
    date (e.g. a subscription started on the 12th is due on the 12th of
    every month). Clamped to the last day of a shorter month.
    """
    day = start.day
    year, month = today.year, today.month
    candidate = date(year, month, min(day, calendar.monthrange(year, month)[1]))
    if candidate > today:
        month -= 1
        if month == 0:
            month, year = 12, year - 1
        candidate = date(year, month, min(day, calendar.monthrange(year, month)[1]))
    return candidate


def _payment_due_message(sub: dict, period_start: date) -> str:
    label = f"{sub['room']}호 " if sub.get("room") else ""
    return (
        f"[정기 주차 미납] {label}{sub['plate_number']} 정기 주차 결제가 필요합니다 "
        f"(이번 결제일: {period_start.isoformat()})."
    )


def check_payments(conn: sqlite3.Connection, today: date | None = None) -> dict:
    """Scans active subscriptions and queues a reminder for anyone unpaid past their due date.

    Billing is anchored to each subscription's own contract-date anniversary
    (see _current_period_start), not the calendar month. Once due, an unpaid
    subscription is re-flagged once per day until a payment is recorded for
    the current period.

    Args:
        conn: Open database connection.
        today: Override for "today" (used in tests); defaults to date.today().

    Returns:
        dict: {"checked": <active subscriptions scanned>, "queued": <notifications queued>}
    """
    today = today or date.today()
    active = list_subscriptions(conn, status="active")
    queued = 0
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for sub in active:
        start = _parse_date(sub["start_date"], "start_date")
        period_start = _current_period_start(start, today)
        if period_start < start:
            continue  # not yet due for the first time

        last_paid = _parse_date(sub["last_paid_date"], "last_paid_date") if sub.get("last_paid_date") else None
        if last_paid and last_paid >= period_start:
            continue  # already paid for the current period

        cursor = conn.execute(
            "INSERT OR IGNORE INTO notifications_outbox "
            "(subscription_id, kind, days_before, message, created_at) "
            "VALUES (?, ?, 0, ?, ?)",
            (
                sub["id"], f"payment_due:{today.isoformat()}",
                _payment_due_message(sub, period_start), created_at,
            ),
        )
        queued += cursor.rowcount

    conn.commit()
    return {"checked": len(active), "queued": queued}
