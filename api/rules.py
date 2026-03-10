"""규칙 CRUD + 테스트 API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from db import queries
from db.oracle import execute
from rules.models import RuleCreate, RuleUpdate

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("")
async def list_rules():
    return await queries.get_active_rules()


@router.get("/{rule_id}")
async def get_rule(rule_id: int):
    rule = await queries.get_rule(rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    return rule


@router.post("", status_code=201)
async def create_rule(body: RuleCreate):
    data = body.model_dump(exclude_none=True)
    if "llm_enabled" in data:
        data["llm_enabled"] = 1 if data["llm_enabled"] else 0
    if "enabled" in data:
        data["enabled"] = 1 if data["enabled"] else 0
    rule_id = await queries.create_rule(data)
    return {"rule_id": rule_id}


@router.patch("/{rule_id}")
async def update_rule(rule_id: int, body: RuleUpdate):
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(400, "No fields to update")
    if "llm_enabled" in data:
        data["llm_enabled"] = 1 if data["llm_enabled"] else 0
    if "enabled" in data:
        data["enabled"] = 1 if data["enabled"] else 0
    updated = await queries.update_rule(rule_id, data)
    if not updated:
        raise HTTPException(404, "Rule not found")
    return {"updated": updated}


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int):
    deleted = await queries.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(404, "Rule not found")
    return {"deleted": deleted}


@router.post("/{rule_id}/test")
async def test_rule(rule_id: int):
    """규칙 SQL만 실행해서 결과 확인 (이상 생성 안 함)."""
    rule = await queries.get_rule(rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")

    sql = rule.get("query_template", "")
    if not sql:
        raise HTTPException(400, "Rule has no query_template")

    try:
        rows = await execute(sql)
        return {
            "rule_id": rule_id,
            "rule_name": rule["rule_name"],
            "row_count": len(rows),
            "rows": rows[:50],
        }
    except Exception as e:
        raise HTTPException(400, f"Query error: {e}")
