"""상관그룹 조회 API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from db import queries

router = APIRouter(prefix="/api/correlations", tags=["correlations"])


@router.get("")
async def list_correlations(limit: int = 50):
    return await queries.get_correlations(limit=limit)


@router.get("/{correlation_id}")
async def get_correlation(correlation_id: int):
    result = await queries.get_correlation_with_anomalies(correlation_id)
    if not result:
        raise HTTPException(404, "Correlation not found")
    return result
