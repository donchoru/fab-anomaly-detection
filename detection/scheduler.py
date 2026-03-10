"""감지 주기 오케스트레이션."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from db import queries
from detection.evaluator import evaluate_and_detect

logger = logging.getLogger(__name__)


async def run_detection_cycle() -> dict[str, Any]:
    """감지 사이클 1회 실행.

    1. 활성 규칙 로드
    2. 규칙별 평가 (임계치 + AI)
    3. 이상 생성 + 토픽 발행 (evaluator가 처리)
    4. 사이클 로그 기록

    Returns: cycle summary dict
    """
    start = time.monotonic()
    cycle_id = await queries.start_cycle()
    logger.info("Detection cycle %d started", cycle_id)

    rules = await queries.get_active_rules()
    anomalies_found = 0

    for rule in rules:
        try:
            anomaly = await evaluate_and_detect(rule)
            if anomaly:
                anomalies_found += 1
        except Exception:
            logger.exception("Rule evaluation failed: rule_id=%s", rule.get("rule_id"))

    duration_ms = int((time.monotonic() - start) * 1000)
    await queries.complete_cycle(cycle_id, len(rules), anomalies_found, duration_ms)

    summary = {
        "cycle_id": cycle_id,
        "rules_evaluated": len(rules),
        "anomalies_found": anomalies_found,
        "duration_ms": duration_ms,
    }
    logger.info("Detection cycle %d completed: %s", cycle_id, summary)
    return summary
