"""Milvus 벡터 저장소 — 전문지식 임베딩 + 검색."""

from __future__ import annotations

import logging
from typing import Any

from pymilvus import (
    MilvusClient,
    DataType,
    CollectionSchema,
    FieldSchema,
)

from config import settings

logger = logging.getLogger(__name__)

COLLECTION = "fab_knowledge"
DIM = 1024  # 임베딩 차원 (모델에 따라 조정)

_client: MilvusClient | None = None


def init_store(uri: str = "", dim: int = DIM) -> MilvusClient:
    """Milvus 연결 초기화."""
    global _client, DIM
    DIM = dim
    milvus_uri = uri or settings.rag.milvus_uri
    _client = MilvusClient(uri=milvus_uri)

    # 컬렉션 없으면 생성
    if not _client.has_collection(COLLECTION):
        _create_collection()
        logger.info("Collection '%s' created (dim=%d)", COLLECTION, DIM)
    else:
        logger.info("Collection '%s' exists", COLLECTION)

    return _client


def _create_collection() -> None:
    schema = CollectionSchema(fields=[
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=256),
    ])
    _client.create_collection(
        collection_name=COLLECTION,
        schema=schema,
    )
    # 인덱스 생성
    _client.create_index(
        collection_name=COLLECTION,
        field_name="embedding",
        index_params={"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 64}},
    )


def insert_chunks(chunks: list[dict[str, Any]], embeddings: list[list[float]]) -> int:
    """청크 + 임베딩을 Milvus에 삽입.

    chunks: [{"text": "...", "source": "equipment.md", "category": "equipment", "section": "알람 코드"}]
    embeddings: 각 청크의 임베딩 벡터
    """
    if not _client:
        raise RuntimeError("Store not initialized")

    data = []
    for chunk, emb in zip(chunks, embeddings):
        data.append({
            "embedding": emb,
            "text": chunk["text"],
            "source": chunk.get("source", ""),
            "category": chunk.get("category", ""),
            "section": chunk.get("section", ""),
        })

    result = _client.insert(collection_name=COLLECTION, data=data)
    logger.info("Inserted %d chunks into Milvus", len(data))
    return len(data)


def search(
    query_embedding: list[float],
    top_k: int = 5,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """벡터 유사도 검색.

    Returns: [{"text": "...", "source": "...", "category": "...", "score": 0.85}]
    """
    if not _client:
        raise RuntimeError("Store not initialized")

    filter_expr = f'category == "{category}"' if category else ""

    results = _client.search(
        collection_name=COLLECTION,
        data=[query_embedding],
        limit=top_k,
        output_fields=["text", "source", "category", "section"],
        filter=filter_expr if filter_expr else None,
    )

    hits = []
    for hit in results[0]:
        hits.append({
            "text": hit["entity"]["text"],
            "source": hit["entity"]["source"],
            "category": hit["entity"]["category"],
            "section": hit["entity"]["section"],
            "score": hit["distance"],
        })

    return hits


def drop_collection() -> None:
    """컬렉션 삭제 (재인덱싱용)."""
    if _client and _client.has_collection(COLLECTION):
        _client.drop_collection(COLLECTION)
        logger.info("Collection '%s' dropped", COLLECTION)
