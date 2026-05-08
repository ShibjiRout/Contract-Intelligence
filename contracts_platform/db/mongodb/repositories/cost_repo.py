from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from contracts_platform.core.logging import logger


async def record_llm_call(
    db: AsyncIOMotorDatabase,
    contract_id: str,
    task_name: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
) -> None:
    """Record a single LLM API call cost entry."""
    doc = {
        "contract_id": contract_id,
        "task_name": task_name,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": cost_usd,
        "timestamp": datetime.now(timezone.utc),
    }
    await db["cost_tracking"].insert_one(doc)
    logger.info(
        "cost.recorded",
        contract_id=contract_id,
        task_name=task_name,
        cost_usd=cost_usd,
    )


async def get_cost_summary(
    db: AsyncIOMotorDatabase,
    contract_id: str,
) -> list[dict]:
    """Return all cost tracking entries for a contract."""
    cursor = db["cost_tracking"].find({"contract_id": contract_id}, {"_id": 0})
    return await cursor.to_list(length=None)
