# 아키텍처 (Architecture)

한국어 | [English](ARCHITECTURE.md)

## 개요

parking-subscriptions는 정기(월) 주차권의 등록, 조회, 결제 추적, 취소, 만료/미납 알림을 처리하는 독립 프로그램이다. 텔레그램/디스코드 등 메시징 플랫폼과 무관하며, CLI와 라이브러리 인터페이스로 여러 오케스트레이터가 구동한다.

## 데이터 모델

- `subscriptions` — 차량번호, 방, 투숙객 이름, 시작일/종료일(종료일은 선택이며, 없으면 취소 전까지 계속 갱신되는 무기한 구독), 월 요금, 상태(`active`/`expired`/`cancelled`), `created_by`, `last_paid_date`. 부분 유니크 인덱스로 방당 활성 구독 하나만 허용하며, 방이 배정되지 않은(`NULL`) 행은 이 제약에서 예외다.
- `notifications_outbox` — 발송 대기 중인 알림 큐. `UNIQUE(subscription_id, kind, days_before)`로 같은 알림이 중복 적재되는 걸 막는다.

## 비즈니스 로직

- **만료 (`check-expiry`)** — 활성 구독을 스캔해 종료일 기준 7/3/1/0일 전에는 임박 알림을 큐에 적재하고, 종료일이 지나면 만료 알림을 적재하면서 상태를 `expired`로 전환한다. 종료일이 없는 무기한 구독은 대상에서 제외된다.
- **결제 추적 (`pay`, `check-payments`)** — 결제 한 건은 고정된 달력 월이나 계약일 그리드가 아니라, 결제한 날짜로부터 정확히 한 달을 커버한다. 그래서 며칠 일찍 결제해도 다음 결제 주기로 인정된다. `check-payments`는 활성 구독을 스캔해 놓친 결제일마다 딱 한 번 미납 알림을 큐에 적재한다 — outbox 행이 결제일 자체를 키로 갖기 때문에, 아직 결제하지 않은 구독이라도 매일 새로 알림이 쌓이는 게 아니라 그 결제일에 대해 정확히 한 번만 알림이 생긴다.
- **조회** — `show`, `pay`, `deactivate`는 `--room`, `--plate`, `--id` 중 정확히 하나로 구독을 찾는다. 방 번호가 권장 식별자다 — 한 번 배정되면 고정불변이라 `register` → 조회 → `deactivate`로 이어지는 흐름에서 항상 같은 구독을 가리킨다. 같은 차량번호로 활성 구독이 여러 개면(방과 달리 차량번호는 DB 레벨에서 유일성이 강제되지 않는다) 차량번호 조회는 모호하다는 에러를 낸다.

## 인터페이스

- **CLI** (`python -m parking_subscriptions`) — `register`, `list`, `show`, `pay`, `deactivate`, `check-expiry`, `check-payments`. 모든 명령은 결과를 JSON 한 줄로 stdout에 출력한다: `{"ok": true, "data": ...}` 또는 `{"ok": false, "error": "..."}`, 종료 코드 0/1.
- **라이브러리** (`parking_subscriptions.outbox`) — 알림 큐를 원자적으로 클레임하는 `claim_unsent`(조회와 발송완료 처리를 한 트랜잭션으로 실행). 주기적으로 도는 drain 작업과 수동 "지금 확인" 액션처럼 동시에 호출될 수 있는 오케스트레이터라면, 별도의 `fetch_unsent()`/`mark_sent()` 호출 대신 반드시 이걸 써야 같은 알림이 두 번 발송되는 걸 막을 수 있다.

## 연동

오케스트레이터는 같은 서버에서 `PYTHONPATH`로 이 저장소를 참조한다 — 별도 설치 과정이 없다. SQLite 경로는 이 저장소가 자체 관리하며 기본값은 `data/parking.db`이므로 오케스트레이터가 따로 알 필요는 없다. 재정의가 정말 필요할 때(테스트, 또는 의도적으로 별도 DB가 필요한 배포)만 `PARKING_SUBSCRIPTIONS_DB_PATH`를 지정한다. `register`/`list`/`deactivate`/`check-expiry`/`check-payments`는 서브프로세스로 실행하고, 알림 발송은 `outbox` 모듈을 직접 임포트한다.
