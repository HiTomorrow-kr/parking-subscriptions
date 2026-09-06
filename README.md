# parking-subscriptions

[한국어](docs/readme-ko.md) | English

parking-subscriptions manages monthly parking subscriptions: registration, tracking, and expiry notifications. It is a standalone program with no messaging-platform dependency, so any bot (Telegram, Discord, ...) can drive it as a subprocess or library.

## Key Features

- Register, list, and cancel monthly parking subscriptions, backed by SQLite
- Automatic expiry scanning (7/3/1/0 days before, and past-due) with duplicate-safe notification queueing
- No install step — works via PYTHONPATH on any host with Python 3.11+

## Usage

```bash
python -m parking_subscriptions register --plate 12가3456 --start-date 2026-09-01 --end-date 2026-10-01 --room 101 --guest-name 홍길동 --monthly-fee 150000
python -m parking_subscriptions list --status active
python -m parking_subscriptions deactivate --id 3
python -m parking_subscriptions check-expiry
```

Omit `--end-date` to register an open-ended subscription: it stays active and is excluded from expiry checks until explicitly cancelled with `deactivate`.

Every command prints a single JSON line to stdout: `{"ok": true, "data": ...}` or `{"ok": false, "error": "..."}`, exit code 0/1. Set `PARKING_SUBSCRIPTIONS_DB_PATH` to the shared SQLite file path before running any command.

## Integration

An orchestrator clones this repo on the same host and adds it to `PYTHONPATH`:

```python
import sys
sys.path.insert(0, "/path/to/parking-subscription-worker")

from parking_subscriptions.outbox import fetch_unsent, mark_sent
```

## Documentation

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design details.
