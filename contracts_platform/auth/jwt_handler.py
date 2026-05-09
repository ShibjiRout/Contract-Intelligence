from __future__ import annotations

from fastapi import Request

from contracts_platform.core.exceptions import AuthenticationError
from contracts_platform.core.security import decode_token


def get_token_from_cookie(request: Request) -> str:
    """Extract 'access_token' from cookies. Raise AuthenticationError if missing."""
    token = request.cookies.get("access_token")
    if not token:
        raise AuthenticationError("Missing access_token cookie.")
    return token


def get_current_user(request: Request) -> dict:
    """Extract and decode the access token from cookies. Return the payload dict."""
    token = get_token_from_cookie(request)
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type.")
    return payload
