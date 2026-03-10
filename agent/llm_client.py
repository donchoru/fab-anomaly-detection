"""OpenAI-compatible LLM client via httpx."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        cfg = settings.llm
        self.base_url = cfg.base_url.rstrip("/")
        self.api_key = cfg.api_key
        self.model = cfg.model
        self.timeout = cfg.timeout
        self.max_tokens = cfg.max_tokens
        self.temperature = cfg.temperature

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Call /v1/chat/completions and return the response message."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        message = choice["message"]
        logger.debug(
            "LLM response: finish_reason=%s tool_calls=%s",
            choice.get("finish_reason"),
            bool(message.get("tool_calls")),
        )
        return message

    async def simple_chat(self, system: str, user: str) -> str:
        """Simple chat without tools, returns content string."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        msg = await self.chat(messages)
        return msg.get("content", "")


llm_client = LLMClient()
