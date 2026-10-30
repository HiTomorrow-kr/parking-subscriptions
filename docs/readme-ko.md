# parking-subscriptions

한국어 | [English](../README.md)

parking-subscriptions는 정기(월) 주차권의 등록, 결제, 만료를 관리한다.

## 주요 기능

- 정기 주차권 등록, 조회, 취소
- 결제를 기록하고 결제 완료 상태인지 확인
- 만료 전과 결제일에 보낼 알림을 큐에 쌓음

## 시작하기

```bash
git clone https://github.com/HiTomorrow-kr/parking-subscriptions.git
cd parking-subscriptions
pip install -e .
```

## 사용법

```bash
python -m parking_subscriptions register --plate 12가3456 --start-date 2026-09-01 --end-date 2026-10-01 --room 101 --guest-name 홍길동 --monthly-fee 150000
python -m parking_subscriptions list --status active
python -m parking_subscriptions show --room 101
python -m parking_subscriptions update --room 101 --monthly-fee 160000 --end-date 2026-11-01
python -m parking_subscriptions pay --room 101 --date 2026-09-05  # --date 생략 시 오늘 날짜
python -m parking_subscriptions deactivate --room 101
python -m parking_subscriptions check-expiry    # 만료가 다가온 주차권의 알림을 큐에 쌓음
python -m parking_subscriptions check-payments  # 결제일이 된 주차권의 알림을 큐에 쌓음
python -m parking_subscriptions prune-outbox --older-than-days 30  # 30일이 지난 발송 완료 알림을 삭제
```

- `--end-date`를 생략하면 종료일 없이 등록된다. `deactivate`로 취소하기 전까지 계속 활성 상태로 유지된다.
- `show`, `update`, `pay`, `deactivate`는 `--room`, `--plate`, `--id` 중 하나를 받는다. 한 방에는 활성 구독을 하나만 둘 수 있으므로 `--room`을 권장한다.

## 라이선스

MIT — [LICENSE](../LICENSE) 참고.
