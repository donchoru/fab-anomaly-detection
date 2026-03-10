"""알림 채널 ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAlertChannel(ABC):
    channel_name: str = "base"

    @abstractmethod
    async def send(self, anomaly: dict[str, Any], message: str) -> bool:
        """알림 발송. 성공 시 True."""
        ...
