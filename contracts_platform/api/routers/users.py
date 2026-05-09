from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException

from contracts_platform.api.dependencies import get_db
from contracts_platform.api.schemas.user import UserCreateRequest, UserUpdateRequest
from contracts_platform.auth.rbac import require_role
from contracts_platform.core.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])
logger = structlog.get_logger()


@router.get("/", dependencies=[Depends(require_role("admin"))])
async def list_users(db=Depends(get_db)):
    cursor = db["users"].find({}, {"_id": 0, "hashed_password": 0})
    users = await cursor.to_list(length=200)
    return users


@router.post("/", dependencies=[Depends(require_role("admin"))], status_code=201)
async def create_user(body: UserCreateRequest, db=Depends(get_db)):
    existing = await db["users"].find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=409, detail="A user with that email already exists.")

    now = datetime.now(timezone.utc)
    user_doc = {
        "user_id": str(uuid4()),
        "email": body.email,
        "hashed_password": hash_password(body.password),
        "role": body.role,
        "tenant_id": body.tenant_id,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    await db["users"].insert_one(user_doc)
    logger.info("users.created", user_id=user_doc["user_id"], email=body.email)

    # Return doc without sensitive fields
    user_doc.pop("_id", None)
    user_doc.pop("hashed_password", None)
    return user_doc


@router.patch("/{user_id}", dependencies=[Depends(require_role("admin"))])
async def update_user(user_id: str, body: UserUpdateRequest, db=Depends(get_db)):
    updates: dict = {"updated_at": datetime.now(timezone.utc)}
    if body.role is not None:
        updates["role"] = body.role
    if body.is_active is not None:
        updates["is_active"] = body.is_active

    result = await db["users"].update_one({"user_id": user_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")

    logger.info("users.updated", user_id=user_id)
    return {"user_id": user_id, "updated": True}
