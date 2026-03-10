# FAB-SENTINEL

반도체 FAB 폐쇄망 환경에서 물류 부하 / 재공(WIP) / 설비 이상을 AI 에이전트가 주기적으로 감지하고, 근본원인을 분석하여 대시보드로 알림하는 시스템.

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
| **스케줄러** | APScheduler | 감지 주기 + RCA 폴링 |
| **HTTP 클라이언트** | httpx | LLM API 호출 (async + sync) |
| **차트** | Plotly | 대시보드 시각화 |
| **데이터** | Pandas | 테이블 데이터 처리 |
| **AI 패턴** | ReAct (자체 구현) | LLM + Tool Use 에이전트 루프 |
| **벡터 검색** | Milvus (RAG) | 전문지식 검색 보강 |

### 의존성 (requirements.txt)

```
fastapi, uvicorn, httpx, oracledb, apscheduler, pydantic, python-dotenv
streamlit, streamlit-autorefresh, plotly, pandas
pymilvus (RAG용)
```

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FAB-SENTINEL v2.0                            │
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │ Scheduler │───→│  Detection   │───→│  DB INSERT               │  │
│  │(APSched)  │    │  Agent       │    │  (rca_status='pending')  │  │
│  │ 매 5분    │    │  (ReAct)     │    └──────────────────────────┘  │
│  └──────────┘    └──────────────┘                                   │
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │ RCA      │───→│  RCA Agent   │───→│  DB UPDATE               │  │
│  │ Poller   │    │  (ReAct)     │    │  (rca_status='done')     │  │
│  │ 매 30초  │    │  근본원인분석 │    │  + 알림 DB INSERT        │  │
│  └──────────┘    └──────────────┘    └──────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Streamlit 대시보드 (:3009)                 │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │  │
│  │  │ 대시보드  │ │ 이상목록  │ │ 규칙관리  │ │ 처리 로그    │   │  │
│  │  │ KPI      │ │ 상세+RCA │ │ CRUD     │ │ 감지/RCA/알림│   │  │
│  │  │ 차트     │ │ 상태전이  │ │ AI생성   │ │              │   │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌────────────┐   ┌──────────────┐   ┌────────────────────────┐   │
│  │ Rule       │   │ Correlation  │   │ Web API (FastAPI)      │   │
│  │ Engine     │   │ Engine       │   │ :8600                  │   │
│  │ SQL+임계치 │   │ 시간/공간/인과│   │ 규칙 CRUD + AI 생성    │   │
│  └────────────┘   └──────────────┘   └────────────────────────┘   │
│                                                                     │
│                         ┌───────────┐                               │
│                         │ Oracle DB │                                │
│                         │ MES 데이터 │                               │
│                         │ + SENTINEL │                               │
│                         │   테이블   │                               │
│                         └───────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 핵심 설계: DB 폴링 기반 에이전트 분리

이상감지와 원인분석을 **DB 상태(rca_status)** 로 분리합니다. 토픽 버스 없이 DB만으로 동작하므로 디버깅이 쉽고 폐쇄망에서 견고합니다.

