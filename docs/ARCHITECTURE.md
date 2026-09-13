# Architecture

[한국어](architecture-ko.md) | English

## Overview

parking-subscriptions is a standalone program that manages monthly parking subscriptions: registration, lookup, payment tracking, cancellation, and expiry/payment-due notifications. It has no dependency on any messaging platform (Telegram, Discord, etc.) — any orchestrator can drive it through its CLI or import it as a library.

## Data Model

- `subscriptions` — plate number, room, guest name, start/end date (end date is optional; omitting it makes the subscription open-ended, renewing until explicitly cancelled), monthly fee, status (`active`/`expired`/`cancelled`), `created_by`, `last_paid_date`. A partial unique index enforces one active subscription per room; rooms with no assignment (`NULL`) are exempt.
- `notifications_outbox` — queued notifications awaiting delivery. `UNIQUE(subscription_id, kind, days_before)` keeps the same notification from being queued twice.

## Business Logic

- **Expiry (`check-expiry`)** — scans active subscriptions and queues an upcoming-expiry notification at 7/3/1/0 days before the end date; once the end date has passed, it queues an expired notification and flips the subscription's status to `expired`. Open-ended subscriptions (no end date) are skipped.
- **Payment tracking (`pay`, `check-payments`)** — each recorded payment covers exactly one month forward from the date it was made, not a fixed calendar month or a fixed contract-date grid, so paying a few days early still counts toward the upcoming period. `check-payments` scans active subscriptions and queues one payment-due reminder per missed due date; the outbox row is keyed on the due date itself, so a still-unpaid subscription gets exactly one reminder for that date rather than a fresh one every day.
- **Lookup** — `show`, `pay`, and `deactivate` resolve a subscription via `--room`, `--plate`, or `--id` (exactly one). Room is the recommended identifier: it's a fixed, permanent assignment, so it round-trips cleanly through `register` → lookup → `deactivate`. Plate lookup can raise an ambiguity error if more than one active subscription shares a plate — only rooms are constrained to uniqueness at the database level.

## Interface

- **CLI** (`python -m parking_subscriptions`) — `register`, `list`, `show`, `pay`, `deactivate`, `check-expiry`, `check-payments`. Every command prints a single JSON line to stdout, `{"ok": true, "data": ...}` or `{"ok": false, "error": "..."}`, with exit code 0/1.
- **Library** (`parking_subscriptions.outbox`) — atomic notification-queue claiming (`claim_unsent`, fetch and mark-sent in a single transaction). An orchestrator with potentially concurrent callers (a periodic drain job and a manual "check now" action, say) must use this instead of separate `fetch_unsent()`/`mark_sent()` calls to avoid delivering the same notification twice.

## Integration

An orchestrator references this repository via `PYTHONPATH` on the same host — no install step required. The SQLite path is managed by this repository itself, defaulting to `data/parking.db`, so the orchestrator doesn't need to know about it; set `PARKING_SUBSCRIPTIONS_DB_PATH` only when an override is genuinely needed (tests, or a deployment that intentionally needs a separate database). `register`/`list`/`deactivate`/`check-expiry`/`check-payments` run as a subprocess; notification delivery imports the `outbox` module directly.
