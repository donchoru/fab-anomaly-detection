# FAB 이상감지 — 반도체 공정 AI 이상감지 시스템

## 개요
- **목적**: 반도체 FAB 폐쇄망에서 물류/WIP/설비 이상을 AI가 감지
- **포트**: API 8600, Streamlit 3009
- **DB**: Oracle (운영) / SQLite (시뮬레이터)
- **LLM**: OpenAI 호환 API (사내 LLM 또는 Ollama)

## 아키텍처 (v3.0 — 이상감지 집중)
```
Detection Scheduler (매 5분)
  → 규칙 SQL 실행 → 임계치 비교
  → 위반 시 LLM 에이전트가 실제 이상 판단
  → DB INSERT (anomalies 테이블)
  → Streamlit 대시보드에서 조회
```

### 추후 확장
- **RCA (근본원인분석)**: agent/rca_agent.py 참고. DB 폴링 방식으로 구현 가능.
- **알림**: alert/router.py 참고. DB 기록 → 외부 채널 연동.
- **에스컬레이션**: alert/escalation.py 참고.

## 규칙 관리 — YAML 기반
- **`rules.yaml`이 규칙의 원본** (source of truth)
- 서버 시작 시: `rules.yaml` → DB 자동 동기화 (`rules/loader.py`)
- UI에서 규칙 추가/수정/삭제 → DB 변경 → `rules.yaml` 자동 갱신
- 시뮬레이터도 `rules.yaml`에서 규칙 로드

## 핵심 파일
| 파일 | 역할 |
|------|------|
| `rules.yaml` | **규칙 원본** — 이상감지 규칙 정의 |
| `rules/loader.py` | YAML ↔ DB 동기화 |
| `main.py` | FastAPI + APScheduler 진입점 |
| `agent/detection_agent.py` | 이상감지 (ReAct) → DB INSERT |
| `detection/evaluator.py` | 규칙 평가 → 에이전트 호출 |
| `detection/scheduler.py` | 감지 사이클 오케스트레이션 |
| `rules/engine.py` | threshold/delta/absence/llm 평가 |
| `api/rules.py` | 규칙 CRUD + AI 자연어 생성 + YAML 동기화 |
| `db/queries.py` | 모든 DB 쿼리 |
| `streamlit_app/app.py` | 4페이지 대시보드 |
| `simulator/runner.py` | SQLite 시뮬레이터 |

## DB 테이블 (sentinel_ 접두사 없음)
- `detection_rules` — 감지 규칙
- `anomalies` — 감지된 이상
- `correlations` — 상관 그룹 (추후)
- `detection_cycles` — 감지 사이클 로그

## 시뮬레이터 실행
```bash
python -m simulator.runner           # API (:8600)
streamlit run streamlit_app/app.py   # 대시보드 (:3009)
```

## 주의사항
- SQLite 시뮬레이터는 Oracle SQL을 `simulator/sql_compat.py`로 자동 변환
- Python 3.14에서 SQLite WAL + executescript 충돌 → 개별 execute 사용
- FETCH NEXT → LIMIT 변환 시 리터럴 숫자 + 바인드 변수 모두 처리 필요
