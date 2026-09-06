# parking-subscriptions

[한국어](docs/readme-ko.md) | English

parking-subscriptions manages monthly parking subscriptions: registration, tracking, and expiry notifications. It is a standalone program with no messaging-platform dependency, so any bot (Telegram, Discord, ...) can drive it as a subprocess or library.

## Key Features

- Register, list, and cancel monthly parking subscriptions, backed by SQLite
- Payment tracking: record a payment date per subscription; `list` reports whether it's currently paid up
- Automatic expiry scanning (7/3/1/0 days before, and past-due) with duplicate-safe notification queueing
- Automatic payment-due reminders: each payment covers exactly one month forward from when it was made (paying a few days early still counts for the upcoming period); once a due date is missed, exactly one reminder is queued for it — not a fresh one every day — until a payment is recorded
- No install step — works via PYTHONPATH on any host with Python 3.11+

## Usage

```bash
python -m parking_subscriptions register --plate 12가3456 --start-date 2026-09-01 --end-date 2026-10-01 --room 101 --guest-name 홍길동 --monthly-fee 150000
python -m parking_subscriptions list --status active
python -m parking_subscriptions show --room 101
python -m parking_subscriptions pay --room 101 --date 2026-09-05  # --date defaults to today
python -m parking_subscriptions deactivate --room 101
python -m parking_subscriptions check-expiry
python -m parking_subscriptions check-payments
```

Omit `--end-date` to register an open-ended subscription: it stays active and is excluded from expiry checks until explicitly cancelled with `deactivate`.

`show`, `pay`, and `deactivate` accept `--room`, `--plate`, or `--id` interchangeably (exactly one). Room is the recommended identifier: it's a fixed, permanent assignment (one room = one car), so `register` rejects a room that already has an active subscription.

Every command prints a single JSON line to stdout: `{"ok": true, "data": ...}` or `{"ok": false, "error": "..."}`, exit code 0/1. Data lives at `data/parking.db` inside this repo by default; set `PARKING_SUBSCRIPTIONS_DB_PATH` only to override it (e.g. tests, or a deployment that intentionally needs a separate database).

## Integration

An orchestrator clones this repo on the same host and adds it to `PYTHONPATH`:

```python
import sys
sys.path.insert(0, "/path/to/parking-subscription-worker")

from parking_subscriptions.outbox import fetch_unsent, mark_sent
```

## Documentation

- [System Architecture](docs/ARCHITECTURE.md)
