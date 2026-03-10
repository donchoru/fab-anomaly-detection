"""재공(WIP) 관련 DB 쿼리 도구."""

from __future__ import annotations

from db.oracle import execute
from agent.tool_registry import registry


@registry.tool(description="공정별 현재 WIP 수준. 목표 대비 실제 WIP 비율.")
async def get_wip_levels(process: str = "") -> dict:
    """
    process: 공정명 (TFT/CELL/MODULE, 비우면 전체)
    """
    where = "WHERE process = :proc" if process else ""
    params = {"proc": process} if process else {}
    rows = await execute(
        f"""SELECT process, step_id, step_name, current_wip, target_wip,
                   ROUND(current_wip / NULLIF(target_wip, 0) * 100, 1) AS wip_ratio_pct
            FROM mes_wip_summary {where}
            ORDER BY wip_ratio_pct DESC""",
        params,
    )
    return {"wip_levels": rows}


@registry.tool(description="공정 간 흐름 밸런스. 유입량 vs 유출량 비교.")
async def get_flow_balance(hours: int = 4) -> dict:
    """
    hours: 분석 기간 (시간, 기본 4시간)
    """
    rows = await execute(
        """SELECT process, step_id,
                  SUM(CASE WHEN direction = 'IN' THEN qty ELSE 0 END) AS inflow,
                  SUM(CASE WHEN direction = 'OUT' THEN qty ELSE 0 END) AS outflow,
                  SUM(CASE WHEN direction = 'IN' THEN qty ELSE 0 END)
                    - SUM(CASE WHEN direction = 'OUT' THEN qty ELSE 0 END) AS net_wip
           FROM mes_wip_flow
           WHERE flow_time >= SYSTIMESTAMP - NUMTODSINTERVAL(:hours, 'HOUR')
           GROUP BY process, step_id
           ORDER BY net_wip DESC""",
        {"hours": hours},
    )
    return {"flow_balance": rows}


@registry.tool(description="큐 길이 조회. 각 공정 스텝 앞 대기 중인 LOT 수.")
async def get_queue_length(step_id: str = "") -> dict:
    """
    step_id: 스텝 ID (비우면 전체)
    """
    where = "WHERE step_id = :step" if step_id else ""
    params = {"step": step_id} if step_id else {}
    rows = await execute(
        f"""SELECT step_id, step_name, queue_count, avg_wait_min,
                   max_wait_min
            FROM mes_queue_status {where}
            ORDER BY queue_count DESC""",
        params,
    )
    return {"queue_length": rows}


@registry.tool(description="에이징(장기 체류) LOT 조회. 기준시간 초과 체류 LOT.")
async def get_aging_lots(hours_threshold: int = 24) -> dict:
    """
    hours_threshold: 에이징 기준 시간 (기본 24시간)
    """
    rows = await execute(
        """SELECT lot_id, product_id, current_step, step_name,
                  ROUND((SYSDATE - step_in_time) * 24, 1) AS hours_in_step,
                  hold_flag, hold_reason
           FROM mes_lot_status
           WHERE (SYSDATE - step_in_time) * 24 > :threshold
           ORDER BY hours_in_step DESC""",
        {"threshold": hours_threshold},
    )
    return {"aging_lots": rows}


@registry.tool(description="WIP 추이 트렌드. 최근 N시간의 시간별 WIP 변화.")
async def get_wip_trend(process: str, hours: int = 24) -> dict:
    """
    process: 공정명 (TFT/CELL/MODULE)
    hours: 조회 기간 (시간, 기본 24시간)
    """
    rows = await execute(
        """SELECT TRUNC(snapshot_time, 'HH24') AS hour_slot,
                  process, SUM(wip_count) AS total_wip
           FROM mes_wip_snapshot
           WHERE process = :proc
             AND snapshot_time >= SYSTIMESTAMP - NUMTODSINTERVAL(:hours, 'HOUR')
           GROUP BY TRUNC(snapshot_time, 'HH24'), process
           ORDER BY hour_slot""",
        {"proc": process, "hours": hours},
    )
    return {"wip_trend": rows}
