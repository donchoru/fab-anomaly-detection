"""FAB 이상감지 API 클라이언트 — async httpx."""

from __future__ import annotations

import os

import httpx

BASE_URL = os.getenv("API_URL", "http://localhost:8600")
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(base_url=BASE_URL, timeout=10.0)
    return _client


async def _get(path: str, params: dict | None = None) -> dict | list:
    r = await get_client().get(path, params=params)
    r.raise_for_status()
    return r.json()


async def _post(path: str, json: dict | None = None, params: dict | None = None) -> dict:
    r = await get_client().post(path, json=json, params=params)
    r.raise_for_status()
    return r.json()


async def _patch(path: str, json: dict | None = None) -> dict:
    r = await get_client().patch(path, json=json)
    r.raise_for_status()
    return r.json()


async def _delete(path: str) -> dict:
    r = await get_client().delete(path)
    r.raise_for_status()
    return r.json()


# ── 대시보드 ──

async def get_overview() -> dict:
    return await _get("/api/dashboard/overview")


async def get_stats() -> dict:
    return await _get("/api/stats")


async def get_health() -> dict:
    return await _get("/health")


# ── 차트 ──

async def get_timeline(hours: int = 24) -> dict:
    return await _get("/api/dashboard/timeline", {"hours": hours})


async def get_heatmap() -> dict:
    return await _get("/api/dashboard/heatmap")


# ── 이상 ──

async def get_anomalies(status: str | None = None, limit: int = 100) -> list:
    params: dict = {"limit": limit}
    if status:
        params["status"] = status
    return await _get("/api/anomalies", params)


async def get_active_anomalies() -> list:
    return await _get("/api/anomalies/active")


async def update_anomaly_status(anomaly_id: int, status: str, resolved_by: str = "") -> dict:
    body = {"status": status}
    if resolved_by:
        body["resolved_by"] = resolved_by
    return await _patch(f"/api/anomalies/{anomaly_id}/status", body)


# ── 규칙 ──

async def get_rules(include_disabled: bool = False) -> list:
    params = {}
    if include_disabled:
        params["include_disabled"] = "true"
    return await _get("/api/rules", params=params or None)


async def create_rule(data: dict) -> dict:
    return await _post("/api/rules", json=data)


async def update_rule(rule_id: int, data: dict) -> dict:
    return await _patch(f"/api/rules/{rule_id}", data)


async def delete_rule(rule_id: int) -> dict:
    return await _delete(f"/api/rules/{rule_id}")


async def test_rule(rule_id: int) -> dict:
    return await _post(f"/api/rules/{rule_id}/test")


async def get_tool_catalog() -> dict:
    return await _get("/api/rules/tools/catalog")


# ── RCA ──

async def get_rca(anomaly_id: int) -> dict | None:
    try:
        return await _get(f"/api/rca/{anomaly_id}")
    except Exception:
        return None


async def get_rca_list(status: str | None = None, limit: int = 50) -> list:
    params: dict = {"limit": limit}
    if status:
        params["status"] = status
    return await _get("/api/rca", params)


# ── 사용자 ──

async def get_users() -> list:
    return await _get("/api/users")


async def create_user(data: dict) -> dict:
    return await _post("/api/users", json=data)


async def update_user(user_id: int, data: dict) -> dict:
    return await _patch(f"/api/users/{user_id}", data)


async def delete_user(user_id: int) -> dict:
    return await _delete(f"/api/users/{user_id}")


async def login(username: str, password: str) -> dict:
    return await _post("/api/users/login", json={"username": username, "password": password})


async def register(username: str, password: str, display_name: str = "") -> dict:
    return await _post("/api/users/register", json={
        "username": username,
        "password": password,
        "display_name": display_name or username,
    })


# ── 수동 트리거 ──

async def trigger_detection() -> dict:
    return await _post("/api/detect/trigger")
