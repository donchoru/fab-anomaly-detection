"""시스템 API — 헬스체크, 수동 트리거, 통계."""

from __future__ import annotations

from fastapi import APIRouter

from config import settings
from detection.scheduler import run_detection_cycle
from db.oracle import execute

router = APIRouter(tags=["system"])


@router.get("/health")
async def health():
    try:
        rows = await execute("SELECT 1 AS ok")
        db_ok = bool(rows)
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "disconnected",
    }


@router.post("/api/detect/trigger")
async def trigger_detection():
    """감지 사이클 수동 트리거."""
    result = await run_detection_cycle()
    return result


@router.get("/api/stats")
async def stats():
    """시스템 통계."""
    rules = await execute("SELECT COUNT(*) AS cnt FROM detection_rules WHERE enabled = 1")
    anomalies_24h = await execute(
        """SELECT COUNT(*) AS cnt FROM anomalies
           WHERE detected_at >= SYSTIMESTAMP - INTERVAL '24' HOUR"""
    )
    cycles_24h = await execute(
        """SELECT COUNT(*) AS cnt, AVG(duration_ms) AS avg_ms
           FROM detection_cycles
           WHERE started_at >= SYSTIMESTAMP - INTERVAL '24' HOUR"""
    )

    return {
        "active_rules": rules[0]["cnt"] if rules else 0,
        "anomalies_24h": anomalies_24h[0]["cnt"] if anomalies_24h else 0,
        "cycles_24h": cycles_24h[0] if cycles_24h else {},
    }
