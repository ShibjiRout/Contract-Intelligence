from datetime import datetime, timezone

from contracts_platform.core.logging import logger
from contracts_platform.db.mongodb.client import get_database


async def record_llm_call(
    contract_id: str,
    task_name: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
) -> None:
    """Insert an LLM cost record into MongoDB cost_tracking collection."""
    db = await get_database()
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
        "cost_tracker.recorded",
        contract_id=contract_id,
        task_name=task_name,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
    )
