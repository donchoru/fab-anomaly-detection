"""데이터 주입기 — 이상 시나리오를 시간차로 DB에 주입.

실행: python data_injector.py [--db simulator.db] [--speed 2]

시나리오 (60초 간격, --speed로 조절):
  1. 컨베이어 과부하  (LINE03-ZONE-A 부하율 96%)
  2. 설비 비계획정지  (EQ-005 DOWN + 알람)
  3. WIP 적체         (TFT 공정 170%)
  4. 에이징 LOT       (5개 LOT 24시간+ 체류)
  5. AGV 장애         (3대 ERROR)

--loop: 주입 후 상황 점진적 악화 반복
--reset: 이전 주입 데이터 초기화 후 재주입
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time


def _inject_anomalies_with_rca(logger) -> None:
    """이상 데이터 + RCA 원인분석 결과를 직접 삽입."""
    import json
    from simulator.sqlite_backend import get_conn

    conn = get_conn()

    # rca_analyses 테이블 생성 (없으면)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rca_analyses (
            rca_id INTEGER PRIMARY KEY AUTOINCREMENT,
            anomaly_id INTEGER NOT NULL REFERENCES anomalies(anomaly_id),
            status TEXT DEFAULT 'pending',
            root_cause TEXT,
            cause_category TEXT,
            contributing_factors TEXT,
            evidence TEXT,
            recommendations TEXT,
            confidence REAL,
            analyzed_at TEXT,
            analysis_duration_ms INTEGER,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    SAMPLE_DATA = [
        {
            "anomaly": {
                "category": "logistics",
                "severity": "critical",
                "title": "LINE03-ZONE-A 컨베이어 부하율 96% 초과",
                "description": "LINE03-ZONE-A 구간 컨베이어 부하율이 96%로 위험 임계치(90%)를 초과했습니다.",
                "measured_value": 96.0,
                "threshold_value": 90.0,
                "affected_entity": "LINE03-ZONE-A",
                "status": "in_progress",
                "llm_analysis": "LINE03-ZONE-A 구간에서 캐리어가 비정상적으로 적체되고 있습니다. 상류 공정에서의 과도한 투입과 하류 설비의 처리 지연이 복합적으로 작용한 것으로 판단됩니다.",
                "llm_suggestion": json.dumps(["상류 공정 투입량 일시 제한", "하류 설비 처리 속도 점검", "캐리어 우회 경로 활성화"], ensure_ascii=False),
            },
            "rca": {
                "status": "done",
                "root_cause": "하류 설비 EQ-005 비계획정지로 인한 캐리어 적체. 상류 TFT 공정의 WIP 증가와 동시 발생하여 부하율이 급격히 상승.",
                "cause_category": "equipment",
                "contributing_factors": json.dumps([
                    "EQ-005 설비 비계획정지 (베어링 마모)",
                    "TFT-03 공정 WIP 170% 적체로 캐리어 투입 증가",
                    "AGV-003 장애로 캐리어 회수 지연",
                    "PM 일정 미준수 (EQ-005 예방정비 2주 지연)",
                ], ensure_ascii=False),
                "evidence": json.dumps([
                    "mes_conveyor_status: LINE03-ZONE-A carrier_count 96/100",
                    "mes_equipment_status: EQ-005 status=DOWN since 14:23",
                    "mes_wip_summary: TFT-03 current_wip=170, target_wip=100",
                    "mes_vehicle_status: AGV-003 status=ERROR",
                    "mes_pm_schedule: EQ-005 PM 예정일 2주 경과",
                ], ensure_ascii=False),
                "recommendations": json.dumps([
                    "EQ-005 베어링 즉시 교체 및 설비 복구 (예상 소요: 2시간)",
                    "LINE03-ZONE-A → ZONE-B 캐리어 우회 경로 활성화",
                    "TFT-03 공정 투입 일시 제한 (현재 WIP 정상화까지)",
                    "AGV-003 장애 원인 확인 및 복구",
                    "PM 일정 관리 프로세스 재검토 (지연 알림 체계 강화)",
                ], ensure_ascii=False),
                "confidence": 0.87,
                "analysis_duration_ms": 3420,
            },
        },
        {
            "anomaly": {
                "category": "equipment",
                "severity": "critical",
                "title": "EQ-005 비계획정지 — 베어링 마모 알람",
                "description": "EQ-005 설비가 비계획적으로 정지되었습니다. 알람 코드 A-501 (베어링 과열).",
                "measured_value": 1.0,
                "threshold_value": 0.0,
                "affected_entity": "EQ-005",
                "status": "detected",
                "llm_analysis": "EQ-005 설비에서 A-501 알람(베어링 과열)이 발생하며 비계획 정지되었습니다. 최근 PM 일정이 지연된 상태에서 발생하여 예방정비 미흡이 원인으로 추정됩니다.",
                "llm_suggestion": json.dumps(["베어링 즉시 교체", "설비 복구 후 시운전 검증", "PM 일정 준수 강화"], ensure_ascii=False),
            },
            "rca": {
                "status": "done",
                "root_cause": "EQ-005 메인 스핀들 베어링의 점진적 마모. 예방정비(PM) 일정이 2주 지연되면서 마모가 임계점을 초과하여 과열 → 비계획정지 발생.",
                "cause_category": "equipment",
                "contributing_factors": json.dumps([
                    "메인 스핀들 베어링 마모 (가동시간 4,200h, 교체주기 3,500h 초과)",
                    "예방정비(PM) 일정 2주 지연",
                    "진동 센서 경고(W-301) 3일 전 발생했으나 미조치",
                    "윤활유 교체 주기 미준수",
                ], ensure_ascii=False),
                "evidence": json.dumps([
                    "mes_equipment_alarms: A-501 베어링 과열 알람 발생",
                    "mes_down_history: EQ-005 down_code=A-501, down_type=UNSCHEDULED",
                    "mes_pm_schedule: EQ-005 PM 예정일 2주 경과 (status=PENDING)",
                    "mes_equipment_history: 가동시간 4,200h 누적",
                    "mes_equipment_alarms: W-301 진동 경고 3일 전 미조치",
                ], ensure_ascii=False),
                "recommendations": json.dumps([
                    "메인 스핀들 베어링 즉시 교체 (예비부품 재고 확인)",
                    "교체 후 진동/온도 모니터링 24시간 집중 감시",
                    "PM 일정 자동 알림 시스템 도입 (지연 시 에스컬레이션)",
                    "유사 설비(EQ-003, EQ-007) 베어링 상태 선제 점검",
                    "윤활유 자동 보충 시스템 도입 검토",
                ], ensure_ascii=False),
                "confidence": 0.92,
                "analysis_duration_ms": 2850,
            },
        },
        {
            "anomaly": {
                "category": "wip",
                "severity": "warning",
                "title": "TFT 공정 WIP 170% 적체 — 목표 대비 과잉",
                "description": "TFT-03, TFT-04 단계의 재공(WIP)이 목표 대비 170%로 적체되고 있습니다.",
                "measured_value": 170.0,
                "threshold_value": 130.0,
                "affected_entity": "TFT-03",
                "status": "in_progress",
                "llm_analysis": "TFT 공정 WIP가 목표의 170%에 달합니다. 하류 설비 정지와 상류 투입량 증가가 복합적으로 작용하고 있습니다.",
                "llm_suggestion": json.dumps(["하류 설비 복구 우선", "투입 제한 검토", "WIP 추이 모니터링 강화"], ensure_ascii=False),
            },
            "rca": {
                "status": "done",
                "root_cause": "하류 CELL 공정 설비(EQ-005) 정지로 TFT → CELL 이동이 차단되면서 TFT 공정에 WIP가 누적. 동시에 상류에서 신규 LOT 투입이 계속되어 적체 심화.",
                "cause_category": "process",
                "contributing_factors": json.dumps([
                    "하류 CELL 공정 EQ-005 비계획정지 (연쇄 영향)",
                    "LOT 투입 계획이 설비 가동 상태와 비연동",
                    "WIP 적체 시 자동 투입 중단 로직 부재",
                    "물류 캐리어 적체로 WIP 이동 추가 지연",
                ], ensure_ascii=False),
                "evidence": json.dumps([
                    "mes_wip_summary: TFT-03 current_wip=170, target_wip=100",
                    "mes_wip_summary: TFT-04 current_wip=165, target_wip=100",
                    "mes_wip_flow: TFT-03 OUT flow 최근 2시간 0건 (정상 시 시간당 15건)",
                    "mes_equipment_status: EQ-005(CELL) DOWN → TFT→CELL 이동 불가",
                    "mes_queue_status: TFT-03 queue_count=45, avg_wait=85min",
                ], ensure_ascii=False),
                "recommendations": json.dumps([
                    "EQ-005 복구 최우선 처리 (TFT WIP 해소의 근본 해결책)",
                    "TFT 공정 신규 LOT 투입 일시 중단 (WIP 120% 이하까지)",
                    "적체 LOT 중 긴급 오더 선별 → 대체 설비 경로 배정",
                    "WIP 기반 자동 투입 조절 로직 개발 (Phase 2 제안)",
                ], ensure_ascii=False),
                "confidence": 0.81,
                "analysis_duration_ms": 4150,
            },
        },
        {
            "anomaly": {
                "category": "wip",
                "severity": "warning",
                "title": "에이징 LOT 5건 — 24시간 이상 체류",
                "description": "LOT-991~995가 24시간 이상 동일 공정에 체류 중입니다.",
                "measured_value": 5.0,
                "threshold_value": 0.0,
                "affected_entity": "TFT-03",
                "status": "detected",
                "llm_analysis": "5개 LOT가 24시간 이상 TFT-03 공정에 정체되어 있습니다. 품질 열화 위험이 있으며, 원인 파악이 필요합니다.",
            },
            "rca": {
                "status": "done",
                "root_cause": "TFT-03 공정 WIP 적체로 인한 대기 시간 증가. 해당 LOT들은 WIP 적체 시작(EQ-005 정지) 직후 투입되어 처리 대기 중.",
                "cause_category": "process",
                "contributing_factors": json.dumps([
                    "TFT-03 WIP 170% 적체 (선행 이상과 연쇄)",
                    "해당 LOT들이 적체 시작 시점에 투입됨",
                    "우선순위 관리 부재 (FIFO만 적용, 긴급 오더 미반영)",
                ], ensure_ascii=False),
                "evidence": json.dumps([
                    "mes_lot_status: LOT-991~995 step_in_time > 24h ago",
                    "mes_queue_status: TFT-03 max_wait_min=1620 (27시간)",
                    "mes_wip_summary: TFT-03 적체 상태 지속 중",
                ], ensure_ascii=False),
                "recommendations": json.dumps([
                    "에이징 LOT 5건 우선 처리 (품질 열화 방지)",
                    "24시간 이상 체류 LOT 자동 알림 규칙 활성화",
                    "긴급 오더 우선순위 스케줄링 도입",
                ], ensure_ascii=False),
                "confidence": 0.75,
                "analysis_duration_ms": 1890,
            },
        },
        {
            "anomaly": {
                "category": "logistics",
                "severity": "warning",
                "title": "AGV 3대 동시 장애 — ERROR 상태",
                "description": "AGV-003, AGV-007, AGV-011 3대가 동시에 ERROR 상태입니다.",
                "measured_value": 3.0,
                "threshold_value": 2.0,
                "affected_entity": "AGV-003,AGV-007,AGV-011",
                "status": "detected",
                "llm_analysis": "전체 AGV 15대 중 3대(20%)가 동시 ERROR 상태. 단일 장애가 아닌 시스템적 이슈 가능성 검토 필요.",
                "llm_suggestion": json.dumps(["개별 AGV 에러 로그 확인", "충전 인프라 점검", "공통 원인 분석"], ensure_ascii=False),
            },
            "rca": {
                "status": "done",
                "root_cause": "배터리 관리 시스템(BMS) 펌웨어 v2.3.1 버그로 인한 동시 셧다운. 해당 펌웨어가 적용된 AGV 3대에서 동일 시간대에 BMS 통신 타임아웃 발생.",
                "cause_category": "equipment",
                "contributing_factors": json.dumps([
                    "BMS 펌웨어 v2.3.1 버그 (특정 충전 레벨에서 통신 끊김)",
                    "3대 모두 동일 시간대에 충전 80% 도달 → 버그 트리거",
                    "펌웨어 업데이트 미적용 (v2.3.2 패치 배포되었으나 미설치)",
                    "AGV 모니터링 시스템에서 BMS 경고 미감지",
                ], ensure_ascii=False),
                "evidence": json.dumps([
                    "mes_vehicle_status: AGV-003,007,011 동시 ERROR (14:25~14:27)",
                    "AGV 내부 로그: BMS_COMM_TIMEOUT 에러 (3대 공통)",
                    "충전 로그: 3대 모두 14:20~14:25 사이 80% 충전 도달",
                    "펌웨어 버전: 3대 모두 v2.3.1 (최신: v2.3.2)",
                    "정상 AGV 12대: 펌웨어 v2.3.0 또는 v2.3.2",
                ], ensure_ascii=False),
                "recommendations": json.dumps([
                    "AGV 3대 BMS 펌웨어 v2.3.2로 긴급 업데이트",
                    "수동 재시작 후 정상 가동 확인",
                    "나머지 v2.3.1 적용 AGV 식별 및 선제 업데이트",
                    "AGV BMS 모니터링 규칙 추가 (통신 타임아웃 감지)",
                    "펌웨어 배포 프로세스 개선 (자동 적용 또는 기한 관리)",
                ], ensure_ascii=False),
                "confidence": 0.94,
                "analysis_duration_ms": 5200,
            },
        },
        # ── 해결된 케이스 ──
        {
            "anomaly": {
                "category": "equipment",
                "severity": "critical",
                "title": "EQ-012 진공펌프 압력 이상 — 즉시 교체 완료",
                "description": "EQ-012 챔버 진공펌프 압력이 임계치를 초과했습니다. 교체 완료 후 정상 복구.",
                "measured_value": 8.5,
                "threshold_value": 5.0,
                "affected_entity": "EQ-012",
                "status": "resolved",
                "resolved_by": "김엔지니어",
                "llm_analysis": "EQ-012 진공펌프 압력이 8.5 Torr로 임계치(5.0 Torr)를 크게 초과. 즉시 교체가 필요한 수준입니다.",
                "llm_suggestion": json.dumps(["진공펌프 즉시 교체", "챔버 리크 테스트", "공정 재개 전 더미 런 3회"], ensure_ascii=False),
            },
            "rca": {
                "status": "done",
                "root_cause": "진공펌프 로터리 베인 마모로 인한 배기 효율 저하. 가동 6,800시간 누적으로 교체 주기(6,000h)를 초과한 상태에서 점진적 성능 저하 발생.",
                "cause_category": "equipment",
                "contributing_factors": json.dumps([
                    "로터리 베인 마모 (가동 6,800h, 교체주기 6,000h 초과)",
                    "오일 오염도 상승 (정기 교환 미실시)",
                    "챔버 내부 파티클 증가로 펌프 부하 가중",
                ], ensure_ascii=False),
                "evidence": json.dumps([
                    "mes_equipment_alarms: EQ-012 VACUUM_PRESSURE_HIGH 알람",
                    "펌프 압력 추이: 최근 1주간 3.2 → 5.1 → 8.5 Torr 상승",
                    "PM 이력: 진공펌프 교체 예정일 2주 경과",
                    "오일 분석: 오염도 NAS 9등급 (기준: 7등급 이하)",
                ], ensure_ascii=False),
                "recommendations": json.dumps([
                    "[완료] 진공펌프 신품 교체 (2시간 소요)",
                    "[완료] 챔버 리크 테스트 통과 (1.2E-9 Torr·L/s)",
                    "[완료] 더미 런 3회 정상 확인",
                    "PM 주기 재설정 (6,000h → 5,500h 단축 권장)",
                    "오일 자동 분석 센서 도입 검토",
                ], ensure_ascii=False),
                "confidence": 0.95,
                "analysis_duration_ms": 2100,
            },
        },
        {
            "anomaly": {
                "category": "logistics",
                "severity": "warning",
                "title": "LINE01-ZONE-C 반송 지연 — 경로 재설정 완료",
                "description": "LINE01-ZONE-C 구간에서 반송 시간이 평균 대비 3배 이상 지연되었습니다.",
                "measured_value": 180.0,
                "threshold_value": 60.0,
                "affected_entity": "LINE01-ZONE-C",
                "status": "resolved",
                "resolved_by": "박매니저",
                "llm_analysis": "LINE01-ZONE-C 반송 시간이 180초로 평균(60초) 대비 3배 지연. 해당 구간 컨베이어 속도 저하 또는 물리적 장애물 확인 필요.",
                "llm_suggestion": json.dumps(["컨베이어 벨트 상태 점검", "센서 정렬 확인", "우회 경로 활성화"], ensure_ascii=False),
            },
            "rca": {
                "status": "done",
                "root_cause": "ZONE-C 구간 광센서(PS-C03) 오정렬로 인한 캐리어 정지/재시작 반복. 전날 PM 작업 중 센서 브라켓이 3mm 틀어진 상태로 체결됨.",
                "cause_category": "equipment",
                "contributing_factors": json.dumps([
                    "광센서 PS-C03 오정렬 (PM 후 3mm 편차)",
                    "센서 오정렬 → 캐리어 감지 지연 → 정지/재시작 반복",
                    "PM 체크리스트에 센서 정렬 검증 항목 누락",
                ], ensure_ascii=False),
                "evidence": json.dumps([
                    "mes_transfer_log: ZONE-C 평균 반송시간 180초 (정상 55~65초)",
                    "컨베이어 PLC 로그: PS-C03 감지 지연 이벤트 47회/시간",
                    "PM 작업 이력: 전날 16:00 ZONE-C 정기 PM 수행",
                    "센서 진단: PS-C03 감지 거리 83mm (정상 80±1mm)",
                ], ensure_ascii=False),
                "recommendations": json.dumps([
                    "[완료] PS-C03 센서 브라켓 재정렬 (감지거리 80.2mm 확인)",
                    "[완료] 반송 시간 정상 복귀 확인 (평균 58초)",
                    "PM 체크리스트에 센서 정렬 검증 항목 추가",
                    "PM 후 자동 반송 테스트 절차 도입",
                ], ensure_ascii=False),
                "confidence": 0.91,
                "analysis_duration_ms": 3800,
            },
        },
    ]

    for i, item in enumerate(SAMPLE_DATA):
        a = item["anomaly"]
        resolved_at = "datetime('now', 'localtime')" if a.get("status") == "resolved" else "NULL"
        cursor = conn.execute(
            f"""INSERT INTO anomalies (category, severity, title, description,
               measured_value, threshold_value, affected_entity, status,
               llm_analysis, llm_suggestion, detected_at, resolved_at, resolved_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime', ?),
               {'datetime("now", "localtime")' if a.get("status") == "resolved" else 'NULL'}, ?)""",
            (
                a["category"], a["severity"], a["title"], a["description"],
                a.get("measured_value"), a.get("threshold_value"),
                a.get("affected_entity"), a.get("status", "detected"),
                a.get("llm_analysis"), a.get("llm_suggestion"),
                f"-{(len(SAMPLE_DATA) - i) * 10} minutes",
                a.get("resolved_by"),
            ),
        )
        anomaly_id = cursor.lastrowid

        r = item["rca"]
        conn.execute(
            """INSERT INTO rca_analyses (anomaly_id, status, root_cause, cause_category,
               contributing_factors, evidence, recommendations, confidence,
               analyzed_at, analysis_duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), ?)""",
            (
                anomaly_id, r["status"], r["root_cause"], r["cause_category"],
                r.get("contributing_factors"), r.get("evidence"),
                r.get("recommendations"), r.get("confidence"),
                r.get("analysis_duration_ms"),
            ),
        )

    conn.commit()
    logger.info("이상 + RCA 가상 데이터 %d건 삽입 완료", len(SAMPLE_DATA))


def _reset_injected_data(logger) -> None:
    """이전 주입 데이터를 정리하고 정상 상태로 복원."""
    from simulator.sqlite_backend import get_conn

    conn = get_conn()

    # 큐 데이터 (시나리오가 INSERT한 것) 삭제
    conn.execute("DELETE FROM mes_carrier_queue WHERE carrier_id LIKE 'CR-05%'")

    # 설비 정상 복원
    conn.execute("UPDATE mes_equipment_status SET status = 'RUN', last_status_change = NULL WHERE equipment_id = 'EQ-005'")

    # 비계획정지 + 알람 (시나리오가 INSERT한 것) 삭제
    conn.execute("DELETE FROM mes_down_history WHERE equipment_id = 'EQ-005' AND down_code = 'A-501'")
    conn.execute("DELETE FROM mes_equipment_alarms WHERE equipment_id = 'EQ-005'")
    conn.execute("DELETE FROM mes_equipment_alarms WHERE equipment_id LIKE 'AGV-%' AND alarm_code = 'V-101'")

    # WIP 정상 복원
    conn.execute("UPDATE mes_wip_summary SET current_wip = CAST(target_wip * 0.9 AS INTEGER) WHERE step_id IN ('TFT-03', 'TFT-04')")
    conn.execute("UPDATE mes_queue_status SET queue_count = 10, avg_wait_min = 20, max_wait_min = 45 WHERE step_id = 'TFT-03'")

    # 시나리오 WIP flow/snapshot 삭제
    conn.execute("DELETE FROM mes_wip_flow WHERE process = 'TFT' AND step_id = 'TFT-03' AND qty > 14")
    conn.execute("DELETE FROM mes_wip_snapshot WHERE process = 'TFT' AND wip_count > 500")

    # 에이징 LOT 삭제
    conn.execute("DELETE FROM mes_lot_status WHERE lot_id LIKE 'LOT-99%'")

    # AGV 정상 복원
    conn.execute("UPDATE mes_vehicle_status SET status = 'RUN' WHERE vehicle_id IN ('AGV-003', 'AGV-007', 'AGV-011')")

    # 감지된 이상 + RCA 초기화
    conn.execute("DELETE FROM rca_analyses")
    conn.execute("DELETE FROM anomalies")
    conn.execute("DELETE FROM detection_cycles")

    conn.commit()
    logger.info("이전 주입 데이터 초기화 완료")


def main():
    parser = argparse.ArgumentParser(description="이상 데이터 주입기")
    parser.add_argument("--db", default="simulator.db", help="SQLite DB 파일 (기본: simulator.db)")
    parser.add_argument("--speed", type=float, default=2.0, help="속도 배율 (기본: 2x)")
    parser.add_argument("--loop", action="store_true", help="주입 후 상황 악화 반복 (Ctrl+C로 중지)")
    parser.add_argument("--reset", action="store_true", help="이전 주입 데이터 초기화 후 재주입")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("injector")

    if not os.path.exists(args.db):
        logger.error("DB 파일 없음: %s", args.db)
        logger.error("먼저 실행: python init_db.py --db %s", args.db)
        sys.exit(1)

    # SQLite 연결
    from simulator.sqlite_backend import init_sqlite
    init_sqlite(args.db)

    # 이전 데이터 초기화
    if args.reset:
        _reset_injected_data(logger)

    from simulator.scenarios import (
        scenario_conveyor_overload,
        scenario_equipment_down,
        scenario_wip_surge,
        scenario_aging_lots,
        scenario_agv_failure,
        worsen_situation,
    )

    scenarios = [
        ("컨베이어 과부하", scenario_conveyor_overload),
        ("설비 비계획정지", scenario_equipment_down),
        ("WIP 적체", scenario_wip_surge),
        ("에이징 LOT", scenario_aging_lots),
        ("AGV 장애", scenario_agv_failure),
    ]

    interval = 60 / args.speed

    logger.info("=" * 50)
    logger.info("이상 데이터 주입 시작 (속도: %.1fx, 간격: %.0f초)", args.speed, interval)
    logger.info("=" * 50)

    for i, (name, fn) in enumerate(scenarios):
        if i > 0:
            logger.info("'%s' → %.0f초 후...", name, interval)
            time.sleep(interval)
        fn()
        logger.warning("=== 주입 완료: %s ===", name)

    logger.info("모든 시나리오 주입 완료!")

    # 이상 + RCA 가상 데이터 직접 삽입
    _inject_anomalies_with_rca(logger)

    if args.loop:
        logger.info("상황 악화 모드 (%.0f초마다, Ctrl+C로 중지)", interval)
        try:
            while True:
                time.sleep(interval)
                worsen_situation()
                logger.info("상황 악화 주입")
        except KeyboardInterrupt:
            logger.info("주입 중지")


if __name__ == "__main__":
    main()
