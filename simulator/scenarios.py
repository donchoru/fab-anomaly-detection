"""이상 시나리오 — 시간에 따라 정상→이상 데이터 주입.

5개 시나리오가 시간차를 두고 발생:
1. [1분] 컨베이어 과부하: LINE03-ZONE-A 부하율 점진 상승
2. [2분] 설비 비계획정지: EQ-005 DOWN + 알람
3. [3분] WIP 적체: TFT 공정 WIP 급등 (설비 정지 영향)
4. [4분] 에이징 LOT: 특정 LOT 24시간+ 체류
5. [5분] AGV 장애: AGV 3대 ERROR 상태
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta

from simulator.sqlite_backend import get_conn

logger = logging.getLogger(__name__)


class ScenarioRunner:
    """시나리오를 시간차로 실행."""

    def __init__(self, speed: float = 1.0) -> None:
        """speed: 1.0 = 실시간, 2.0 = 2배속."""
        self.speed = speed
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Scenario runner started (speed=%.1fx)", self.speed)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run(self) -> None:
        scenarios = [
            (60, "컨베이어 과부하", scenario_conveyor_overload),
            (120, "설비 비계획정지", scenario_equipment_down),
            (180, "WIP 적체", scenario_wip_surge),
            (240, "에이징 LOT", scenario_aging_lots),
            (300, "AGV 장애", scenario_agv_failure),
        ]

        for delay_sec, name, fn in scenarios:
            if not self._running:
                break
            actual_delay = delay_sec / self.speed
            logger.info("Scenario '%s' scheduled in %.0f초", name, actual_delay)
            await asyncio.sleep(actual_delay)
            if not self._running:
                break
            logger.warning("=== SCENARIO: %s ===", name)
            fn()

        logger.info("All scenarios completed. Anomalies are now in the data.")

        # 이후 주기적으로 상황 악화
        while self._running:
            await asyncio.sleep(60 / self.speed)
            worsen_situation()


def scenario_conveyor_overload() -> None:
    """LINE03-ZONE-A 컨베이어 부하율을 95%+로 올림."""
    conn = get_conn()

    # LINE03-ZONE-A 부하율 급등
    conn.execute(
        "UPDATE mes_conveyor_status SET carrier_count = CAST(capacity * 0.96 AS INTEGER) WHERE zone_id = 'LINE03-ZONE-A'"
    )
    # LINE03-ZONE-B도 약간 상승
    conn.execute(
        "UPDATE mes_conveyor_status SET carrier_count = CAST(capacity * 0.88 AS INTEGER) WHERE zone_id = 'LINE03-ZONE-B'"
    )

    # 병목 큐 데이터 추가
    conn.execute(
        "INSERT INTO mes_carrier_queue (zone_id, line_id, carrier_id, wait_time_sec) VALUES ('LINE03-ZONE-A', 'LINE03', 'CR-0501', 450)"
    )
    conn.execute(
        "INSERT INTO mes_carrier_queue (zone_id, line_id, carrier_id, wait_time_sec) VALUES ('LINE03-ZONE-A', 'LINE03', 'CR-0502', 380)"
    )
    conn.execute(
        "INSERT INTO mes_carrier_queue (zone_id, line_id, carrier_id, wait_time_sec) VALUES ('LINE03-ZONE-A', 'LINE03', 'CR-0503', 520)"
    )

    conn.commit()
    logger.info("Injected: LINE03-ZONE-A conveyor load → 96%%")


def scenario_equipment_down() -> None:
    """EQ-005 비계획정지 + 알람 발생."""
    conn = get_conn()
    now = datetime.now().isoformat()

    # 설비 다운
    conn.execute(
        "UPDATE mes_equipment_status SET status = 'DOWN', last_status_change = ? WHERE equipment_id = 'EQ-005'",
        (now,),
    )

    # 비계획정지 기록
    conn.execute(
        """INSERT INTO mes_down_history
           (equipment_id, equipment_name, line_id, down_type, down_code, down_reason, start_time)
           VALUES ('EQ-005', '포토 설비', 'LINE01', 'UNSCHEDULED', 'A-501', '온도 이상으로 자동 정지', ?)""",
        (now,),
    )

    # 알람 기록
    conn.execute(
        """INSERT INTO mes_equipment_alarms
           (equipment_id, alarm_code, alarm_name, severity, alarm_time)
           VALUES ('EQ-005', 'A-501', '챔버 온도 상한 초과', 'CRITICAL', ?)""",
        (now,),
    )
    conn.execute(
        """INSERT INTO mes_equipment_alarms
           (equipment_id, alarm_code, alarm_name, severity, alarm_time)
           VALUES ('EQ-005', 'A-210', '공정 자동 중단', 'WARNING', ?)""",
        (now,),
    )

    conn.commit()
    logger.info("Injected: EQ-005 unscheduled down (A-501 온도 이상)")


def scenario_wip_surge() -> None:
    """TFT 공정 WIP 급등 — 설비 정지 영향으로 상류 적체."""
    conn = get_conn()
    now = datetime.now()

    # TFT 포토 스텝 WIP 급등
    conn.execute(
        "UPDATE mes_wip_summary SET current_wip = CAST(target_wip * 1.7 AS INTEGER) WHERE step_id = 'TFT-03'"
    )
    # TFT 식각도 영향
    conn.execute(
        "UPDATE mes_wip_summary SET current_wip = CAST(target_wip * 1.4 AS INTEGER) WHERE step_id = 'TFT-04'"
    )

    # 큐 길이 증가
    conn.execute(
        "UPDATE mes_queue_status SET queue_count = 45, avg_wait_min = 85, max_wait_min = 150 WHERE step_id = 'TFT-03'"
    )

    # WIP 흐름 불균형 (유입 >> 유출)
    for i in range(5):
        t = (now - timedelta(minutes=i * 10)).isoformat()
        conn.execute(
            "INSERT INTO mes_wip_flow (process, step_id, direction, qty, flow_time) VALUES ('TFT', 'TFT-03', 'IN', ?, ?)",
            (random.randint(15, 25), t),
        )
        conn.execute(
            "INSERT INTO mes_wip_flow (process, step_id, direction, qty, flow_time) VALUES ('TFT', 'TFT-03', 'OUT', ?, ?)",
            (random.randint(2, 5), t),
        )

    # WIP 스냅샷에 급등 기록
    conn.execute(
        "INSERT INTO mes_wip_snapshot (snapshot_time, process, wip_count) VALUES (?, 'TFT', 580)",
        (now.isoformat(),),
    )

    conn.commit()
    logger.info("Injected: TFT WIP surge (TFT-03 → 170%% of target)")


def scenario_aging_lots() -> None:
    """특정 LOT들이 24시간+ 체류 — HOLD 상태."""
    conn = get_conn()
    now = datetime.now()

    aging_lots = [
        ("LOT-9901", "PROD-A", "TFT-03", "포토", 36, 1, "설비 대기"),
        ("LOT-9902", "PROD-B", "TFT-03", "포토", 28, 1, "설비 대기"),
        ("LOT-9903", "PROD-A", "TFT-04", "식각", 30, 0, None),
        ("LOT-9904", "PROD-C", "CELL-01", "배향", 48, 1, "품질 이슈"),
        ("LOT-9905", "PROD-B", "TFT-03", "포토", 26, 1, "설비 대기"),
    ]

    for lot_id, prod, step, step_name, hours, hold, reason in aging_lots:
        step_in = (now - timedelta(hours=hours)).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO mes_lot_status (lot_id, product_id, current_step, step_name, step_in_time, hold_flag, hold_reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (lot_id, prod, step, step_name, step_in, hold, reason),
        )

    conn.commit()
    logger.info("Injected: 5 aging lots (26~48h)")


def scenario_agv_failure() -> None:
    """AGV 3대 ERROR 상태."""
    conn = get_conn()

    for vid in ["AGV-003", "AGV-007", "AGV-011"]:
        conn.execute(
            "UPDATE mes_vehicle_status SET status = 'ERROR' WHERE vehicle_id = ?",
            (vid,),
        )

    # 관련 알람
    now = datetime.now().isoformat()
    for vid in ["AGV-003", "AGV-007", "AGV-011"]:
        conn.execute(
            """INSERT INTO mes_equipment_alarms
               (equipment_id, alarm_code, alarm_name, severity, alarm_time)
               VALUES (?, 'V-101', '통신 이상', 'WARNING', ?)""",
            (vid, now),
        )

    conn.commit()
    logger.info("Injected: 3 AGVs → ERROR (AGV-003, 007, 011)")


def worsen_situation() -> None:
    """상황 점진적 악화 (반복 호출)."""
    conn = get_conn()

    # 컨베이어 부하 조금씩 상승
    conn.execute(
        "UPDATE mes_conveyor_status SET carrier_count = MIN(capacity, carrier_count + 2) WHERE zone_id = 'LINE03-ZONE-A'"
    )

    # WIP 계속 누적
    conn.execute(
        "UPDATE mes_wip_summary SET current_wip = current_wip + ? WHERE step_id = 'TFT-03'",
        (random.randint(1, 5),),
    )

    conn.commit()
