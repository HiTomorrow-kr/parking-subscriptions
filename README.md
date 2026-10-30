# parking-subscriptions

[한국어](docs/readme-ko.md) | English

parking-subscriptions keeps track of monthly parking subscriptions: registration, payments and expiry.

## Key Features

- Register, list and cancel monthly parking subscriptions
- Record each payment and see whether a subscription is paid up
- Queue notifications before a subscription expires and when a payment is due

## Getting Started

```bash
git clone https://github.com/HiTomorrow-kr/parking-subscriptions.git
cd parking-subscriptions
pip install -e .
```

## Usage

```bash
python -m parking_subscriptions register --plate 12가3456 --start-date 2026-09-01 --end-date 2026-10-01 --room 101 --guest-name 홍길동 --monthly-fee 150000
python -m parking_subscriptions list --status active
python -m parking_subscriptions show --room 101
python -m parking_subscriptions update --room 101 --monthly-fee 160000 --end-date 2026-11-01
python -m parking_subscriptions pay --room 101 --date 2026-09-05  # --date defaults to today
python -m parking_subscriptions deactivate --room 101
python -m parking_subscriptions check-expiry    # queue notifications for subscriptions about to expire
python -m parking_subscriptions check-payments  # queue notifications for payments that are due
python -m parking_subscriptions prune-outbox --older-than-days 30  # delete delivered notifications older than 30 days
```

- Omit `--end-date` to register without an end date. The subscription stays active until you run `deactivate`.
- `show`, `update`, `pay` and `deactivate` take one of `--room`, `--plate` or `--id`. Prefer `--room`: a room can have only one active subscription.

## License

MIT — see [LICENSE](LICENSE).
