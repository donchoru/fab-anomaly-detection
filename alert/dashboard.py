"""대시보드 채널 — DB 기록 + WebSocket 브로드캐스트."""

from __future__ import annotations

import json
import logging
from typing import Any

from alert.base import BaseAlertChannel

logger = logging.getLogger(__name__)

# 연결된 WebSocket 클라이언트
_ws_clients: set = set()


def register_ws(ws) -> None:
    _ws_clients.add(ws)


def unregister_ws(ws) -> None:
    _ws_clients.discard(ws)


class DashboardChannel(BaseAlertChannel):
    channel_name = "dashboard"

    async def send(self, anomaly: dict[str, Any], message: str) -> bool:
        payload = json.dumps({
            "type": "anomaly",
            "anomaly_id": anomaly.get("anomaly_id"),
            "severity": anomaly.get("severity"),
            "title": anomaly.get("title", ""),
            "message": message,
        }, ensure_ascii=False)

        dead: list = []
        for ws in _ws_clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            _ws_clients.discard(ws)

        logger.info("Dashboard alert sent to %d clients", len(_ws_clients) - len(dead))
        return True
