import argparse
import json
import sys

from . import db, subscriptions


def _print_ok(data) -> None:
    print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))


def _print_err(message: str) -> None:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))


def _cmd_register(args: argparse.Namespace) -> int:
    conn = db.connect()
    try:
        sub = subscriptions.register(
            conn,
            plate_number=args.plate,
            start_date=args.start_date,
            end_date=args.end_date,
            room=args.room,
            guest_name=args.guest_name,
            monthly_fee=args.monthly_fee,
            created_by=args.created_by,
        )
    except ValueError as e:
        _print_err(str(e))
        return 1
    _print_ok(sub)
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    conn = db.connect()
    rows = subscriptions.list_subscriptions(conn, status=args.status)
    _print_ok(rows)
    return 0


def _resolve_id(conn, args: argparse.Namespace) -> int:
    """Resolves --id/--plate/--room (mutually exclusive) to a subscription id."""
    if args.room is not None:
        return subscriptions.find_active_by_room(conn, args.room)["id"]
    if args.plate is not None:
        return subscriptions.find_active_by_plate(conn, args.plate)["id"]
    return args.id


def _cmd_deactivate(args: argparse.Namespace) -> int:
    conn = db.connect()
    try:
        sub = subscriptions.deactivate(conn, _resolve_id(conn, args))
    except ValueError as e:
        _print_err(str(e))
        return 1
    _print_ok(sub)
    return 0


def _cmd_pay(args: argparse.Namespace) -> int:
    conn = db.connect()
    try:
        sub = subscriptions.mark_paid(conn, _resolve_id(conn, args), args.date)
    except ValueError as e:
        _print_err(str(e))
        return 1
    _print_ok(sub)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    conn = db.connect()
    try:
        sub = subscriptions.get_with_status(conn, _resolve_id(conn, args))
    except ValueError as e:
        _print_err(str(e))
        return 1
    _print_ok(sub)
    return 0


def _cmd_check_expiry(args: argparse.Namespace) -> int:
    conn = db.connect()
    result = subscriptions.check_expiry(conn)
    _print_ok(result)
    return 0


def _cmd_check_payments(args: argparse.Namespace) -> int:
    conn = db.connect()
    result = subscriptions.check_payments(conn)
    _print_ok(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="parking-subscriptions")
    sub = parser.add_subparsers(dest="command", required=True)

    p_register = sub.add_parser("register", help="Register a new monthly parking subscription")
    p_register.add_argument("--plate", required=True)
    p_register.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    p_register.add_argument("--end-date", help="YYYY-MM-DD (omit for an open-ended subscription)")
    p_register.add_argument("--room", required=True)
    p_register.add_argument("--guest-name")
    p_register.add_argument("--monthly-fee", type=int)
    p_register.add_argument("--created-by")
    p_register.set_defaults(func=_cmd_register)

    p_list = sub.add_parser("list", help="List subscriptions")
    p_list.add_argument("--status", choices=["active", "expired", "cancelled"])
    p_list.set_defaults(func=_cmd_list)

    p_deactivate = sub.add_parser("deactivate", help="Cancel a subscription")
    g_deactivate = p_deactivate.add_mutually_exclusive_group(required=True)
    g_deactivate.add_argument("--id", type=int)
    g_deactivate.add_argument("--plate")
    g_deactivate.add_argument("--room")
    p_deactivate.set_defaults(func=_cmd_deactivate)

    p_pay = sub.add_parser("pay", help="Record a payment for a subscription")
    g_pay = p_pay.add_mutually_exclusive_group(required=True)
    g_pay.add_argument("--id", type=int)
    g_pay.add_argument("--plate")
    g_pay.add_argument("--room")
    p_pay.add_argument("--date", help="YYYY-MM-DD (defaults to today)")
    p_pay.set_defaults(func=_cmd_pay)

    p_show = sub.add_parser("show", help="Show full details for a subscription")
    g_show = p_show.add_mutually_exclusive_group(required=True)
    g_show.add_argument("--id", type=int)
    g_show.add_argument("--plate")
    g_show.add_argument("--room")
    p_show.set_defaults(func=_cmd_show)

    p_check = sub.add_parser("check-expiry", help="Scan subscriptions and queue expiry notifications")
    p_check.set_defaults(func=_cmd_check_expiry)

    p_check_pay = sub.add_parser("check-payments", help="Scan subscriptions and queue payment-due reminders")
    p_check_pay.set_defaults(func=_cmd_check_payments)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
