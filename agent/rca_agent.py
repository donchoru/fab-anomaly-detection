"""원인분석(RCA) 에이전트 — 추후 확장용 스텁.

현재는 이상감지에만 집중. RCA는 아래 패턴으로 추후 구현 가능:

1. anomalies 테이블에 rca_status 컬럼 추가 (pending/processing/done/failed)
2. detection_agent가 이상 INSERT 시 rca_status='pending' 설정
3. 본 모듈의 poll_and_analyze()를 스케줄러에 30초 간격으로 등록
4. pending 이상을 폴링 → ReAct 루프로 근본원인 분석 → DB UPDATE

스케줄러 등록 예시 (main.py):
    from agent.rca_agent import poll_and_analyze
    scheduler.add_job(poll_and_analyze, "interval", seconds=30, id="rca_poll")
"""
