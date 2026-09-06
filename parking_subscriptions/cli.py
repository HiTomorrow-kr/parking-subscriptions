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


def _cmd_deactivate(args: argparse.Namespace) -> int:
    conn = db.connect()
    try:
        sub = subscriptions.deactivate(conn, args.id)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="parking-subscriptions")
    sub = parser.add_subparsers(dest="command", required=True)

    p_register = sub.add_parser("register", help="Register a new monthly parking subscription")
    p_register.add_argument("--plate", required=True)
    p_register.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    p_register.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    p_register.add_argument("--room")
    p_register.add_argument("--guest-name")
    p_register.add_argument("--monthly-fee", type=int)
    p_register.add_argument("--created-by")
    p_register.set_defaults(func=_cmd_register)

    p_list = sub.add_parser("list", help="List subscriptions")
    p_list.add_argument("--status", choices=["active", "expired", "cancelled"])
    p_list.set_defaults(func=_cmd_list)

    p_deactivate = sub.add_parser("deactivate", help="Cancel a subscription")
    p_deactivate.add_argument("--id", type=int, required=True)
    p_deactivate.set_defaults(func=_cmd_deactivate)

    p_check = sub.add_parser("check-expiry", help="Scan subscriptions and queue expiry notifications")
    p_check.set_defaults(func=_cmd_check_expiry)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RuntimeError as e:
        # e.g. PARKING_SUBSCRIPTIONS_DB_PATH missing
        _print_err(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
