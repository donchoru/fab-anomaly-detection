"""지식 문서 로더 — 마크다운 파일을 청크로 분할 + Milvus에 저장."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from rag.store import init_store, insert_chunks, drop_collection
from rag.embedder import embed_texts

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")

# 카테고리 매핑 (파일명 → 카테고리)
FILE_CATEGORIES = {
    "equipment.md": "equipment",
    "process.md": "wip",
    "logistics.md": "logistics",
    "incidents.md": "incidents",
}


def chunk_markdown(text: str, source: str, category: str, max_chunk: int = 1000) -> list[dict[str, Any]]:
    """마크다운을 ## 섹션 기준으로 청크 분할."""
    chunks = []
    current_section = ""
    current_text = ""

    for line in text.split("\n"):
        if line.startswith("## "):
            if current_text.strip():
                chunks.append({
                    "text": current_text.strip(),
                    "source": source,
                    "category": category,
                    "section": current_section,
                })
            current_section = line.lstrip("# ").strip()
            current_text = line + "\n"
        elif line.startswith("### "):
            # ### 레벨도 분할
            if len(current_text) > max_chunk and current_text.strip():
                chunks.append({
                    "text": current_text.strip(),
                    "source": source,
                    "category": category,
                    "section": current_section,
                })
                current_text = ""
            current_text += line + "\n"
        else:
            current_text += line + "\n"

    if current_text.strip():
        chunks.append({
            "text": current_text.strip(),
            "source": source,
            "category": category,
            "section": current_section,
        })

    return chunks


async def load_knowledge(milvus_uri: str = "", dim: int = 1024, rebuild: bool = False) -> int:
    """knowledge/ 디렉토리의 모든 마크다운을 임베딩 → Milvus 저장.

    Args:
        milvus_uri: Milvus 서버 URI
        dim: 임베딩 차원
        rebuild: True면 기존 컬렉션 삭제 후 재구축

    Returns: 총 저장된 청크 수
    """
    client = init_store(uri=milvus_uri, dim=dim)

    if rebuild:
        drop_collection()
        init_store(uri=milvus_uri, dim=dim)

    all_chunks: list[dict[str, Any]] = []

    for filename in sorted(os.listdir(KNOWLEDGE_DIR)):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(KNOWLEDGE_DIR, filename)
        with open(filepath, encoding="utf-8") as f:
            text = f.read()

        category = FILE_CATEGORIES.get(filename, "general")
        chunks = chunk_markdown(text, source=filename, category=category)
        all_chunks.extend(chunks)
        logger.info("Loaded %s: %d chunks", filename, len(chunks))

    if not all_chunks:
        logger.warning("No knowledge chunks found")
        return 0

    # 배치 임베딩 (한번에 최대 32개씩)
    batch_size = 32
    total = 0
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        embeddings = await embed_texts(texts)
        inserted = insert_chunks(batch, embeddings)
        total += inserted

    logger.info("Total %d knowledge chunks loaded into Milvus", total)
    return total
