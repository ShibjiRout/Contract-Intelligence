"""
Run once to create the admin user in MongoDB.
Usage: python scripts/seed_admin_user.py
"""
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()


async def seed():
    from contracts_platform.core.security import hash_password
    from contracts_platform.db.mongodb.client import get_database

    db = await get_database()

    email = "admin@contractplatform.com"
    password = "Admin@1234"

    existing = await db["users"].find_one({"email": email})
    if existing:
        print(f"Admin user already exists: {email}")
        return

    now = datetime.now(timezone.utc)
    user_doc = {
        "user_id": str(uuid4()),
        "email": email,
        "hashed_password": hash_password(password),
        "role": "admin",
        "tenant_id": "tenant-001",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    await db["users"].insert_one(user_doc)
    print(f"Admin user created successfully!")
    print(f"  Email:    {email}")
    print(f"  Password: {password}")
    print(f"  Role:     admin")


asyncio.run(seed())
