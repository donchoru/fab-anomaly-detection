"""원인분석(RCA) 에이전트 — anomaly.detected 토픽 구독 → 근본원인 분석."""

from __future__ import annotations

import json
import logging
from typing import Any

from agent.agent_loop import run_agent_loop
from agent.prompts import RCA_SYSTEM
from bus.topic import Message, bus, TOPIC_ANOMALY_DETECTED, TOPIC_RCA_COMPLETED, TOPIC_ALERT_REQUEST
from db import queries

logger = logging.getLogger(__name__)


def register() -> None:
    """토픽 버스에 RCA 에이전트 핸들러 등록."""
    bus.subscribe(TOPIC_ANOMALY_DETECTED, handle_anomaly)
    logger.info("RCA agent registered on topic=%s", TOPIC_ANOMALY_DETECTED)


async def handle_anomaly(msg: Message) -> None:
    """anomaly.detected 토픽 메시지 수신 → RCA 분석 실행."""
    payload = msg.payload
    anomaly_id = payload["anomaly_id"]
    logger.info("RCA agent received anomaly_id=%d", anomaly_id)

    try:
        result = await _run_rca(payload)

        # DB에 분석 결과 저장
        await queries.update_anomaly_rca(
            anomaly_id=anomaly_id,
            analysis=result.get("root_cause", "분석 실패"),
            suggestion=json.dumps(
                result.get("suggested_actions", []),
                ensure_ascii=False,
            ),
        )

        logger.info(
            "RCA completed: anomaly_id=%d root_cause=%s confidence=%.2f",
            anomaly_id,
            result.get("root_cause", "?")[:80],
            result.get("confidence", 0),
        )

        # RCA 완료 토픽 발행
        await bus.publish(
            topic=TOPIC_RCA_COMPLETED,
            payload={
                "anomaly_id": anomaly_id,
                "rca_result": result,
                "severity": payload.get("severity", "warning"),
                "title": payload.get("title", ""),
                "category": payload.get("rule", {}).get("category", ""),
            },
            source="rca_agent",
        )

        # 알림 요청 토픽 발행
        await bus.publish(
            topic=TOPIC_ALERT_REQUEST,
            payload={
                "anomaly_id": anomaly_id,
                "severity": payload.get("severity", "warning"),
                "category": payload.get("rule", {}).get("category", ""),
                "title": payload.get("title", ""),
                "analysis": result.get("root_cause", ""),
                "suggested_actions": result.get("suggested_actions", []),
            },
            source="rca_agent",
        )

    except Exception:
        logger.exception("RCA failed for anomaly_id=%d", anomaly_id)
        await queries.update_anomaly_rca(
            anomaly_id=anomaly_id,
            analysis="RCA 분석 중 오류 발생",
            suggestion="수동 분석 필요",
        )


async def _run_rca(payload: dict[str, Any]) -> dict[str, Any]:
    """ReAct 루프로 근본원인 분석."""
    user_msg = _build_rca_message(payload)
    return await run_agent_loop(
        system_prompt=RCA_SYSTEM,
        user_message=user_msg,
        max_rounds=3,
    )


def _build_rca_message(payload: dict[str, Any]) -> str:
    rule = payload.get("rule", {})
    query_result = payload.get("query_result", [])
    return f"""## 이상 감지 — 근본원인 분석 요청

**이상 ID**: {payload['anomaly_id']}
**제목**: {payload.get('title', '')}
**심각도**: {payload.get('severity', 'warning')}
**카테고리**: {rule.get('category', '')} / {rule.get('subcategory', '')}
**측정값**: {payload.get('measured_value', '')}
**영향 엔티티**: {payload.get('affected_entity', '')}

### 감지 에이전트 분석
{payload.get('analysis', '정보 없음')}

### 원본 데이터 (일부)
```json
{json.dumps(query_result[:10], default=str, ensure_ascii=False, indent=2)}
```

위 이상의 근본 원인을 분석하세요.
제공된 도구로 관련 설비/공정/물류 데이터를 추가 조회하여
원인을 좁혀가세요.
"""