```
감지 에이전트                    RCA 에이전트                     알림
     │                              │                              │
     │  DB INSERT                   │  DB 폴링 (30초)              │  DB INSERT
     ▼                              ▼                              ▼
 ┌──────────────────────────────────────────────────────────────────────┐
 │                         Oracle DB                                    │
 │                                                                      │
 │   sentinel_anomalies                                                │
 │   ├─ rca_status = 'pending'    ← 감지 에이전트가 INSERT            │
 │   ├─ rca_status = 'processing' ← RCA 에이전트가 UPDATE (처리 중)   │
 │   ├─ rca_status = 'done'       ← RCA 에이전트가 UPDATE (분석 완료) │
 │   └─ rca_status = 'failed'     ← 분석 실패 시                      │
 │                                                                      │
 │   sentinel_alert_history       ← RCA 완료 시 알림 메시지 INSERT    │
 └──────────────────────────────────────────────────────────────────────┘
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
│   ├── schema.sql              # DDL (sentinel_* 테이블 6개)
│   └── queries.py              # 공통 쿼리 + RCA 폴링 쿼리
│
├── agent/
│   ├── llm_client.py           # OpenAI 호환 LLM 클라이언트
│   ├── tool_registry.py        # @registry.tool → JSON Schema 자동 생성
│   ├── agent_loop.py           # ReAct 에이전트 루프 (최대 3라운드)
│   ├── prompts.py              # 시스템 프롬프트 (감지 / RCA / 상관)
│   ├── detection_agent.py      # 이상감지 에이전트 → DB INSERT
│   ├── rca_agent.py            # 원인분석 에이전트 → DB 폴링 → 분석
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
├── correlation/
│   └── engine.py               # 상관관계 (시간·공간·인과)
│
├── alert/
│   ├── router.py               # 알림 → DB 기록 (대시보드용)
│   └── escalation.py           # 에스컬레이션 (미확인 시 재알림)
│
├── lifecycle/
│   └── manager.py              # 이상 상태머신
│
├── api/
│   ├── rules.py                # 규칙 CRUD + 테스트 + AI 자연어 생성
│   ├── anomalies.py            # 이상 목록 + 상태 변경
│   ├── correlations.py         # 상관그룹 조회
│   ├── alerts.py               # 알림 이력
│   ├── dashboard.py            # 대시보드 데이터
│   └── system.py               # 헬스체크, 수동 트리거, 통계
│
├── rag/                        # RAG 전문지식 시스템
│   ├── milvus_store.py         # Milvus 벡터 저장소
│   ├── embedder.py             # 텍스트 임베딩
│   └── knowledge_base.py       # 지식 검색
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

## AI 에이전트 상세

### ReAct 패턴

두 에이전트 모두 동일한 ReAct 루프(`agent_loop.py`)를 사용합니다:

```
1. 시스템 프롬프트 + 컨텍스트 → LLM 전달
2. LLM이 tool_call 요청 → DB 쿼리 실행 → 결과 반환
3. 최대 3라운드 반복
4. 최종 JSON 응답 반환
```

### 감지 에이전트 (detection_agent.py)

규칙 위반이 감지되면 LLM에게 실제 이상 여부를 판단시킵니다.

```json
{
  "is_anomaly": true,
  "confidence": 0.85,
  "severity": "critical",
  "title": "LINE03 컨베이어 부하율 95% 초과",
  "analysis": "TFT 공정 LINE03 존의 부하율이...",
  "affected_entity": "LINE03-ZONE-A"
}
```

이상 확인 시 DB에 INSERT (`rca_status='pending'`) → RCA 에이전트가 폴링.

### RCA 에이전트 (rca_agent.py)

DB에서 `rca_status='pending'`인 이상을 폴링(30초)하여 근본원인을 분석합니다:

```json
{
  "root_cause": "CELL 공정 EQ-201 비계획정지로 상류 WIP 적체",
  "evidence": [
    "EQ-201 14:23 DOWN (알람코드 A-501)",
    "LINE03 WIP 30분간 45% 증가",
    "컨베이어 부하율 동시 상승"
  ],
  "impact_scope": "TFT→CELL 라인 전체, 예상 2시간 영향",
  "suggested_actions": [
    "EQ-201 알람 코드 A-501 점검",
    "LINE03 WIP 우회 경로 검토",
    "PM 일정 앞당김 검토"
  ],
  "confidence": 0.78,
  "related_entities": ["EQ-201", "LINE03-ZONE-A", "LINE03-ZONE-B"]
}
```

### 도구 목록 (15개)

| 카테고리 | 도구 | 설명 |
|----------|------|------|
| 물류 | `get_conveyor_load` | 컨베이어 부하율(%) |
| 물류 | `get_transfer_throughput` | 반송 처리량 (moves/hr) |
| 물류 | `get_bottleneck_zones` | 병목 존 감지 |
| 물류 | `get_agv_utilization` | AGV/OHT 가동률 |
| 물류 | `get_zone_transfer_history` | 존별 반송 이력 |
| WIP | `get_wip_levels` | 공정별 WIP 수준 |
| WIP | `get_flow_balance` | 유입/유출 밸런스 |
| WIP | `get_queue_length` | 큐 길이 |
| WIP | `get_aging_lots` | 에이징 LOT |
| WIP | `get_wip_trend` | WIP 추이 트렌드 |
| 설비 | `get_equipment_status` | 설비 현재 상태 |
| 설비 | `get_equipment_utilization` | 설비 가동률 |
| 설비 | `get_unscheduled_downs` | 비계획정지 이력 |
| 설비 | `get_pm_schedule` | PM 일정 |
| 설비 | `get_equipment_alarms` | 설비 알람 이력 |

각 도구는 `@registry.tool` 데코레이터로 등록되며, OpenAI function calling JSON Schema가 자동 생성됩니다.

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

**AI 생성 결과:**
```json
{
  "rule_name": "공정별 WIP 상대 편차 이상",
  "category": "wip",
  "check_type": "llm",
  "query_template": "SELECT process, current_wip, target_wip, (SELECT AVG(current_wip) FROM mes_wip_summary) as avg_wip FROM mes_wip_summary ORDER BY current_wip DESC",
  "llm_enabled": true,
  "llm_prompt": "각 공정의 재공을 전체 평균과 비교해서, 평균 대비 유독 높은 공정이 있으면 이상. 전체적으로 높은 건 정상."
}
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

