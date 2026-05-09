from __future__ import annotations

import json
import time

import redis
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from contracts_platform.core.config import settings

logger = structlog.get_logger()

IP_LIMIT = 100        # requests per minute per IP
API_KEY_LIMIT = 1000  # requests per minute per API key
WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    def _is_limited(self, key: str, limit: int) -> bool:
        now = time.time()
        window_start = now - WINDOW_SECONDS
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, WINDOW_SECONDS)
        results = pipe.execute()
        count = int(results[2])
        return count > limit

    async def dispatch(self, request: Request, call_next) -> Response:
        api_key = request.headers.get("X-API-Key")

        if api_key:
            key = f"rate:apikey:{api_key}"
            if self._is_limited(key, API_KEY_LIMIT):
                logger.warning("rate_limit.exceeded", api_key=api_key[:8] + "...")
                return Response(
                    content=json.dumps(
                        {
                            "status": 429,
                            "title": "Too Many Requests",
                            "detail": "API key rate limit exceeded. Max 1000 requests per minute.",
                            "type": "about:blank",
                        }
                    ),
                    status_code=429,
                    media_type="application/json",
                )
        else:
            client_ip = request.client.host if request.client else "unknown"
            key = f"rate:ip:{client_ip}"
            if self._is_limited(key, IP_LIMIT):
                logger.warning("rate_limit.exceeded", client_ip=client_ip)
                return Response(
                    content=json.dumps(
                        {
                            "status": 429,
                            "title": "Too Many Requests",
                            "detail": "IP rate limit exceeded. Max 100 requests per minute.",
                            "type": "about:blank",
                        }
                    ),
                    status_code=429,
                    media_type="application/json",
                )

        return await call_next(request)
