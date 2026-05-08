from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contracts_platform.db.postgresql.models import Jurisdiction


async def get_all_jurisdictions(session: AsyncSession) -> list[dict]:
    """Return all active jurisdictions."""
    result = await session.execute(
        select(Jurisdiction).where(Jurisdiction.is_active.is_(True))
    )
    rows = result.scalars().all()
    return [{"id": r.id, "code": r.code, "name": r.name, "is_active": r.is_active} for r in rows]


async def get_jurisdiction(session: AsyncSession, code: str) -> dict | None:
    """Return a single jurisdiction by its code, or None."""
    result = await session.execute(
        select(Jurisdiction).where(Jurisdiction.code == code)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return {"id": row.id, "code": row.code, "name": row.name, "is_active": row.is_active}
