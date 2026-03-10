"""에스컬레이션 — 추후 확장용 스텁.

미확인 이상에 대한 재알림. RCA + 알림 시스템 구현 후 활성화.

1. alert_routes 테이블에서 escalation_delay_min > 0인 규칙 조회
2. detected 상태로 delay_min 이상 경과한 이상 조회
3. 재알림 발송

스케줄러 등록 예시:
    from alert.escalation import check_escalations
    scheduler.add_job(check_escalations, "interval", seconds=60, id="escalation")
"""
