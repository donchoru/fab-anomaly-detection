"""알림 라우터 — 규칙 기반 채널 매핑 + 토픽 구독."""

from __future__ import annotations

import logging
from typing import Any

from alert.base import BaseAlertChannel
from alert.dashboard import DashboardChannel
from alert.email_channel import EmailChannel
from alert.messenger import MessengerChannel
from bus.topic import Message, bus, TOPIC_ALERT_REQUEST
from db import queries

logger = logging.getLogger(__name__)

# 채널 인스턴스
_channels: dict[str, BaseAlertChannel] = {
    "dashboard": DashboardChannel(),
    "email": EmailChannel(),
    "messenger": MessengerChannel(),
}

SEVERITY_ORDER = {"warning": 1, "critical": 2}


def register() -> None:
    """토픽 버스에 알림 라우터 등록."""
    bus.subscribe(TOPIC_ALERT_REQUEST, handle_alert_request)
    logger.info("Alert router registered on topic=%s", TOPIC_ALERT_REQUEST)


async def handle_alert_request(msg: Message) -> None:
    """alert.request 토픽 수신 → 라우팅 규칙에 따라 발송."""
    payload = msg.payload
    anomaly_id = payload.get("anomaly_id")
    severity = payload.get("severity", "warning")
    category = payload.get("category", "")

    message = _format_message(payload)

    # DB에서 라우팅 규칙 로드
    routes = await queries.get_alert_routes(enabled_only=True)
    matched_routes = _match_routes(routes, category, severity)

    if not matched_routes:
        # 기본: 대시보드에 무조건 발송
        matched_routes = [{"channel": "dashboard", "recipient": "", "escalation_delay_min": 0}]

    for route in matched_routes:
        channel_name = route["channel"]
        channel = _channels.get(channel_name)
        if not channel:
            logger.warning("Unknown channel: %s", channel_name)
            continue

        anomaly_data = {
            "anomaly_id": anomaly_id,
            "severity": severity,
            "title": payload.get("title", ""),
            "_recipient": route.get("recipient", ""),
            "_webhook_url": "",
        }

        delivered = await channel.send(anomaly_data, message)

        await queries.insert_alert({
            "anomaly_id": anomaly_id,
            "channel": channel_name,
            "recipient": route.get("recipient", ""),
            "delivered": 1 if delivered else 0,
            "error_msg": "" if delivered else "delivery_failed",
        })


def _match_routes(
    routes: list[dict[str, Any]], category: str, severity: str
) -> list[dict[str, Any]]:
    """라우팅 규칙 매칭."""
    matched = []
    sev_level = SEVERITY_ORDER.get(severity, 0)

    for route in routes:
        route_cat = route.get("category")
        if route_cat and route_cat != category:
            continue

        min_sev = SEVERITY_ORDER.get(route.get("severity_min", "warning"), 1)
        if sev_level < min_sev:
            continue

        if route.get("escalation_delay_min", 0) == 0:
            matched.append(route)

    return matched


def _format_message(payload: dict[str, Any]) -> str:
    """알림 메시지 포맷."""
    lines = [
        f"## 이상 감지 알림",
        f"**ID**: {payload.get('anomaly_id')}",
        f"**심각도**: {payload.get('severity', 'warning').upper()}",
        f"**제목**: {payload.get('title', '')}",
        f"",
        f"### 분석",
        payload.get("analysis", "분석 정보 없음"),
    ]

    actions = payload.get("suggested_actions", [])
    if actions:
        lines.append("")
        lines.append("### 권장 조치")
        for i, action in enumerate(actions, 1):
            lines.append(f"{i}. {action}")

    return "\n".join(lines)
