# FAB 이상감지

반도체 FAB 폐쇄망 환경에서 물류 부하 / 재공(WIP) / 설비 이상을 AI 에이전트가 주기적으로 감지하여 대시보드로 알림하는 시스템.

오픈소스 프레임워크(LangChain 등) 없이, OpenAI 호환 사내 LLM + Oracle DB 기반으로 자체 구축.

---

## 기술 스택

| 영역 | 기술 | 설명 |
|------|------|------|
| **언어** | Python 3.12+ | 비동기(asyncio) 기반 |
| **API 서버** | FastAPI + Uvicorn | 비동기 Web API (포트 8600) |
| **대시보드** | Streamlit | 4페이지 대시보드 (포트 3009) |
| **DB (운영)** | Oracle (oracledb thin) | Instant Client 없이 순수 Python 연결 |
| **DB (시뮬레이터)** | SQLite | Oracle SQL → SQLite 자동 변환 |
| **LLM** | OpenAI 호환 API | 사내 LLM 또는 Ollama (Qwen 2.5 등) |
| **스케줄러** | APScheduler | 감지 주기 스케줄링 |
| **HTTP 클라이언트** | httpx | LLM API 호출 (async + sync) |
| **차트** | Plotly | 대시보드 시각화 |
| **데이터** | Pandas | 테이블 데이터 처리 |
| **AI 패턴** | ReAct (자체 구현) | LLM + Tool Use 에이전트 루프 |
| **벡터 검색** | Milvus (RAG) | 전문지식 검색 보강 |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     FAB 이상감지 시스템                          │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ Scheduler │───→│  Detection   │───→│  DB INSERT           │  │
│  │(APSched)  │    │  Agent       │    │  (anomalies 테이블)  │  │
│  │ 매 5분    │    │  (ReAct)     │    └──────────────────────┘  │
│  └──────────┘    └──────────────┘                               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Streamlit 대시보드 (:3009)               │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │ 대시보드  │ │ 이상목록  │ │ 규칙관리  │ │ 감지로그  │   │  │
│  │  │ KPI+차트 │ │ 상세+상태 │ │ CRUD+AI  │ │ 사이클   │   │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────────┐     │
│  │ Rule       │   │ Web API      │   │ Oracle DB        │     │
│  │ Engine     │   │ (FastAPI)    │   │ MES + 감지 테이블 │     │
│  │ SQL+임계치 │   │ :8600        │   │                  │     │
│  └────────────┘   └──────────────┘   └──────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 감지 흐름

```
매 5분 (APScheduler)
  │
  ├─ 1. DB에서 활성 규칙 로드
  │
  ├─ 2. 규칙별 SQL 실행 + 임계치 비교
  │     ├─ threshold: 측정값 > 임계값?
  │     ├─ delta: 변화율 > 임계값?
  │     ├─ absence: 데이터 없음?
  │     └─ llm: LLM 판단 위임
  │
  └─ 3. 위반 → 감지 에이전트 (llm_enabled인 경우)
        └─ ReAct: 추가 DB 조회 → 이상 확인 → DB INSERT
```

---

## 프로젝트 구조

