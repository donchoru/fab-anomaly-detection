"""에스컬레이션 — 미확인 이상 상위 채널 재알림."""

from __future__ import annotations

import logging
from typing import Any

from bus.topic import bus, TOPIC_ALERT_REQUEST
from db import queries
from db.oracle import execute

logger = logging.getLogger(__name__)


async def check_escalations() -> int:
    """미확인 이상에 대한 에스컬레이션 확인.

    escalation_delay_min > 0인 라우팅 규칙과 매칭되는
    detected 상태 이상을 찾아 재알림.

    Returns: escalated count
    """
    # 에스컬레이션 대상 라우팅 규칙
    routes = await queries.get_alert_routes(enabled_only=True)
    esc_routes = [r for r in routes if r.get("escalation_delay_min", 0) > 0]
    if not esc_routes:
        return 0

    count = 0
    for route in esc_routes:
        delay_min = route["escalation_delay_min"]
        category = route.get("category")

        # 미확인 이상 중 delay 시간 초과한 것
        cat_where = "AND a.category = :cat" if category else ""
        params: dict[str, Any] = {"delay": delay_min}
        if category:
            params["cat"] = category

        unacked = await execute(
            f"""SELECT a.anomaly_id, a.severity, a.title, a.category,
                       a.llm_analysis, a.llm_suggestion
                FROM sentinel_anomalies a
                WHERE a.status = 'detected'
                  AND a.detected_at <= SYSTIMESTAMP - NUMTODSINTERVAL(:delay, 'MINUTE')
                  {cat_where}
                  AND NOT EXISTS (
                      SELECT 1 FROM sentinel_alert_history h
                      WHERE h.anomaly_id = a.anomaly_id
                        AND h.channel = :channel
                  )""",
            {**params, "channel": route["channel"]},
        )

        for anomaly in unacked:
            await bus.publish(
                topic=TOPIC_ALERT_REQUEST,
                payload={
                    "anomaly_id": anomaly["anomaly_id"],
                    "severity": anomaly.get("severity", "warning"),
                    "category": anomaly.get("category", ""),
                    "title": f"[ESCALATED] {anomaly.get('title', '')}",
                    "analysis": anomaly.get("llm_analysis", ""),
                    "suggested_actions": [],
                },
                source="escalation",
            )
            count += 1

    if count:
        logger.info("Escalated %d anomalies", count)
    return count
