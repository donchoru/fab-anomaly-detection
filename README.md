# FAB 이상감지 시스템

반도체 FAB 폐쇄망 환경에서 **물류 / 재공(WIP) / 설비** 이상을 AI 에이전트가 주기적으로 감지하여 대시보드로 제공하는 시스템.

오픈소스 프레임워크(LangChain 등) 없이, **OpenAI 호환 LLM + Oracle DB + 자체 ReAct 에이전트**로 구축했습니다.

> 시뮬레이터 포함 — Oracle 없이 **SQLite + 더미 데이터**로 즉시 실행 가능합니다.

---

## 핵심 기능

### 1. 규칙 기반 이상감지 (5분 주기)

등록된 규칙을 주기적으로 평가하여 이상을 감지합니다.

```
매 5분 (스케줄러)
  │
  ├─ 1. 활성 규칙 로드 (DB ← rules.yaml 동기화)
  │
  ├─ 2. 규칙별 도구 실행 + 평가
  │     ├─ threshold : 측정값 > 임계치?     (예: 컨베이어 부하율 > 90%)
  │     ├─ delta     : 변화율 > 임계치?     (예: WIP 1시간 변화율 > 30%)
  │     ├─ absence   : 데이터 없음?         (예: 30분간 반송 기록 없음)
  │     └─ llm       : AI에게 판단 위임     (예: ERROR AGV 비율 판단)
  │
  └─ 3. 위반 시 → AI 에이전트가 추가 조회 + 분석 → 이상 등록
```

### 2. AI 에이전트 (ReAct 패턴)

단순 임계치 초과가 아닌, **LLM이 15개 도구를 활용해 직접 판단**합니다.

```
[규칙 위반 감지]
  → 에이전트 호출 (ReAct, 최대 3라운드)
    → 도구 호출: get_conveyor_load() → 부하율 확인
    → 도구 호출: get_bottleneck_zones() → 병목 여부 확인
    → 도구 호출: get_zone_transfer_history() → 최근 반송 이력
    → RAG 검색: 과거 유사 사고 사례 참조
    → 최종 판단: "LINE03-ZONE-A 컨베이어 과부하 및 병목 발생"
```

### 3. RAG 전문지식

이상감지 시 **반도체 FAB 도메인 전문지식**을 벡터 검색하여 LLM 판단에 활용합니다.

| 지식 파일 | 내용 |
|-----------|------|
| `equipment.md` | 알람 코드 분류 (A-5xx/3xx/2xx/V-1xx), 설비별 특성, 연쇄 영향 패턴 |
| `process.md` | TFT/CELL/MODULE 공정 순서, WIP 관리 기준, 에이징 LOT 판단 |
| `logistics.md` | 컨베이어 부하율 기준, AGV 가동률, 병목 판단/해소 방법 |
| `incidents.md` | 과거 사고 사례 4건 및 교훈 |

> 📁 `examples/rag-knowledge/` 에서 전문지식 예시를 확인할 수 있습니다.

### 4. YAML 기반 규칙 관리

`rules.yaml`이 규칙의 **원본(Source of Truth)**입니다.

```yaml
rules:
  - name: 컨베이어 부하율 과부하
    category: logistics
    check_type: threshold
    source_type: tool
    tool: get_conveyor_load
    tool_column: load_pct
    threshold_op: ">"
    warning_value: 85
    critical_value: 95
    llm_enabled: true
    llm_prompt: "컨베이어 부하율이 높습니다. 해당 존의 반송 이력과 병목 여부를 확인하세요."
```

- 서버 시작 시: `rules.yaml` → DB 자동 동기화
- UI에서 규칙 추가/수정/삭제 → DB 변경 → `rules.yaml` 자동 갱신

---

## 도구 (Tools) — 15개

규칙 평가 및 AI 에이전트가 사용하는 데이터 조회 도구입니다.

### 물류 (logistics) — 5개

| 도구 | 설명 | 주요 컬럼 |
|------|------|-----------|
| `get_conveyor_load` | 존별 컨베이어 부하율(%) | load_pct, carrier_count |
| `get_transfer_throughput` | 라인별 반송 처리량 | moves_1h, avg_time_sec |
| `get_bottleneck_zones` | 대기시간 초과 병목 존 | avg_wait, max_wait |
| `get_agv_utilization` | AGV/OHT 상태별 대수 및 비율 | pct, count |
| `get_zone_transfer_history` | 존별 최근 반송 이력 | — |

### 재공 (wip) — 5개

