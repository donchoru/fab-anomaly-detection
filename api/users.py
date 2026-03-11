"""사용자 관리 API."""

from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import queries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    role: str = "viewer"


class UserUpdate(BaseModel):
    password: str | None = None
    display_name: str | None = None
    role: str | None = None
    enabled: int | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


@router.get("")
async def list_users():
    users = await queries.get_all_users()
    for u in users:
        u.pop("password", None)
    return users


@router.post("", status_code=201)
async def create_user(body: UserCreate):
    existing = await queries.get_user_by_username(body.username)
    if existing:
        raise HTTPException(409, "Username already exists")
    data = {
        "username": body.username,
        "password": _hash_pw(body.password),
        "display_name": body.display_name or body.username,
        "role": body.role,
        "enabled": 1,
    }
    user_id = await queries.create_user(data)
    return {"user_id": user_id}


@router.patch("/{user_id}")
async def update_user(user_id: int, body: UserUpdate):
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(400, "No fields to update")
    if "password" in data:
        data["password"] = _hash_pw(data["password"])
    updated = await queries.update_user(user_id, data)
    if not updated:
        raise HTTPException(404, "User not found")
    return {"updated": updated}


@router.delete("/{user_id}")
async def delete_user(user_id: int):
    deleted = await queries.delete_user(user_id)
    if not deleted:
        raise HTTPException(404, "User not found")
    return {"deleted": deleted}


@router.post("/register", status_code=201)
async def register(body: UserCreate):
    """자가 회원가입 — 기본 viewer 역할."""
    existing = await queries.get_user_by_username(body.username)
    if existing:
        raise HTTPException(409, "이미 사용 중인 아이디입니다.")
    data = {
        "username": body.username,
        "password": _hash_pw(body.password),
        "display_name": body.display_name or body.username,
        "role": "viewer",
        "enabled": 1,
    }
    user_id = await queries.create_user(data)
    return {
        "user_id": user_id,
        "username": body.username,
        "display_name": data["display_name"],
        "role": "viewer",
    }


@router.post("/login")
async def login(body: LoginRequest):
    user = await queries.get_user_by_username(body.username)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    if not user.get("enabled", 1):
        raise HTTPException(403, "Account disabled")
    if user["password"] != _hash_pw(body.password):
        raise HTTPException(401, "Invalid credentials")
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "display_name": user.get("display_name", user["username"]),
        "role": user.get("role", "viewer"),
    }