## 감지 흐름

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
  ├─ 3. 위반 → 감지 에이전트 (llm_enabled인 경우)
  │     └─ ReAct: 추가 DB 조회 → 이상 확인 → DB INSERT (rca_status='pending')
  │
  ├─ 4. RCA 폴러 (매 30초)
  │     └─ rca_status='pending' 조회 → RCA 에이전트 실행
  │     └─ ReAct: 추가 DB 조회 → 근본원인 분석 → DB UPDATE (rca_status='done')
  │     └─ 알림 메시지 DB INSERT (sentinel_alert_history)
  │
  └─ 5. 상관관계 분석
        ├─ 시간적: 10분 내 동시 발생
        ├─ 공간적: 같은 라인/존
        └─ 인과적: TFT→CELL→MODULE 흐름
```

---

## 이상 상태머신

```
detected → acknowledged → investigating → resolved
    │            │               │
    └────────────┴───────────────┴──→ false_positive
```

**RCA 상태:**
```
pending → processing → done
                    └→ failed
```

---

## Oracle DB 스키마

6개 테이블:

| 테이블 | 용도 |
|--------|------|
| `sentinel_rules` | 감지 규칙 (SQL 쿼리 + 임계치) |
| `sentinel_anomalies` | 감지된 이상 + LLM 분석 + rca_status |
| `sentinel_correlations` | 상관 그룹 |
| `sentinel_alert_history` | 알림 발송 이력 + 메시지 본문 |
| `sentinel_alert_routes` | 알림 라우팅 설정 |
| `sentinel_detection_cycles` | 감지 사이클 로그 |

MES 참조 테이블 (14개): `mes_conveyor_status`, `mes_transfer_log`, `mes_carrier_queue`, `mes_vehicle_status`, `mes_wip_summary`, `mes_wip_flow`, `mes_queue_status`, `mes_lot_status`, `mes_wip_snapshot`, `mes_equipment_status`, `mes_equipment_history`, `mes_down_history`, `mes_pm_schedule`, `mes_equipment_alarms`

DDL: `db/schema.sql`

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
| 이상 | `GET /api/anomalies` | 이상 목록 (필터: status) |
| 이상 | `GET /api/anomalies/active` | 활성 이상 |
| 이상 | `PATCH /api/anomalies/{id}/status` | 상태 변경 |
| 이상 | `POST /api/anomalies/{id}/notes` | 노트 추가 |
| 상관 | `GET /api/correlations` | 상관그룹 목록 |
| 상관 | `GET /api/correlations/{id}` | 상관그룹 상세 |
| 알림 | `GET /api/alerts/history` | 발송 이력 |
| 대시보드 | `GET /api/dashboard/overview` | 현황 요약 |
| 대시보드 | `GET /api/dashboard/timeline` | 시간별 타임라인 |
| 대시보드 | `GET /api/dashboard/heatmap` | 카테고리×심각도 히트맵 |
| 시스템 | `GET /health` | 헬스체크 |
| 시스템 | `POST /api/detect/trigger` | 수동 감지 실행 |
| 시스템 | `GET /api/stats` | 통계 |

---

## Streamlit 대시보드

### 4개 페이지

| 페이지 | 기능 |
|--------|------|
| **대시보드** | KPI 카드 4개 (활성위험/경고/24h이상/활성규칙), 상태 분포 차트, 마지막 감지 사이클, 수동 감지 버튼 |
| **이상 목록** | 상태별 필터, 좌우 분할(목록+상세), AI 분석 결과, AI 제안, 상태 전이 버튼 |
| **규칙 관리** | 3탭 규칙 추가(자연어/가이드빌더/직접입력), 규칙 수정/삭제, SQL 테스트 |
| **처리 로그** | 감지 사이클, RCA 처리 이력(상태별), 알림 발송 이력 + 메시지 뷰어 |

### 권한 분리

| 역할 | 권한 |
|------|------|
| **열람자** (기본) | 대시보드 조회, 이상 목록 조회, 규칙 조회, 로그 조회 |
| **관리자** | 위 전부 + 규칙 CRUD + 이상 상태 변경 + 수동 감지 실행 |

관리자 비밀번호: `streamlit_app/.streamlit/secrets.toml`에서 설정 (기본: `fab-admin`)

---

## 설치 및 실행

### 환경변수 (.env)

```env
# Oracle
ORACLE_USER=sentinel
ORACLE_PASSWORD=password
ORACLE_DSN=dbhost:1521/FABDB

