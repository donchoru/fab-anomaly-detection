"""설비 관련 DB 쿼리 도구."""

from __future__ import annotations

from db.oracle import execute
from agent.tool_registry import registry


@registry.tool(description="설비 현재 상태 조회. RUN/IDLE/DOWN/PM 등.")
async def get_equipment_status(equipment_id: str = "", line_id: str = "") -> dict:
    """
    equipment_id: 설비 ID (비우면 전체)
    line_id: 라인 ID (비우면 전체)
    """
    conditions = []
    params: dict = {}
    if equipment_id:
        conditions.append("equipment_id = :eid")
        params["eid"] = equipment_id
    if line_id:
        conditions.append("line_id = :lid")
        params["lid"] = line_id
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    rows = await execute(
        f"""SELECT equipment_id, equipment_name, line_id, process, status,
                   last_status_change, current_recipe
            FROM mes_equipment_status {where}
            ORDER BY equipment_id""",
        params,
    )
    return {"equipment_status": rows}


@registry.tool(description="설비 가동률 조회. 최근 N시간 기준 RUN 시간 비율.")
async def get_equipment_utilization(line_id: str = "", hours: int = 8) -> dict:
    """
    line_id: 라인 ID (비우면 전체)
    hours: 분석 기간 (시간, 기본 8시간)
    """
    where = "AND line_id = :lid" if line_id else ""
    params: dict = {"hours": hours}
    if line_id:
        params["lid"] = line_id
    rows = await execute(
        f"""SELECT equipment_id, equipment_name, line_id,
                   ROUND(run_minutes / NULLIF(total_minutes, 0) * 100, 1) AS utilization_pct,
                   run_minutes, idle_minutes, down_minutes
            FROM (
                SELECT equipment_id, equipment_name, line_id,
                       SUM(CASE WHEN status = 'RUN' THEN duration_min ELSE 0 END) AS run_minutes,
                       SUM(CASE WHEN status = 'IDLE' THEN duration_min ELSE 0 END) AS idle_minutes,
                       SUM(CASE WHEN status = 'DOWN' THEN duration_min ELSE 0 END) AS down_minutes,
                       SUM(duration_min) AS total_minutes
                FROM mes_equipment_history
                WHERE event_time >= SYSTIMESTAMP - NUMTODSINTERVAL(:hours, 'HOUR') {where}
                GROUP BY equipment_id, equipment_name, line_id
            )
            ORDER BY utilization_pct ASC""",
        params,
    )
    return {"utilization": rows}


@registry.tool(description="비계획정지(Unscheduled Down) 이력. 최근 발생한 비계획정지 목록.")
async def get_unscheduled_downs(hours: int = 24, line_id: str = "") -> dict:
    """
    hours: 조회 기간 (시간, 기본 24시간)
    line_id: 라인 ID (비우면 전체)
    """
    where = "AND line_id = :lid" if line_id else ""
    params: dict = {"hours": hours}
    if line_id:
        params["lid"] = line_id
    rows = await execute(
        f"""SELECT equipment_id, equipment_name, line_id, down_code, down_reason,
                   start_time, end_time,
                   ROUND((NVL(end_time, SYSTIMESTAMP) - start_time) * 24 * 60, 1) AS down_min
            FROM mes_down_history
            WHERE down_type = 'UNSCHEDULED'
              AND start_time >= SYSTIMESTAMP - NUMTODSINTERVAL(:hours, 'HOUR') {where}
            ORDER BY start_time DESC""",
        params,
    )
    return {"unscheduled_downs": rows}


@registry.tool(description="PM(예방보전) 일정 조회. 향후 예정된 PM과 지연된 PM.")
async def get_pm_schedule(line_id: str = "") -> dict:
    """
    line_id: 라인 ID (비우면 전체)
    """
    where = "AND line_id = :lid" if line_id else ""
    params: dict = {"lid": line_id} if line_id else {}
    rows = await execute(
        f"""SELECT equipment_id, equipment_name, line_id, pm_type,
                   scheduled_date, status,
                   CASE WHEN scheduled_date < SYSDATE AND status = 'PENDING'
                        THEN 'OVERDUE' ELSE status END AS effective_status
            FROM mes_pm_schedule
            WHERE (scheduled_date >= SYSDATE - 7 OR status = 'PENDING') {where}
            ORDER BY scheduled_date""",
        params,
    )
    return {"pm_schedule": rows}


@registry.tool(description="설비 알람 이력 조회. 최근 발생한 설비 알람 목록.")
async def get_equipment_alarms(equipment_id: str = "", hours: int = 8) -> dict:
    """
    equipment_id: 설비 ID (비우면 전체)
    hours: 조회 기간 (시간, 기본 8시간)
    """
    where = "AND equipment_id = :eid" if equipment_id else ""
    params: dict = {"hours": hours}
    if equipment_id:
        params["eid"] = equipment_id
    rows = await execute(
        f"""SELECT equipment_id, alarm_code, alarm_name, severity,
                   alarm_time, clear_time, acknowledged
            FROM mes_equipment_alarms
            WHERE alarm_time >= SYSTIMESTAMP - NUMTODSINTERVAL(:hours, 'HOUR') {where}
            ORDER BY alarm_time DESC""",
        params,
    )
    return {"alarms": rows}