```
fab-sentinel/
├── main.py                     # FastAPI + APScheduler 진입점 (:8600)
├── config.py                   # 환경설정 (DB, LLM, 스케줄)
├── requirements.txt
│
├── db/
│   ├── oracle.py               # Oracle 비동기 커넥션 풀
│   ├── schema.sql              # DDL (detection_rules, anomalies 등)
│   └── queries.py              # 공통 쿼리
│
├── agent/
│   ├── llm_client.py           # OpenAI 호환 LLM 클라이언트
│   ├── tool_registry.py        # @registry.tool → JSON Schema 자동 생성
│   ├── agent_loop.py           # ReAct 에이전트 루프 (최대 3라운드)
│   ├── prompts.py              # 시스템 프롬프트
│   ├── detection_agent.py      # 이상감지 에이전트 → DB INSERT
│   ├── rca_agent.py            # [추후] 원인분석 에이전트 스텁
│   └── tools/                  # DB 쿼리 도구 (~15개)
│       ├── logistics.py        # 컨베이어, 반송, 병목존, AGV
│       ├── wip.py              # WIP, 흐름, 큐, 에이징, 트렌드
│       └── equipment.py        # 설비, 가동률, 정지, PM, 알람
│
├── rules/
│   ├── models.py               # Pydantic 모델 (RuleCreate, RuleUpdate)
│   └── engine.py               # 룰 평가 (threshold/delta/absence/llm)
│
├── detection/
│   ├── scheduler.py            # 감지 사이클 오케스트레이션
│   └── evaluator.py            # 규칙별 평가 → 에이전트 연동
│
├── correlation/                # [추후] 상관관계 분석
│   └── engine.py
│
├── alert/                      # [추후] 알림 시스템
│   ├── router.py               # 알림 라우터 스텁
│   └── escalation.py           # 에스컬레이션 스텁
│
├── api/
│   ├── rules.py                # 규칙 CRUD + 테스트 + AI 자연어 생성
│   ├── anomalies.py            # 이상 목록 + 상태 변경
│   ├── dashboard.py            # 대시보드 데이터
│   └── system.py               # 헬스체크, 수동 트리거, 통계
│
├── rag/                        # RAG 전문지식 시스템
│
├── streamlit_app/              # Streamlit 대시보드
│   ├── .streamlit/
│   │   ├── config.toml         # 다크 테마 + 포트 3009
│   │   └── secrets.toml        # 관리자 비밀번호
│   ├── api_client.py           # httpx 동기 API 래퍼
│   └── app.py                  # 4페이지 대시보드
│
└── simulator/                  # SQLite 기반 시뮬레이터
    ├── runner.py               # 시뮬레이터 진입점
    ├── sqlite_backend.py       # Oracle → SQLite 몽키패치
    ├── sql_compat.py           # Oracle SQL → SQLite 변환
    ├── mes_schema.sql          # MES 더미 데이터 스키마
    └── data_generator.py       # 더미 데이터 생성기
```

---

## 감지 규칙 시스템

### 규칙 유형 4가지

| 유형 | 동작 | 예시 |
|------|------|------|
| **threshold** | 값 > 임계치 | 컨베이어 부하율 > 90% |
| **delta** | 변화율 > 임계치 | WIP 1시간 변화율 > 30% |
| **absence** | 데이터 없음 | 30분간 반송 기록 없음 |
| **llm** | LLM에게 판단 위임 | 복합 패턴, 상대 비교 |

### 자연어 규칙 생성 (AI)

사용자가 자연어로 이상 조건을 설명하면 AI가 감지 규칙을 자동 생성합니다.

**예시 입력:**
```
"어떤 공정에 재공이 많이 쌓였는데, 전체 평균 대비 그 공정만 유독 높으면 이상이야.
전체적으로 높은 건 괜찮아."
```

**지원하는 판단 패턴:**

| 패턴 | 설명 | check_type |
|------|------|------------|
| 단순 임계값 | "재공이 100개 넘으면 이상" | threshold |
| 상대적 비교 | "특정 공정만 유독 높으면 이상" | llm |
| 추세/변화 | "최근 1시간 계속 증가하면 이상" | llm |
| 복합 조건 | "설비 DOWN인데 알람 없으면 이상" | llm |
| 비율 기반 | "에러 AGV가 전체의 30% 이상이면" | threshold |

### 규칙 추가 방법 3가지

| 방법 | 설명 | 대상 사용자 |
|------|------|------------|
| 자연어로 만들기 | 자연어 → AI가 SQL+규칙 자동 생성 | 비개발자 |
| 가이드 빌더 | 테이블/컬럼 선택 → SQL 자동 생성 | SQL 모르는 엔지니어 |
| 직접 입력 | SQL 직접 작성 | 개발자/DBA |

---

## 이상 상태머신

```
detected → acknowledged → investigating → resolved
    │            │               │
    └────────────┴───────────────┴──→ false_positive
```

---

## DB 테이블

| 테이블 | 용도 |
|--------|------|
| `detection_rules` | 감지 규칙 (SQL 쿼리 + 임계치) |
| `anomalies` | 감지된 이상 + LLM 분석 |
| `correlations` | 상관 그룹 (추후) |
| `detection_cycles` | 감지 사이클 로그 |

