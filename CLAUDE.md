# FAB-SENTINEL — 반도체 FAB AI 이상감지 시스템

## 개요
- **목적**: 반도체 FAB 폐쇄망에서 물류/WIP/설비 이상을 AI가 감지 + 근본원인 분석
- **포트**: API 8600, Streamlit 3009
- **DB**: Oracle (운영) / SQLite (시뮬레이터)
- **LLM**: OpenAI 호환 API (사내 LLM 또는 Ollama)

## 아키텍처 (v2.0 — DB 폴링)
```
Detection → DB INSERT (rca_status='pending')
RCA Poller (30초) → DB 폴링 → 분석 → DB UPDATE (rca_status='done') + 알림 INSERT
Streamlit → DB 조회 → 표시
```
토픽 버스 없음. 모든 것이 DB + Streamlit.

## 핵심 파일
| 파일 | 역할 |
|------|------|
| `main.py` | FastAPI + APScheduler 진입점 |
| `agent/detection_agent.py` | 이상감지 (ReAct) → DB INSERT |
| `agent/rca_agent.py` | 근본원인분석 (ReAct) → DB 폴링 |
| `alert/router.py` | 알림 → DB 기록 (dashboard 채널) |
| `detection/evaluator.py` | 규칙 평가 → 에이전트 호출 |
| `detection/scheduler.py` | 감지 사이클 오케스트레이션 |
| `rules/engine.py` | threshold/delta/absence/llm 평가 |
| `api/rules.py` | 규칙 CRUD + AI 자연어 생성 |
| `db/queries.py` | 모든 DB 쿼리 (RCA 폴링 포함) |
| `streamlit_app/app.py` | 4페이지 대시보드 |
| `simulator/runner.py` | SQLite 시뮬레이터 |

## 시뮬레이터 실행
```bash
python -m simulator.runner           # API (:8600)
streamlit run streamlit_app/app.py   # 대시보드 (:3009)
```

## 규칙
- 규칙 유형: threshold, delta, absence, llm
- 자연어 → AI 규칙 생성: `POST /api/rules/generate`
- 테이블 스키마: `POST /api/rules/schema/tables`
- MES 테이블 14개 (mes_conveyor_status ~ mes_equipment_alarms)

## 주의사항
- SQLite 시뮬레이터는 Oracle SQL을 `simulator/sql_compat.py`로 자동 변환
- Python 3.14에서 SQLite WAL + executescript 충돌 → 개별 execute 사용
- FETCH NEXT → LIMIT 변환 시 리터럴 숫자 + 바인드 변수 모두 처리 필요
- Streamlit secrets: `streamlit_app/.streamlit/secrets.toml`
