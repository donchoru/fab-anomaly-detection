"""이메일 알림 채널 — aiosmtplib."""

from __future__ import annotations

import logging
from email.message import EmailMessage
from typing import Any

import aiosmtplib

from alert.base import BaseAlertChannel
from config import settings

logger = logging.getLogger(__name__)


class EmailChannel(BaseAlertChannel):
    channel_name = "email"

    async def send(self, anomaly: dict[str, Any], message: str) -> bool:
        cfg = settings.alert
        if not cfg.smtp_host:
            logger.warning("SMTP not configured, skipping email")
            return False

        recipient = anomaly.get("_recipient", "")
        if not recipient:
            return False

        msg = EmailMessage()
        msg["Subject"] = f"[FAB-SENTINEL] [{anomaly.get('severity', 'WARNING').upper()}] {anomaly.get('title', '')}"
        msg["From"] = cfg.smtp_from
        msg["To"] = recipient
        msg.set_content(message)

        try:
            await aiosmtplib.send(
                msg,
                hostname=cfg.smtp_host,
                port=cfg.smtp_port,
                username=cfg.smtp_user or None,
                password=cfg.smtp_password or None,
                start_tls=True,
            )
            logger.info("Email sent to %s", recipient)
            return True
        except Exception:
            logger.exception("Email send failed to %s", recipient)
            return False
