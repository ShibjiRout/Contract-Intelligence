from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: str
    tenant_id: str


class UserUpdateRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None
