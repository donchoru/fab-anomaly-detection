"""Oracle DB async connection pool (oracledb thin mode)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import oracledb

from config import settings

logger = logging.getLogger(__name__)

_pool: oracledb.AsyncConnectionPool | None = None


async def init_pool() -> None:
    global _pool
    cfg = settings.oracle
    _pool = oracledb.create_pool_async(
        user=cfg.user,
        password=cfg.password,
        dsn=cfg.dsn,
        min=cfg.min_pool,
        max=cfg.max_pool,
    )
    logger.info("Oracle pool created (min=%d, max=%d)", cfg.min_pool, cfg.max_pool)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close(force=True)
        _pool = None
        logger.info("Oracle pool closed")


@asynccontextmanager
async def get_connection() -> AsyncGenerator[oracledb.AsyncConnection, None]:
    if _pool is None:
        raise RuntimeError("Oracle pool not initialized. Call init_pool() first.")
    async with _pool.acquire() as conn:
        yield conn


async def execute(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute a SELECT query and return list of dicts."""
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params or {})
            columns = [col[0].lower() for col in cur.description] if cur.description else []
            rows = await cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]


async def execute_dml(sql: str, params: dict[str, Any] | None = None) -> int:
    """Execute INSERT/UPDATE/DELETE and return rowcount."""
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params or {})
            await conn.commit()
            return cur.rowcount


async def execute_returning(
    sql: str, params: dict[str, Any] | None = None, returning_col: str = "rule_id"
) -> Any:
    """Execute INSERT ... RETURNING id INTO :out_id."""
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            out_var = cur.var(oracledb.NUMBER)
            p = dict(params or {})
            p["out_id"] = out_var
            await cur.execute(sql, p)
            await conn.commit()
            return out_var.getvalue()[0]
