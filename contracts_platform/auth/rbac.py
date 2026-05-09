from __future__ import annotations

from fastapi import Depends, Request

from contracts_platform.auth.jwt_handler import get_current_user
from contracts_platform.core.exceptions import AuthorizationError


def require_role(*roles: str):
    """
    Returns a FastAPI dependency that checks the current user's role.
    Raises AuthorizationError if the role is not among the allowed roles.

    Usage: Depends(require_role('senior_lawyer', 'admin'))
    """

    def dependency(request: Request) -> dict:
        user = get_current_user(request)
        if user.get("role") not in roles:
            raise AuthorizationError(
                f"Role '{user.get('role')}' is not permitted. Required: {list(roles)}"
            )
        return user

    return dependency