| 도구 | 설명 | 주요 컬럼 |
|------|------|-----------|
| `get_wip_levels` | 공정별 WIP 목표 대비 비율 | wip_ratio_pct, current_wip |
| `get_flow_balance` | 공정별 유입/유출 밸런스 | net_wip, inflow, outflow |
| `get_queue_length` | 스텝별 대기 LOT 수 | queue_count, avg_wait_min |
| `get_aging_lots` | 기준시간 초과 장기 체류 LOT | hours_in_step, _count |
| `get_wip_trend` | 시간별 WIP 변화 트렌드 | total_wip |

### 설비 (equipment) — 5개

| 도구 | 설명 | 주요 컬럼 |
|------|------|-----------|
| `get_equipment_status` | 설비 현재 상태 (RUN/IDLE/DOWN/PM) | _count |
| `get_equipment_utilization` | 설비 가동률(%) | utilization_pct, down_minutes |
| `get_unscheduled_downs` | 비계획정지 이력 | down_min, _count |
| `get_pm_schedule` | 예방보전(PM) 일정 및 지연 | _count |
| `get_equipment_alarms` | 설비 알람 이력 | _count |

---

## 규칙 생성 — 2가지 방식

Streamlit 대시보드에서 규칙을 추가할 때 2가지 패턴을 선택할 수 있습니다.

### 패턴 1: 📊 임계치 감시

도구를 연결하고, **감시할 컬럼 + 경고/위험 임계치**를 직접 설정합니다.

```
규칙명: "컨베이어 부하율 과부하"
  → 도구: get_conveyor_load (컨베이어 부하율)
  → 감시 컬럼: load_pct (부하율 %)
  → 조건: > 85 (경고) / > 95 (위험)
```

### 패턴 2: 🤖 AI 판단

도구를 연결하고, **자연어로 이상 조건을 설명**하면 AI가 매 사이클마다 판단합니다.

```
규칙명: "AGV 가동률 저하"
  → 도구: get_agv_utilization (AGV/OHT 가동률)
  → 이상 조건: "ERROR 상태 AGV의 비율을 확인해.
               전체의 15% 이상이면 경고, 30% 이상이면 위험으로 판단해."
```

---

## 이상 상태 흐름

```
감지됨 (detected) ──→ 처리중 (in_progress) ──→ 해결 (resolved)
```

| 상태 | 설명 |
|------|------|
| **감지됨** | AI가 이상을 감지하여 등록한 상태 |
| **처리중** | 담당자가 확인하고 조치 중인 상태 |
| **해결** | 조치 완료 |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                       FAB 이상감지 시스템                              │
│                                                                     │
│   rules.yaml ──→ DB 동기화                                          │
│                    │                                                 │
│   ┌────────────┐   │    ┌────────────────────┐                      │
│   │ Scheduler  │───┴───→│  Detection Agent   │                      │
│   │ (매 5분)   │        │  (ReAct + 15 Tools)│                      │
│   └────────────┘        └────────┬───────────┘                      │
│                                  │                                   │
│                    ┌─────────────┼─────────────┐                    │
│                    │ RAG 검색    │ 도구 호출    │                    │
│                    │ (Milvus)    │ (DB 조회)   │                    │
│                    └─────────────┼─────────────┘                    │
│                                  ▼                                   │
│                         ┌────────────────┐                          │
│                         │  Oracle DB     │                          │
│                         │  anomalies     │                          │
│                         └───────┬────────┘                          │
│                                 │                                    │
│   ┌─────────────────────────────┼───────────────────────────────┐   │
│   │          Streamlit 대시보드 (:3009)                          │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │   │
│   │  │ 대시보드  │ │ 이상목록  │ │ 규칙관리  │ │ 감지로그  │      │   │
│   │  │ KPI+차트 │ │ 상세+AI  │ │ 추가+테스트│ │ 사이클   │      │   │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│   ┌────────────┐    ┌────────────┐    ┌────────────────────┐       │
│   │ Rule Engine │    │ FastAPI    │    │ Oracle DB          │       │
│   │ 도구+임계치  │    │ :8600      │    │ MES + 감지 테이블   │       │
│   └────────────┘    └────────────┘    └────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 기술 스택

| 영역 | 기술 | 설명 |
|------|------|------|
| **언어** | Python 3.12+ | 비동기(asyncio) 기반 |
| **API 서버** | FastAPI + Uvicorn | 비동기 Web API (포트 8600) |
| **대시보드** | Streamlit | 4페이지 대시보드 (포트 3009) |
| **DB (운영)** | Oracle (oracledb thin) | Instant Client 없이 순수 Python 연결 |
| **DB (시뮬레이터)** | SQLite | Oracle SQL → SQLite 자동 변환 |
| **LLM** | OpenAI 호환 API | Gemini 2.0 Flash / 사내 LLM / Ollama |
| **벡터 검색** | Milvus (RAG) | 전문지식 임베딩 + 유사도 검색 |
| **스케줄러** | APScheduler | 감지 주기 스케줄링 |
| **AI 패턴** | ReAct (자체 구현) | LLM + Tool Use 에이전트 루프 |
| **차트** | Plotly | 대시보드 시각화 |