# LLM (OpenAI 호환 API)
LLM_BASE_URL=http://llm-server:8080/v1
LLM_API_KEY=your-key
LLM_MODEL=model-name

# 스케줄
DETECTION_INTERVAL_SEC=300
```

### 설치

```bash
# 가상환경 생성
python -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 폐쇄망 (오프라인)
pip install --no-index --find-links=./wheels -r requirements.txt
```

### DB 초기화

```bash
# Oracle
sqlplus sentinel/password@FABDB @db/schema.sql
```

### 실행 (운영)

```bash
# API 서버
python main.py
# → http://0.0.0.0:8600

# Streamlit 대시보드
streamlit run streamlit_app/app.py
# → http://0.0.0.0:3009
```

### 실행 (시뮬레이터)

Oracle 없이 SQLite로 테스트:

```bash
# 시뮬레이터 (API + 더미 데이터 자동 생성)
python -m simulator.runner
# → http://0.0.0.0:8600

# Streamlit 대시보드
streamlit run streamlit_app/app.py
# → http://0.0.0.0:3009
```

---

## 사용 매뉴얼

### 1. 대시보드 접속

브라우저에서 `http://localhost:3009` 접속. 기본은 열람자 모드.

### 2. 관리자 로그인

1. 좌측 사이드바 → "관리자 로그인" 클릭
2. 비밀번호 입력 (기본: `fab-admin`)
3. "ADMIN" 뱃지 확인

### 3. 이상 확인하기

1. "이상 목록" 페이지 이동
2. 상태 필터로 원하는 이상 선택 (detected, acknowledged 등)
3. 목록에서 이상 클릭 → 우측에 상세 표시
   - 심각도, 측정값, 임계치
   - AI 분석 결과 (근본원인)
   - AI 제안 (조치 사항)
4. 관리자: 상태 전이 버튼으로 처리
   - 확인 → 조사 중 → 해결 / 오탐

### 4. 규칙 추가하기

**방법 A: 자연어로 만들기 (추천)**

1. "규칙 관리" 페이지 → "새 규칙 추가" 클릭
2. "자연어로 만들기" 탭 선택
3. 이상 조건을 자연어로 설명:
   ```
   어떤 공정에 재공이 많이 쌓였는데, 전체 평균 대비 그 공정만
   유독 높으면 이상이야. 전체적으로 높은 건 괜찮아.
   ```
4. "AI로 규칙 생성" 클릭
5. AI가 생성한 규칙 확인 (SQL, 임계치, LLM 프롬프트)
6. 필요 시 수정 → "이 규칙 등록" 클릭

**방법 B: 가이드 빌더**

1. "가이드 빌더" 탭 선택
2. MES 테이블 선택 (예: mes_wip_summary)
3. 측정 컬럼, 그룹 컬럼, 집계 함수, 조건 설정
4. (선택) AI 판단 조건 추가
5. "규칙 생성" 클릭 → SQL 자동 생성

**방법 C: 직접 입력**

1. "직접 입력" 탭 선택
2. 규칙명, 카테고리, SQL 쿼리, 임계치 직접 입력
3. "규칙 추가" 클릭

### 5. 규칙 테스트하기

1. "규칙 관리" 페이지에서 규칙 선택
2. "규칙 테스트" 버튼 클릭
3. SQL 실행 결과 확인 (이상 생성 없이 결과만 표시)

### 6. 수동 감지 실행

1. "대시보드" 페이지
2. "수동 감지 실행" 버튼 클릭 (관리자만)
3. 결과: 평가된 규칙 수, 발견된 이상 수, 소요시간

### 7. 처리 로그 확인

1. "처리 로그" 페이지 이동
2. 3개 탭:
   - **감지 사이클**: 마지막 감지 실행 정보
   - **RCA 이력**: 상태별(processing/done/failed/pending) 이상 목록
   - **알림 이력**: 발송된 알림 + 메시지 본문 뷰어
