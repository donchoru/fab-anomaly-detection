"""이상 목록 + 상태 변경 + 노트 API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import queries
from lifecycle.manager import transition, InvalidTransitionError

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


class StatusUpdate(BaseModel):
    status: str
    resolved_by: str | None = None


class NoteAdd(BaseModel):
    note: str


@router.get("")
async def list_anomalies(status: str | None = None, limit: int = 100, offset: int = 0):
    return await queries.get_anomalies(status=status, limit=limit, offset=offset)


@router.get("/active")
async def active_anomalies():
    return await queries.get_active_anomalies()


@router.patch("/{anomaly_id}/status")
async def update_status(anomaly_id: int, body: StatusUpdate):
    try:
        new_status = await transition(anomaly_id, body.status, body.resolved_by)
        return {"anomaly_id": anomaly_id, "status": new_status}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except InvalidTransitionError as e:
        raise HTTPException(400, str(e))


@router.post("/{anomaly_id}/notes")
async def add_note(anomaly_id: int, body: NoteAdd):
    updated = await queries.add_anomaly_note(anomaly_id, body.note)
    if not updated:
        raise HTTPException(404, "Anomaly not found")
    return {"added": True}
