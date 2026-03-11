"""FAB 이상감지 시스템 — 진입점.

SQLite 모드: python main.py --sqlite simulator.db [--port 8600] [--interval 60]
Oracle 모드: python main.py
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys

# ── CLI 파싱 (DB 모드 결정을 위해 가장 먼저) ──

_parser = argparse.ArgumentParser(description="FAB 이상감지 시스템")
_parser.add_argument("--sqlite", type=str, metavar="DB_FILE", help="SQLite 모드 (DB 파일 경로)")
_parser.add_argument("--port", type=int, default=None, help="API 포트 (기본: 8600)")
_parser.add_argument("--interval", type=int, default=None, help="감지 주기 초 (기본: 300)")
_args = _parser.parse_args()

# ── SQLite monkey-patch (다른 모듈 import 전에 실행) ──

if _args.sqlite:
    if not os.path.exists(_args.sqlite):
        print(f"DB 파일 없음: {_args.sqlite}")
        print(f"먼저 실행: python init_db.py --db {_args.sqlite}")
        sys.exit(1)
    from simulator.sqlite_backend import init_sqlite
    init_sqlite(_args.sqlite)

    # macOS Keychain에서 LLM API 키 주입
    if not os.getenv("LLM_API_KEY"):
        try:
            key = subprocess.check_output(
                ["security", "find-generic-password", "-s", "GEMINI_API_KEY", "-w"],
                text=True,
            ).strip()
            os.environ["LLM_API_KEY"] = key
        except Exception:
            pass

# ── 나머지 import (monkey-patch 이후 안전) ──

from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db.oracle import init_pool, close_pool
from detection.scheduler import run_detection_cycle

# 도구 등록
import agent.tools.logistics  # noqa: F401
import agent.tools.wip  # noqa: F401
import agent.tools.equipment  # noqa: F401

# ── 설정 오버라이드 ──

if _args.port:
    settings.port = _args.port
if _args.interval:
    settings.scheduler.detection_interval_sec = _args.interval

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FAB 이상감지 시스템 starting up...")

    # DB 연결 (Oracle만 — SQLite는 이미 monkey-patch됨)
    if not _args.sqlite:
        await init_pool()

    # rules.yaml → DB 동기화 (Oracle만 — SQLite는 init_db.py에서 처리)
    if not _args.sqlite:
        from rules.loader import sync_to_db
        try:
            count = await sync_to_db()
            logger.info("Rules synced from YAML: %d", count)
        except Exception:
            logger.exception("Rule sync failed")

    # 스케줄러 — 이상감지 사이클
    interval = settings.scheduler.detection_interval_sec
    scheduler.add_job(
        run_detection_cycle,
        "interval",
        seconds=interval,
        id="detection_cycle",
        name="Detection Cycle",
    )
    scheduler.start()

    mode = f"SQLite ({_args.sqlite})" if _args.sqlite else "Oracle"
    logger.info("=" * 60)
    logger.info("FAB 이상감지 시스템 running")
    logger.info("  Mode: %s", mode)
    logger.info("  API: http://localhost:%d", settings.port)
    logger.info("  Detection interval: %d초", interval)
    logger.info("=" * 60)

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    if not _args.sqlite:
        await close_pool()
    logger.info("FAB 이상감지 시스템 shut down")


app = FastAPI(
    title="FAB 이상감지",
    description="반도체 공정 AI 이상감지 시스템",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# API 라우터
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
        app,
        host=settings.host,
        port=settings.port,
    )
