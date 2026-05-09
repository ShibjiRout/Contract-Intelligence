from __future__ import annotations

import asyncio

import structlog
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from contracts_platform.api.middleware.logging_middleware import LoggingMiddleware
from contracts_platform.api.middleware.rate_limit_middleware import RateLimitMiddleware
from contracts_platform.api.routers import auth, clauses, contracts, users, webhooks
from contracts_platform.core.config import settings
from contracts_platform.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ContractPlatformError,
)
from contracts_platform.core.logging import setup_logging
from contracts_platform.core.tracing import setup_tracing
from contracts_platform.notifications.websocket_manager import manager

setup_logging()
setup_tracing()

logger = structlog.get_logger()

app = FastAPI(title="Contract Intelligence Platform", version="0.1.0")

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)


# ---------------------------------------------------------------------------
# Exception handlers — RFC 7807 Problem Detail
# ---------------------------------------------------------------------------
@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "status": 401,
            "title": "Unauthorized",
            "detail": exc.message,
            "type": "about:blank",
        },
    )


@app.exception_handler(AuthorizationError)
async def authz_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "status": 403,
            "title": "Forbidden",
            "detail": exc.message,
            "type": "about:blank",
        },
    )


@app.exception_handler(ContractPlatformError)
async def platform_error_handler(
    request: Request, exc: ContractPlatformError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "status": 400,
            "title": "Bad Request",
            "detail": exc.message,
            "type": "about:blank",
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(contracts.router)
app.include_router(clauses.router)
app.include_router(users.router)
app.include_router(webhooks.router)


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------
@app.websocket("/ws/contracts/{contract_id}")
async def contract_ws(websocket: WebSocket, contract_id: str):
    await manager.connect(contract_id, websocket)
    asyncio.create_task(manager.listen_and_forward(contract_id))
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        await manager.disconnect(contract_id, websocket)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}
