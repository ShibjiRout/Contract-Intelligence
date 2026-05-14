from __future__ import annotations

from datetime import timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from contracts_platform.api.dependencies import get_current_user, get_db
from contracts_platform.api.schemas.auth import LoginRequest, TokenResponse
from contracts_platform.auth.oauth2 import authenticate_user
from contracts_platform.core.config import settings
from contracts_platform.core.exceptions import AuthenticationError
from contracts_platform.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = structlog.get_logger()


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db=Depends(get_db)):
    user = await authenticate_user(db, body.email, body.password)
    if user is None:
        raise AuthenticationError("Invalid email or password.")

    token_data = {
        "sub": user["user_id"],
        "email": user["email"],
        "role": user["role"],
        "tenant_id": user["tenant_id"],
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    _set_auth_cookies(response, access_token, refresh_token)
    logger.info("auth.login_success", user_id=user["user_id"])
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response):
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise AuthenticationError("Missing refresh_token cookie.")

    payload = decode_token(raw)
    if payload.get("type") != "refresh":
        raise AuthenticationError("Invalid token type for refresh.")

    token_data = {
        "sub": payload["sub"],
        "email": payload["email"],
        "role": payload["role"],
        "tenant_id": payload["tenant_id"],
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    _set_auth_cookies(response, access_token, refresh_token)
    logger.info("auth.token_refreshed", sub=payload["sub"])
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"detail": "Logged out successfully."}


@router.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    doc = await db["users"].find_one(
        {"user_id": current_user["sub"]}, {"_id": 0, "hashed_password": 0}
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return doc
