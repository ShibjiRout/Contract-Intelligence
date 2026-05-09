from __future__ import annotations

import json

import redis.asyncio as aioredis
import structlog
from fastapi import WebSocket

from contracts_platform.core.config import settings

logger = structlog.get_logger()


class WebSocketManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, contract_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(contract_id, []).append(ws)
        logger.info("ws.connected", contract_id=contract_id)

    async def disconnect(self, contract_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(contract_id, [])
        if ws in conns:
            conns.remove(ws)
        logger.info("ws.disconnected", contract_id=contract_id)

    async def broadcast(self, contract_id: str, message: dict) -> None:
        for ws in list(self._connections.get(contract_id, [])):
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.warning("ws.send_failed", contract_id=contract_id, error=str(exc))
                await self.disconnect(contract_id, ws)

    async def listen_and_forward(self, contract_id: str) -> None:
        """Subscribe to Redis progress:{contract_id} channel and forward messages to WS clients."""
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"progress:{contract_id}")
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await self.broadcast(contract_id, data)
                except Exception as exc:
                    logger.error(
                        "ws.forward_failed", contract_id=contract_id, error=str(exc)
                    )


manager = WebSocketManager()
