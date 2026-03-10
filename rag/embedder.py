"""임베딩 생성 — 사내 LLM의 /v1/embeddings 엔드포인트 사용."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """텍스트 목록을 임베딩 벡터로 변환.

    OpenAI 호환 /v1/embeddings API 사용.
    """
    cfg = settings.llm
    url = f"{cfg.base_url.rstrip('/')}/embeddings"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            json={
                "model": settings.rag.embedding_model,
                "input": texts,
            },
            headers={
                "Authorization": f"Bearer {cfg.api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    embeddings = [item["embedding"] for item in data["data"]]
    logger.debug("Embedded %d texts (dim=%d)", len(texts), len(embeddings[0]) if embeddings else 0)
    return embeddings


async def embed_query(text: str) -> list[float]:
    """단일 쿼리 텍스트 임베딩."""
    result = await embed_texts([text])
    return result[0]
