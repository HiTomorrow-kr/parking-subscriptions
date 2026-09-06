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
    end_date: str,
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
        end_date: Subscription end date (YYYY-MM-DD).
        room: Optional room/guest identifier.
        guest_name: Optional guest name.
        monthly_fee: Optional monthly fee amount.
        created_by: Identifier of who registered this (bot-specific user id).

    Returns:
        dict: The newly created subscription record.

    Raises:
        ValueError: If dates are malformed or end_date is not after start_date.
    """
    plate_number = (plate_number or "").strip()
    if not plate_number:
        raise ValueError("plate_number is required")

    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")
    if end <= start:
        raise ValueError("end_date must be after start_date")

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
            end.isoformat(),
            monthly_fee,
            created_by,
            created_at,
        ),
    )
    conn.commit()
    return get(conn, cursor.lastrowid)


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


def list_subscriptions(conn: sqlite3.Connection, status: str | None = None) -> list[dict]:
    """Lists subscriptions, optionally filtered by status.

    Args:
        conn: Open database connection.
        status: One of 'active' / 'expired' / 'cancelled', or None for all.

    Returns:
        list[dict]: Matching subscription records, most recent first.
    """
    if status:
        rows = conn.execute(
            "SELECT * FROM subscriptions WHERE status = ? ORDER BY id DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM subscriptions ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


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
    label = f"{sub['room']} " if sub.get("room") else ""
    if days_left == 0:
        return f"[정기 주차 알림] {label}{sub['plate_number']} 정기 주차권이 오늘({sub['end_date']}) 만료됩니다."
    return (
        f"[정기 주차 알림] {label}{sub['plate_number']} 정기 주차권이 "
        f"{sub['end_date']}에 만료됩니다 ({days_left}일 남음)."
    )


def _expired_message(sub: dict) -> str:
    label = f"{sub['room']} " if sub.get("room") else ""
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
