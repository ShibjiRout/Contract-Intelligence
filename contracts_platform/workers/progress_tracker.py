import json
from datetime import datetime, timezone

import redis

from contracts_platform.core.config import settings

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def publish(contract_id: str, stage: str, percent: int, message: str = "") -> None:
    """Publish a progress event to the Redis channel for the given contract."""
    payload = json.dumps(
        {
            "contract_id": contract_id,
            "stage": stage,
            "percent": percent,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    _get_redis().publish(f"progress:{contract_id}", payload)