---

## 프로젝트 구조

```
fab-sentinel/
├── main.py                         # FastAPI + APScheduler 진입점 (:8600)
├── config.py                       # 환경설정 (DB, LLM, RAG, 스케줄)
├── rules.yaml                      # 규칙 원본 (Source of Truth)
├── requirements.txt
│
├── agent/                          # AI 에이전트
│   ├── llm_client.py               # OpenAI 호환 LLM 클라이언트
│   ├── tool_registry.py            # @registry.tool → JSON Schema 자동 생성
│   ├── agent_loop.py               # ReAct 에이전트 루프 (최대 3라운드)
│   ├── prompts.py                  # 시스템 프롬프트
│   ├── detection_agent.py          # 이상감지 에이전트 → DB INSERT
│   └── tools/                      # 데이터 조회 도구 (15개)
│       ├── logistics.py            # 컨베이어, 반송, 병목존, AGV
│       ├── wip.py                  # WIP, 흐름, 큐, 에이징, 트렌드
│       └── equipment.py            # 설비, 가동률, 정지, PM, 알람
│
├── rules/                          # 규칙 시스템
│   ├── models.py                   # Pydantic 모델
│   ├── engine.py                   # 규칙 평가 (threshold/delta/absence/llm)
│   └── loader.py                   # YAML ↔ DB 양방향 동기화
│
├── detection/                      # 감지 오케스트레이션
│   ├── scheduler.py                # 감지 사이클 관리
│   └── evaluator.py                # 규칙별 평가 → 에이전트 연동
│
├── rag/                            # RAG 전문지식 시스템
│   ├── knowledge/                  # 도메인 전문지식 (마크다운)
│   │   ├── equipment.md            # 설비 알람 코드, 연쇄 영향
│   │   ├── process.md              # 공정 흐름, WIP 기준
│   │   ├── logistics.md            # 물류 부하율, AGV 기준
│   │   └── incidents.md            # 과거 사고 사례
│   ├── store.py                    # Milvus 벡터 저장소
│   ├── loader.py                   # 마크다운 → 청크 → 임베딩
│   ├── embedder.py                 # 임베딩 생성 (bge-m3)
│   └── retriever.py                # 유사도 검색 (top_k=5)
│
├── db/
│   ├── oracle.py                   # Oracle 비동기 커넥션 풀
│   ├── schema.sql                  # DDL
│   └── queries.py                  # 공통 쿼리
│
├── api/                            # REST API
│   ├── rules.py                    # 규칙 CRUD + 도구 카탈로그
│   ├── anomalies.py                # 이상 목록 + 상태 변경
│   ├── dashboard.py                # 대시보드 데이터
│   └── system.py                   # 헬스체크, 수동 트리거
│
├── streamlit_app/                  # Streamlit 대시보드
│   ├── .streamlit/config.toml      # 다크 테마 + 포트 3009
│   ├── api_client.py               # httpx 동기 API 래퍼
│   └── app.py                      # 4페이지 대시보드
│
├── examples/                       # 예시 데이터
│   └── rag-knowledge/              # RAG 임베딩 전문지식 예시
│
└── simulator/                      # SQLite 기반 시뮬레이터
    ├── runner.py                   # 시뮬레이터 진입점
    ├── sqlite_backend.py           # Oracle → SQLite 몽키패치
    ├── sql_compat.py               # Oracle SQL → SQLite 변환
    ├── mes_schema.sql              # MES 더미 데이터 스키마
    ├── seeder.py                   # 더미 데이터 시딩
    ├── data_generator.py           # 더미 데이터 생성기
    └── scenarios.py                # 이상 시나리오 자동 재현
```

---

## 시뮬레이터

Oracle 없이 **SQLite + 더미 데이터**로 전체 시스템을 실행할 수 있습니다.

### 시뮬레이터가 하는 일

1. **SQLite DB 생성** — MES 14개 테이블 + 감지 테이블
2. **더미 데이터 시딩** — 설비, 컨베이어, AGV, WIP, LOT 등
3. **Oracle SQL 자동 변환** — `SYSTIMESTAMP` → `datetime('now')`, `FETCH NEXT` → `LIMIT` 등
4. **이상 시나리오 재현** — 컨베이어 과부하, 설비 정지, WIP 급증 등을 시간차로 발생

