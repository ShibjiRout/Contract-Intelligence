import json

import redis

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger


class RedisCheckpointer:
    """Simple Redis checkpoint store for LangGraph state persistence."""

    TTL = 86400  # 24 hours

    def __init__(self) -> None:
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    def save(self, thread_id: str, state: dict) -> None:
        key = f"checkpoint:{thread_id}"
        self._redis.setex(key, self.TTL, json.dumps(state, default=str))
        logger.info("checkpoint.saved", thread_id=thread_id, key=key)

    def load(self, thread_id: str) -> dict | None:
        key = f"checkpoint:{thread_id}"
        data = self._redis.get(key)
        if data:
            logger.info("checkpoint.loaded", thread_id=thread_id, key=key)
            return json.loads(data)
        logger.debug("checkpoint.miss", thread_id=thread_id, key=key)
        return None

    def delete(self, thread_id: str) -> None:
        key = f"checkpoint:{thread_id}"
        self._redis.delete(key)
        logger.info("checkpoint.deleted", thread_id=thread_id, key=key)
