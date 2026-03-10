"""FAB 이상감지 시스템 — 진입점."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from config import settings
from db.oracle import init_pool, close_pool
from detection.scheduler import run_detection_cycle

# Ensure tools are imported so @registry.tool decorators run
import agent.tools.logistics  # noqa: F401
import agent.tools.wip  # noqa: F401
import agent.tools.equipment  # noqa: F401

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("FAB 이상감지 시스템 starting up...")
    await init_pool()

    # RAG 지식베이스 초기화 (lazy import)
    if settings.rag.enabled:
        try:
            from rag.store import init_store
            from rag.loader import load_knowledge
            init_store(uri=settings.rag.milvus_uri, dim=settings.rag.embedding_dim)
            count = await load_knowledge(
                milvus_uri=settings.rag.milvus_uri,
                dim=settings.rag.embedding_dim,
            )
            logger.info("RAG knowledge loaded: %d chunks", count)
        except Exception:
            logger.exception("RAG initialization failed, continuing without RAG")
            settings.rag.enabled = False

    # 스케줄러 설정 — 이상감지 사이클만
    interval = settings.scheduler.detection_interval_sec
    scheduler.add_job(
        run_detection_cycle,
        "interval",
        seconds=interval,
        id="detection_cycle",
        name="Detection Cycle",
    )
    scheduler.start()
    logger.info("Scheduler started (detection every %ds)", interval)

    # ── 추후 확장 ──
    # RCA(근본원인분석): agent/rca_agent.py 참고
    #   - DB 폴링 방식으로 anomalies 테이블의 이상을 가져와 분석
    #   - scheduler.add_job(poll_and_analyze, "interval", seconds=30)
    # 상관분석: correlation/engine.py 참고
    # 에스컬레이션: alert/escalation.py 참고

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    await close_pool()
    logger.info("FAB 이상감지 시스템 shut down")


app = FastAPI(
    title="FAB 이상감지",
    description="반도체 공정 AI 이상감지 시스템",
    version="3.0.0",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# API 라우터 등록
from api.rules import router as rules_router
from api.anomalies import router as anomalies_router
from api.dashboard import router as dashboard_router
from api.system import router as system_router

app.include_router(rules_router)
app.include_router(anomalies_router)
app.include_router(dashboard_router)
app.include_router(system_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
