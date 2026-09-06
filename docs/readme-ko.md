# parking-subscriptions

한국어 | [English](../README.md)

parking-subscriptions는 정기(월) 주차권의 등록, 추적, 만료 알림을 처리한다. 메시징 플랫폼과 무관한 독립 프로그램이라, 어떤 봇(텔레그램, 디스코드 등)이든 서브프로세스나 라이브러리로 구동할 수 있다.

## 주요 기능

- SQLite 기반 정기 주차권 등록/조회/취소
- 결제 추적: 주차권별 결제일을 기록하고, `list`에서 현재 결제 완료 상태인지 알려줌
- 만료 7/3/1/0일 전 및 만료 후 자동 스캔, 중복 없는 알림 큐잉
- 미납 자동 알림: 결제 한 번이 그 날짜로부터 정확히 한 달을 커버함(며칠 일찍 내도 다음 결제 주기로 인정). 결제일을 놓치면 그 결제일에 대해 딱 한 번만 알림이 쌓이고, 결제 전까지 매일 재알림하지 않음
- 설치 단계 없음 — Python 3.11+ 환경에서 PYTHONPATH만으로 동작

## 사용법

```bash
python -m parking_subscriptions register --plate 12가3456 --start-date 2026-09-01 --end-date 2026-10-01 --room 101 --guest-name 홍길동 --monthly-fee 150000
python -m parking_subscriptions list --status active
python -m parking_subscriptions show --room 101
python -m parking_subscriptions pay --room 101 --date 2026-09-05  # --date 생략 시 오늘 날짜
python -m parking_subscriptions deactivate --room 101
python -m parking_subscriptions check-expiry
python -m parking_subscriptions check-payments
```

`--end-date`를 생략하면 종료일 없이 등록되며, 취소(`deactivate`)하기 전까지 계속 활성 상태로 유지되고 만료 알림 대상에서 제외된다.

`show`, `pay`, `deactivate`는 `--room`, `--plate`, `--id` 중 정확히 하나를 받는다. 방 번호가 권장 식별자다 — 한 번 배정되면 고정불변(방 하나당 차량 하나)이라, `register`는 이미 활성 구독이 있는 방으로 재등록을 거부한다.

모든 명령은 결과를 JSON 한 줄로 stdout에 출력한다: `{"ok": true, "data": ...}` 또는 `{"ok": false, "error": "..."}`, 종료 코드 0/1. 데이터는 기본적으로 이 저장소 안의 `data/parking.db`에 저장되며, `PARKING_SUBSCRIPTIONS_DB_PATH`는 이를 재정의할 때만(테스트, 별도 DB가 필요한 배포 등) 지정한다.

## 연동

오케스트레이터는 이 저장소를 같은 서버에 클론하고 `PYTHONPATH`에 추가한다:

```python
import sys
sys.path.insert(0, "/path/to/parking-subscription-worker")

from parking_subscriptions.outbox import fetch_unsent, mark_sent
```

## 문서

- [시스템 아키텍처](ARCHITECTURE.md)
