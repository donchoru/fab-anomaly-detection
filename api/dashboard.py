"""대시보드 데이터 API — 개요, 타임라인, 히트맵."""

from __future__ import annotations

from fastapi import APIRouter

from db.oracle import execute

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview")
async def overview():
    """현재 이상 현황 요약."""
    rows = await execute(
        """SELECT
             COUNT(*) AS total,
             SUM(CASE WHEN status = 'detected' THEN 1 ELSE 0 END) AS detected,
             SUM(CASE WHEN status = 'acknowledged' THEN 1 ELSE 0 END) AS acknowledged,
             SUM(CASE WHEN status = 'investigating' THEN 1 ELSE 0 END) AS investigating,
             SUM(CASE WHEN severity = 'critical' AND status IN ('detected','acknowledged','investigating') THEN 1 ELSE 0 END) AS active_critical,
             SUM(CASE WHEN severity = 'warning' AND status IN ('detected','acknowledged','investigating') THEN 1 ELSE 0 END) AS active_warning
           FROM sentinel_anomalies
           WHERE detected_at >= SYSTIMESTAMP - INTERVAL '24' HOUR"""
    )
    overview_data = rows[0] if rows else {}

    # 최근 사이클 정보
    cycles = await execute(
        """SELECT * FROM sentinel_detection_cycles
           ORDER BY started_at DESC FETCH NEXT 1 ROWS ONLY"""
    )

    return {
        "anomaly_summary": overview_data,
        "last_cycle": cycles[0] if cycles else None,
    }


@router.get("/timeline")
async def timeline(hours: int = 24):
    """시간별 이상 발생 타임라인."""
    rows = await execute(
        """SELECT TRUNC(detected_at, 'HH24') AS hour_slot,
                  category, severity, COUNT(*) AS count
           FROM sentinel_anomalies
           WHERE detected_at >= SYSTIMESTAMP - NUMTODSINTERVAL(:hours, 'HOUR')
           GROUP BY TRUNC(detected_at, 'HH24'), category, severity
           ORDER BY hour_slot""",
        {"hours": hours},
    )
    return {"timeline": rows}


@router.get("/heatmap")
async def heatmap():
    """카테고리 x 심각도 히트맵."""
    rows = await execute(
        """SELECT category, severity, COUNT(*) AS count
           FROM sentinel_anomalies
           WHERE detected_at >= SYSTIMESTAMP - INTERVAL '24' HOUR
             AND status IN ('detected', 'acknowledged', 'investigating')
           GROUP BY category, severity
           ORDER BY category, severity"""
    )
    return {"heatmap": rows}
