# parking-subscriptions

한국어 | [English](../README.md)

parking-subscriptions는 정기(월) 주차권의 등록, 추적, 만료 알림을 처리한다. 메시징 플랫폼과 무관한 독립 프로그램이라, 어떤 봇(텔레그램, 디스코드 등)이든 서브프로세스나 라이브러리로 구동할 수 있다.

## 주요 기능

- SQLite 기반 정기 주차권 등록/조회/취소
- 결제 추적: 주차권별 결제일을 기록하고, `list`에서 이번 달 결제 여부를 알려줌
- 만료 7/3/1/0일 전 및 만료 후 자동 스캔, 중복 없는 알림 큐잉
- 미납 자동 알림: 계약일(방 배정일) 기준으로 매달 돌아오는 결제일에 맞춰 확인하며(달력상 월이 아님), 결제 안 된 상태면 결제될 때까지 매일 재알림
- 설치 단계 없음 — Python 3.11+ 환경에서 PYTHONPATH만으로 동작

## 사용법

```bash
python -m parking_subscriptions register --plate 12가3456 --start-date 2026-09-01 --end-date 2026-10-01 --room 101 --guest-name 홍길동 --monthly-fee 150000
python -m parking_subscriptions list --status active
python -m parking_subscriptions pay --room 101 --date 2026-09-05  # --date 생략 시 오늘 날짜
python -m parking_subscriptions deactivate --room 101
python -m parking_subscriptions check-expiry
python -m parking_subscriptions check-payments
```

`--end-date`를 생략하면 종료일 없이 등록되며, 취소(`deactivate`)하기 전까지 계속 활성 상태로 유지되고 만료 알림 대상에서 제외된다.

모든 명령은 결과를 JSON 한 줄로 stdout에 출력한다: `{"ok": true, "data": ...}` 또는 `{"ok": false, "error": "..."}`, 종료 코드 0/1. 데이터는 기본적으로 이 저장소 안의 `data/parking.db`에 저장되며, `PARKING_SUBSCRIPTIONS_DB_PATH`는 이를 재정의할 때만(테스트, 별도 DB가 필요한 배포 등) 지정한다.

## 연동

오케스트레이터는 이 저장소를 같은 서버에 클론하고 `PYTHONPATH`에 추가한다:

```python
import sys
sys.path.insert(0, "/path/to/parking-subscription-worker")

from parking_subscriptions.outbox import fetch_unsent, mark_sent
```

## 문서

설계 상세는 [docs/ARCHITECTURE.md](ARCHITECTURE.md) 참고.
