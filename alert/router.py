"""알림 라우터 — 추후 확장용 스텁.

현재는 이상감지에만 집중. 알림은 아래 패턴으로 추후 구현 가능:

1. RCA 분석 완료 시 send_alert() 호출
2. 알림 메시지를 포매팅하여 alert_history 테이블에 INSERT
3. 외부 채널 (이메일, 메신저 등) 연동 가능

테이블: alert_history (anomaly_id, channel, recipient, message, sent_at, delivered)
"""
