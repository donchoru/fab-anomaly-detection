"""이상감지 에이전트 — 이상 감지 후 토픽 발행."""

from __future__ import annotations

import logging
from typing import Any

from agent.agent_loop import run_agent_loop
from agent.prompts import DETECTION_SYSTEM
from bus.topic import bus, TOPIC_ANOMALY_DETECTED
from db import queries

logger = logging.getLogger(__name__)


async def analyze_and_publish(
    rule: dict[str, Any],
    measured_value: float,
    query_result: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """LLM으로 이상 분석 후 토픽에 발행.

    1. ReAct 루프로 이상 여부 판단
    2. 이상이면 DB에 anomaly 레코드 생성
    3. anomaly.detected 토픽에 발행 → RCA 에이전트가 수신
    """
    user_msg = _build_user_message(rule, measured_value, query_result)

    result = await run_agent_loop(
        system_prompt=DETECTION_SYSTEM,
        user_message=user_msg,
        max_rounds=3,
    )

    if result.get("parse_error"):
        logger.warning("Detection LLM parse error for rule=%s", rule["rule_name"])
        return None

    if not result.get("is_anomaly", False):
        logger.info("Rule %s: no anomaly (confidence=%.2f)", rule["rule_name"], result.get("confidence", 0))
        return None

    severity = result.get("severity", "warning")
    anomaly_data = {
        "rule_id": rule["rule_id"],
        "category": rule["category"],
        "severity": severity,
        "title": result.get("title", rule["rule_name"]),
        "description": result.get("analysis", ""),
        "measured_value": measured_value,
        "threshold_value": rule.get("critical_value") if severity == "critical" else rule.get("warning_value"),
        "affected_entity": result.get("affected_entity", ""),
    }

    anomaly_id = await queries.insert_anomaly(anomaly_data)
    logger.info("Anomaly created: id=%d rule=%s severity=%s", anomaly_id, rule["rule_name"], severity)

    # 토픽 발행 → RCA 에이전트가 구독
    await bus.publish(
        topic=TOPIC_ANOMALY_DETECTED,
        payload={
            "anomaly_id": anomaly_id,
            "rule": rule,
            "severity": severity,
            "title": result.get("title", ""),
            "analysis": result.get("analysis", ""),
            "measured_value": measured_value,
            "affected_entity": result.get("affected_entity", ""),
            "query_result": query_result,
        },
        source="detection_agent",
    )

    return {**anomaly_data, "anomaly_id": anomaly_id}


async def analyze_without_llm(
    rule: dict[str, Any],
    measured_value: float,
    severity: str,
) -> dict[str, Any]:
    """LLM 없이 임계치 기반 이상 생성 + 토픽 발행."""
    title = f"[{rule['category'].upper()}] {rule['rule_name']} - {severity}"
    anomaly_data = {
        "rule_id": rule["rule_id"],
        "category": rule["category"],
        "severity": severity,
        "title": title,
        "description": f"측정값 {measured_value} 이 임계치를 초과",
        "measured_value": measured_value,
        "threshold_value": rule.get("critical_value") if severity == "critical" else rule.get("warning_value"),
        "affected_entity": "",
    }

    anomaly_id = await queries.insert_anomaly(anomaly_data)
    logger.info("Anomaly (no-llm) created: id=%d rule=%s", anomaly_id, rule["rule_name"])

    await bus.publish(
        topic=TOPIC_ANOMALY_DETECTED,
        payload={
            "anomaly_id": anomaly_id,
            "rule": rule,
            "severity": severity,
            "title": title,
            "analysis": anomaly_data["description"],
            "measured_value": measured_value,
            "affected_entity": "",
            "query_result": [],
        },
        source="detection_agent",
    )

    return {**anomaly_data, "anomaly_id": anomaly_id}


def _build_user_message(
    rule: dict[str, Any],
    measured_value: float,
    query_result: list[dict[str, Any]],
) -> str:
    import json
    return f"""## 규칙 위반 감지

**규칙**: {rule['rule_name']}
**카테고리**: {rule['category']} / {rule.get('subcategory', '')}
**검사 유형**: {rule['check_type']}
**측정값**: {measured_value}
**경고 임계치**: {rule.get('warning_value', 'N/A')}
**위험 임계치**: {rule.get('critical_value', 'N/A')}

### 쿼리 결과 (원본 데이터)
```json
{json.dumps(query_result[:20], default=str, ensure_ascii=False, indent=2)}
```

{rule.get('llm_prompt', '')}

위 데이터를 분석하여 실제 이상 여부를 판단하세요.
필요시 도구를 사용하여 추가 데이터를 조회하세요.
"""
