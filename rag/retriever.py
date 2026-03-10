"""RAG 검색기 — 이상 컨텍스트로 관련 전문지식 검색."""

from __future__ import annotations

import logging
from typing import Any

from rag.store import search
from rag.embedder import embed_query

logger = logging.getLogger(__name__)


async def retrieve_context(
    query: str,
    category: str | None = None,
    top_k: int = 5,
    min_score: float = 0.3,
) -> str:
    """이상 상황에 맞는 전문지식을 검색하여 LLM 컨텍스트로 구성.

    Args:
        query: 검색 쿼리 (이상 제목 + 분석 내용)
        category: 카테고리 필터 (logistics/wip/equipment, None이면 전체)
        top_k: 검색 결과 수
        min_score: 최소 유사도 (이하 제외)

    Returns: LLM에 주입할 전문지식 컨텍스트 문자열
    """
    try:
        query_emb = await embed_query(query)
        hits = search(query_emb, top_k=top_k, category=category)
    except Exception:
        logger.exception("RAG retrieval failed, proceeding without context")
        return ""

    # 유사도 필터링
    relevant = [h for h in hits if h["score"] >= min_score]

    if not relevant:
        return ""

    # 컨텍스트 구성
    lines = ["## 참고 전문지식 (RAG)", ""]
    for i, hit in enumerate(relevant, 1):
        lines.append(f"### [{i}] {hit['source']} > {hit['section']} (유사도: {hit['score']:.2f})")
        lines.append(hit["text"])
        lines.append("")

    context = "\n".join(lines)
    logger.info("RAG: retrieved %d relevant chunks for query (top score=%.2f)", len(relevant), relevant[0]["score"])
    return context


def build_search_query(rule: dict[str, Any], analysis: str = "") -> str:
    """규칙 + 분석 내용으로 검색 쿼리 구성."""
    parts = [
        rule.get("rule_name", ""),
        rule.get("category", ""),
        rule.get("subcategory", ""),
        analysis,
    ]
    return " ".join(p for p in parts if p)
