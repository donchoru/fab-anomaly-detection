"""사내 메신저 웹훅 채널."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from alert.base import BaseAlertChannel
from config import settings

logger = logging.getLogger(__name__)


class MessengerChannel(BaseAlertChannel):
    channel_name = "messenger"

    async def send(self, anomaly: dict[str, Any], message: str) -> bool:
        url = anomaly.get("_webhook_url") or settings.alert.messenger_webhook_url
        if not url:
            logger.warning("Messenger webhook not configured")
            return False

        severity = anomaly.get("severity", "warning").upper()
        payload = {
            "title": f"[FAB-SENTINEL] [{severity}] {anomaly.get('title', '')}",
            "body": message,
            "severity": severity,
            "anomaly_id": anomaly.get("anomaly_id"),
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            logger.info("Messenger webhook sent")
            return True
        except Exception:
            logger.exception("Messenger webhook failed")
            return False
