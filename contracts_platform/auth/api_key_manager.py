from __future__ import annotations

import secrets

from motor.motor_asyncio import AsyncIOMotorDatabase


def generate_api_key() -> str:
    """Generate a 32-byte hex API key."""
    return secrets.token_hex(32)


async def validate_api_key(db: AsyncIOMotorDatabase, api_key: str) -> dict | None:
    """Look up api_key in MongoDB 'api_keys' collection. Return key doc or None."""
    return await db["api_keys"].find_one({"api_key": api_key, "is_active": True}, {"_id": 0})
