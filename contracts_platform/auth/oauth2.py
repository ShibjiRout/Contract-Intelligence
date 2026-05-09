from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from contracts_platform.core.security import verify_password


async def authenticate_user(db: AsyncIOMotorDatabase, email: str, password: str) -> dict | None:
    """
    Find user document in MongoDB 'users' collection by email.
    Verify password with verify_password(). Return user doc or None.
    """
    user = await db["users"].find_one({"email": email}, {"_id": 0})
    if user is None:
        return None
    if not verify_password(password, user.get("hashed_password", "")):
        return None
    return user