### 시나리오 예시

```
0초   → 컨베이어 과부하 시나리오 시작 (LINE03-ZONE-A 부하 100%로 변경)
30초  → 설비 비계획정지 시나리오 (EQ-005 DOWN 상태로 변경)
60초  → WIP 급증 시나리오 (TFT-03 공정 WIP 600%로 변경)
120초 → 시나리오 종료 → 정상 복귀 → 반복
```

---

## 설치 및 실행

### 요구사항

- Python 3.12+
- (운영) Oracle DB + MES 테이블
- (시뮬레이터) 별도 DB 불필요

### 시뮬레이터 실행 (Oracle 불필요)

```bash
# 가상환경 생성 + 패키지 설치
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# API 서버 (포트 8600) + 시뮬레이터
python -m simulator.runner

# 대시보드 (포트 3009) — 별도 터미널
streamlit run streamlit_app/app.py
```

### 운영 실행

```bash
# 환경변수 설정 (.env)
ORACLE_USER=fab
ORACLE_PASSWORD=password
ORACLE_DSN=dbhost:1521/FABDB
LLM_BASE_URL=http://llm-server:8080/v1
LLM_API_KEY=your-key
LLM_MODEL=model-name

# 실행
python main.py                      # API :8600
streamlit run streamlit_app/app.py  # 대시보드 :3009
```

---

## API 엔드포인트

| 영역 | 엔드포인트 | 설명 |
|------|-----------|------|
| 규칙 | `GET /api/rules` | 규칙 목록 |
| 규칙 | `POST /api/rules` | 규칙 생성 |
| 규칙 | `PATCH /api/rules/{id}` | 규칙 수정 |
| 규칙 | `DELETE /api/rules/{id}` | 규칙 삭제 |
| 규칙 | `POST /api/rules/{id}/test` | 도구 테스트 실행 |
| 규칙 | `GET /api/rules/tools/catalog` | 도구 카탈로그 (14개) |
| 이상 | `GET /api/anomalies` | 이상 목록 |
| 이상 | `GET /api/anomalies/active` | 활성 이상 |
| 이상 | `PATCH /api/anomalies/{id}/status` | 상태 변경 |
| 대시보드 | `GET /api/dashboard/overview` | 현황 요약 |
| 대시보드 | `GET /api/dashboard/timeline` | 타임라인 |
| 대시보드 | `GET /api/dashboard/heatmap` | 히트맵 |
| 시스템 | `GET /health` | 헬스체크 |
| 시스템 | `POST /api/detect/trigger` | 수동 감지 실행 |
| 시스템 | `GET /api/stats` | 통계 |

---

## DB 테이블

### 감지 테이블

| 테이블 | 용도 |
|--------|------|
| `detection_rules` | 감지 규칙 (도구 + 임계치 + LLM 프롬프트) |
| `anomalies` | 감지된 이상 + AI 분석 결과 |
| `detection_cycles` | 감지 사이클 로그 (소요시간, 규칙 수, 이상 수) |

### MES 참조 테이블 (14개)

물류: `mes_conveyor_status`, `mes_transfer_log`, `mes_carrier_queue`, `mes_vehicle_status`
재공: `mes_wip_summary`, `mes_wip_flow`, `mes_queue_status`, `mes_lot_status`, `mes_wip_snapshot`
설비: `mes_equipment_status`, `mes_equipment_history`, `mes_down_history`, `mes_pm_schedule`, `mes_equipment_alarms`

---

## Streamlit 대시보드

### 4개 페이지

| 페이지 | 기능 |
|--------|------|
| **대시보드** | KPI 카드 (활성위험/경고/24h이상/활성규칙), 상태 분포 차트, 수동 감지 |
| **이상 목록** | 상태별 필터 (감지됨/처리중/해결), 좌우 분할(목록+상세), AI 분석, 상태 전이 |
| **규칙 관리** | 2탭 추가 (임계치 감시/AI 판단), 도구 카탈로그, 테스트 실행 |
| **감지 로그** | 감지 사이클 이력, 상태별 이상 통계 |

---

## 추후 확장

| 기능 | 설명 | 참고 파일 |
|------|------|----------|
| **RCA (근본원인분석)** | DB 폴링으로 이상 자동 분석 | `agent/rca_agent.py` |
| **알림** | DB 기록 → 이메일/메신저 연동 | `alert/router.py` |
| **에스컬레이션** | 미확인 이상 자동 재알림 | `alert/escalation.py` |
| **상관분석** | 시간/공간/인과 기반 이상 그룹핑 | `correlation/engine.py` |
