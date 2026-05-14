from __future__ import annotations

import asyncio
from http import HTTPStatus

import structlog
from fastapi import FastAPI, Request, WebSocket
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from contracts_platform.api.middleware.logging_middleware import LoggingMiddleware
from contracts_platform.api.middleware.rate_limit_middleware import RateLimitMiddleware
from contracts_platform.api.routers import admin, auth, clauses, contracts, users, webhooks
from contracts_platform.core.config import settings
from contracts_platform.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ContractPlatformError,
    DuplicateContractError,
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


@app.exception_handler(DuplicateContractError)
async def duplicate_contract_error_handler(
    request: Request, exc: DuplicateContractError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "type": "https://errors.contracts-platform.io/duplicate-contract",
            "title": "Duplicate Contract",
            "status": 409,
            "detail": exc.message,
            "existing_contract_id": exc.existing_contract_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://errors.contracts-platform.io/validation-error",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request validation failed.",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    try:
        title = HTTPStatus(exc.status_code).phrase
    except ValueError:
        title = "HTTP Error"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "https://errors.contracts-platform.io/http-error",
            "title": title,
            "status": exc.status_code,
            "detail": exc.detail,
        },
    )


@app.exception_handler(PyMongoError)
async def pymongo_exception_handler(request: Request, exc: PyMongoError) -> JSONResponse:
    logger.error("database_request_failed", exc_info=exc, path=request.url.path)
    return JSONResponse(
        status_code=503,
        content={
            "type": "https://errors.contracts-platform.io/database-unavailable",
            "title": "Service Unavailable",
            "status": 503,
            "detail": "Database temporarily unavailable.",
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", exc_info=exc, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "type": "https://errors.contracts-platform.io/internal-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred.",
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(admin.router)
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
