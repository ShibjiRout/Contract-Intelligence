from __future__ import annotations

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from contracts_platform.db.mongodb.client import get_database


async def get_db() -> AsyncIOMotorDatabase:
    return await get_database()


def get_current_user(request: Request) -> dict:
    from contracts_platform.auth.jwt_handler import get_current_user as _get

    return _get(request)
