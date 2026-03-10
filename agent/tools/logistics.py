"""물류 부하 관련 DB 쿼리 도구."""

from __future__ import annotations

from db.oracle import execute
from agent.tool_registry import registry


@registry.tool(description="컨베이어 라인별 현재 부하율(%) 조회. zone별 WIP 수량 대비 용량 비율.")
async def get_conveyor_load(zone: str = "") -> dict:
    """
    zone: 존 ID (비우면 전체)
    """
    where = "WHERE zone_id = :zone" if zone else ""
    params = {"zone": zone} if zone else {}
    rows = await execute(
        f"""SELECT zone_id, line_id, carrier_count, capacity,
                   ROUND(carrier_count / NULLIF(capacity, 0) * 100, 1) AS load_pct
            FROM mes_conveyor_status {where}
            ORDER BY load_pct DESC""",
        params,
    )
    return {"conveyor_load": rows}


@registry.tool(description="최근 1시간 반송 처리량(moves/hour). 라인별 반송 완료 건수.")
async def get_transfer_throughput(line_id: str = "") -> dict:
    """
    line_id: 라인 ID (비우면 전체)
    """
    where = "AND line_id = :line" if line_id else ""
    params = {"line": line_id} if line_id else {}
    rows = await execute(
        f"""SELECT line_id, COUNT(*) AS moves_1h,
                   ROUND(AVG(transfer_time_sec), 1) AS avg_time_sec
            FROM mes_transfer_log
            WHERE transfer_time >= SYSTIMESTAMP - INTERVAL '1' HOUR {where}
            GROUP BY line_id ORDER BY moves_1h DESC""",
        params,
    )
    return {"throughput": rows}


@registry.tool(description="현재 물류 병목 존 감지. 대기 시간이 임계치(기본 300초) 초과인 존.")
async def get_bottleneck_zones(wait_threshold_sec: int = 300) -> dict:
    """
    wait_threshold_sec: 대기 시간 임계치(초)
    """
    rows = await execute(
        """SELECT zone_id, line_id, AVG(wait_time_sec) AS avg_wait,
                  MAX(wait_time_sec) AS max_wait, COUNT(*) AS carrier_count
           FROM mes_carrier_queue
           WHERE wait_time_sec > :threshold
           GROUP BY zone_id, line_id
           ORDER BY avg_wait DESC""",
        {"threshold": wait_threshold_sec},
    )
    return {"bottleneck_zones": rows}


@registry.tool(description="AGV/OHT 반송 설비 가동률. 현재 상태별 대수.")
async def get_agv_utilization(vehicle_type: str = "") -> dict:
    """
    vehicle_type: AGV 또는 OHT (비우면 전체)
    """
    where = "WHERE vehicle_type = :vtype" if vehicle_type else ""
    params = {"vtype": vehicle_type} if vehicle_type else {}
    rows = await execute(
        f"""SELECT vehicle_type, status,
                   COUNT(*) AS count,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY vehicle_type), 1) AS pct
            FROM mes_vehicle_status {where}
            GROUP BY vehicle_type, status
            ORDER BY vehicle_type, status""",
        params,
    )
    return {"agv_utilization": rows}


@registry.tool(description="특정 존의 최근 반송 이력 (최근 20건).")
async def get_zone_transfer_history(zone_id: str) -> dict:
    """
    zone_id: 존 ID
    """
    rows = await execute(
        """SELECT carrier_id, from_zone, to_zone, transfer_time, transfer_time_sec, status
           FROM mes_transfer_log
           WHERE from_zone = :zone OR to_zone = :zone
           ORDER BY transfer_time DESC
           FETCH NEXT 20 ROWS ONLY""",
        {"zone": zone_id},
    )
    return {"transfer_history": rows}