MES 참조 테이블 (14개): `mes_conveyor_status`, `mes_transfer_log`, `mes_carrier_queue`, `mes_vehicle_status`, `mes_wip_summary`, `mes_wip_flow`, `mes_queue_status`, `mes_lot_status`, `mes_wip_snapshot`, `mes_equipment_status`, `mes_equipment_history`, `mes_down_history`, `mes_pm_schedule`, `mes_equipment_alarms`

---

## API 엔드포인트

| 영역 | 엔드포인트 | 설명 |
|------|-----------|------|
| 규칙 | `GET /api/rules` | 규칙 목록 |
| 규칙 | `POST /api/rules` | 규칙 생성 |
| 규칙 | `PATCH /api/rules/{id}` | 규칙 수정 |
| 규칙 | `DELETE /api/rules/{id}` | 규칙 삭제 |
| 규칙 | `POST /api/rules/{id}/test` | SQL 테스트 실행 |
| 규칙 | `GET /api/rules/schema/tables` | MES 테이블 스키마 |
| 규칙 | `POST /api/rules/generate` | AI 자연어 규칙 생성 |
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

## Streamlit 대시보드

### 4개 페이지

| 페이지 | 기능 |
|--------|------|
| **대시보드** | KPI 카드 (활성위험/경고/24h이상/활성규칙), 상태 분포 차트, 수동 감지 |
| **이상 목록** | 상태별 필터, 좌우 분할(목록+상세), AI 분석, 상태 전이 |
| **규칙 관리** | 3탭 추가(자연어/가이드빌더/직접입력), 규칙 수정/삭제, SQL 테스트 |
| **감지 로그** | 감지 사이클 정보, 상태별 이상 이력 |

### 권한 분리

| 역할 | 권한 |
|------|------|
| **열람자** (기본) | 모든 페이지 조회 |
| **관리자** | 규칙 CRUD + 이상 상태 변경 + 수동 감지 |

---

## 설치 및 실행

### 환경변수 (.env)

```env
ORACLE_USER=fab
ORACLE_PASSWORD=password
ORACLE_DSN=dbhost:1521/FABDB
LLM_BASE_URL=http://llm-server:8080/v1
LLM_API_KEY=your-key
LLM_MODEL=model-name
DETECTION_INTERVAL_SEC=300
```

### 실행 (시뮬레이터)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 시뮬레이터 (SQLite, Oracle 불필요)
python -m simulator.runner    # API :8600
streamlit run streamlit_app/app.py  # 대시보드 :3009
```

### 실행 (운영)

```bash
python main.py                      # API :8600
streamlit run streamlit_app/app.py  # 대시보드 :3009
```

---

## 사용 매뉴얼

### 1. 접속
`http://localhost:3009` → 기본 열람자 모드

### 2. 관리자 로그인
사이드바 → "관리자 로그인" → 비밀번호 (기본: `fab-admin`)

### 3. 이상 확인
"이상 목록" → 상태 필터 → 이상 클릭 → 상세 (AI 분석, 측정값, 상태 전이)

### 4. 규칙 추가
"규칙 관리" → "새 규칙 추가":
- **자연어**: 이상 조건 설명 → AI가 규칙 생성 → 확인/수정 → 등록
- **가이드 빌더**: 테이블/컬럼 선택 → SQL 자동 생성
- **직접 입력**: SQL 직접 작성

### 5. 수동 감지
"대시보드" → "수동 감지 실행" (관리자)

---

## 추후 확장

| 기능 | 설명 | 참고 파일 |
|------|------|----------|
| **RCA (근본원인분석)** | DB 폴링으로 이상 분석, ReAct 루프 | `agent/rca_agent.py` |
| **알림** | DB 기록 → 이메일/메신저 채널 연동 | `alert/router.py` |
| **에스컬레이션** | 미확인 이상 재알림 | `alert/escalation.py` |
| **상관분석** | 시간/공간/인과 기반 이상 그룹핑 | `correlation/engine.py` |
