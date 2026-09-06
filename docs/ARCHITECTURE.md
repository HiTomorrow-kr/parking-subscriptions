# 아키텍처 (Architecture)

## 프로그램 개요

parking-subscriptions는 정기(월) 주차권의 등록, 조회, 취소, 만료 감지를 처리하는 독립 프로그램이다. 텔레그램/디스코드 등 메시징 플랫폼과 무관하며, CLI와 라이브러리 인터페이스로 여러 오케스트레이터가 구동한다.

## 데이터 모델

- subscriptions: 차량번호, 방/투숙객, 시작일/종료일(선택, 없으면 취소 전까지 계속 갱신되는 무기한 구독), 요금, 상태(active/expired/cancelled)
- notifications_outbox: 만료 알림 큐. UNIQUE(subscription_id, kind, days_before)로 중복 방지

## 만료 판정 로직

check-expiry는 활성 구독을 스캔해 종료일 기준 7/3/1/0일 전에는 임박 알림을, 종료일 경과 시 만료 알림과 상태 전환(expired)을 큐에 적재한다.

## 인터페이스

- CLI(python -m parking_subscriptions): register/list/deactivate/check-expiry, 결과는 JSON 한 줄
- 라이브러리(parking_subscriptions.outbox): 알림 큐 원자적 클레임(`claim_unsent`, 조회+발송완료 처리를 한 트랜잭션으로) — 동시 호출자가 있을 수 있는 오케스트레이터는 이걸 써야 중복 발송을 피할 수 있다

## 연동

오케스트레이터는 동일 서버에서 PYTHONPATH로 이 저장소를 참조한다. SQLite 경로는 이 저장소가 자체 관리(기본값 `data/parking.db`)하므로 오케스트레이터는 별도로 알 필요 없음 — 재정의가 필요할 때만 PARKING_SUBSCRIPTIONS_DB_PATH를 지정. register/list/deactivate/check-expiry는 서브프로세스, 알림 전달은 outbox 모듈 직접 임포트.
