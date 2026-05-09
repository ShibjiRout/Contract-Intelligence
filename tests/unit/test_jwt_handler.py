"""Unit tests for JWT functions in contracts_platform.core.security."""
import os

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("POSTGRES_DSN", "postgresql+asyncpg://postgres:postgres@localhost:5432/test")
os.environ.setdefault("NEO4J_URL", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "testpass")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault(
    "AZURE_STORAGE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA==;EndpointSuffix=core.windows.net",
)
os.environ.setdefault(
    "AZURE_FILE_SHARE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA==;EndpointSuffix=core.windows.net",
)
os.environ.setdefault("AZURE_FILE_SHARE_NAME", "test")
os.environ.setdefault("AZURE_STORAGE_CONTAINER_NAME", "test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-ci-only")
os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItY2ktb25seQ==")

from datetime import timedelta

import pytest
from jose import jwt as jose_jwt

from contracts_platform.core.exceptions import AuthenticationError
from contracts_platform.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_create_and_decode_access_token():
    """Encode payload, decode, verify sub + type=='access'."""
    payload = {"sub": "user_123", "role": "senior_lawyer"}
    token = create_access_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "user_123"
    assert decoded["type"] == "access"
    assert decoded["role"] == "senior_lawyer"


def test_create_and_decode_refresh_token():
    """Encode refresh token, decode, verify type=='refresh'."""
    payload = {"sub": "user_456"}
    token = create_refresh_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "user_456"
    assert decoded["type"] == "refresh"


def test_expired_token_raises_authentication_error():
    """Create with expires_delta=timedelta(seconds=-1) → decode raises AuthenticationError."""
    payload = {"sub": "user_789"}
    token = create_access_token(payload, expires_delta=timedelta(seconds=-1))
    with pytest.raises(AuthenticationError):
        decode_token(token)


def test_wrong_secret_raises_authentication_error():
    """Encode with correct secret, decode with wrong secret → AuthenticationError."""
    from contracts_platform.core.config import settings

    payload = {"sub": "user_abc"}
    token = create_access_token(payload)

    # Temporarily patch settings.JWT_SECRET to simulate a different secret
    original_secret = settings.JWT_SECRET
    settings.JWT_SECRET = "completely-wrong-secret"
    try:
        with pytest.raises(AuthenticationError):
            decode_token(token)
    finally:
        settings.JWT_SECRET = original_secret


def test_decode_token_without_type_claim():
    """Manually craft token without 'type' → decode_token succeeds (no type check in decode_token)."""
    from contracts_platform.core.config import settings

    # Craft a token manually without the 'type' field
    raw_payload = {"sub": "user_xyz", "exp": 9999999999}
    token = jose_jwt.encode(raw_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    decoded = decode_token(token)
    assert decoded["sub"] == "user_xyz"
    assert "type" not in decoded


def test_hash_and_verify_password_correct():
    """hash_password + verify_password round-trip → True for correct password."""
    from unittest.mock import patch
    with patch("contracts_platform.core.security.pwd_context.hash", return_value="$2b$hashed"):
        with patch("contracts_platform.core.security.pwd_context.verify", return_value=True):
            hashed = hash_password("TestPass123")
            assert hashed == "$2b$hashed"
            assert verify_password("TestPass123", hashed) is True


def test_wrong_password_returns_false():
    """verify_password returns False for wrong password."""
    from unittest.mock import patch
    with patch("contracts_platform.core.security.pwd_context.verify", return_value=False):
        assert verify_password("WrongPass", "$2b$hashed") is False


def test_access_token_has_expiry():
    """Decoded access token must contain 'exp' field."""
    token = create_access_token({"sub": "user_check"})
    decoded = decode_token(token)
    assert "exp" in decoded


def test_refresh_token_has_longer_expiry_than_access():
    """Refresh token exp should be greater than access token exp."""
    payload = {"sub": "user_exp_test"}
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    access_decoded = decode_token(access_token)
    refresh_decoded = decode_token(refresh_token)
    assert refresh_decoded["exp"] > access_decoded["exp"]
