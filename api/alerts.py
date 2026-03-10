"""알림 라우팅 설정 + 이력 API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import queries

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class RouteCreate(BaseModel):
    category: str | None = None
    severity_min: str = "warning"
    channel: str
    recipient: str | None = None
    escalation_delay_min: int = 0
    enabled: bool = True


class RouteUpdate(BaseModel):
    category: str | None = None
    severity_min: str | None = None
    channel: str | None = None
    recipient: str | None = None
    escalation_delay_min: int | None = None
    enabled: bool | None = None


@router.get("/routes")
async def list_routes():
    return await queries.get_alert_routes(enabled_only=False)


@router.post("/routes", status_code=201)
async def create_route(body: RouteCreate):
    data = body.model_dump(exclude_none=True)
    if "enabled" in data:
        data["enabled"] = 1 if data["enabled"] else 0
    route_id = await queries.create_alert_route(data)
    return {"route_id": route_id}


@router.patch("/routes/{route_id}")
async def update_route(route_id: int, body: RouteUpdate):
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(400, "No fields to update")
    if "enabled" in data:
        data["enabled"] = 1 if data["enabled"] else 0
    updated = await queries.update_alert_route(route_id, data)
    if not updated:
        raise HTTPException(404, "Route not found")
    return {"updated": updated}


@router.get("/history")
async def alert_history(limit: int = 100):
    return await queries.get_alert_history(limit=limit)
