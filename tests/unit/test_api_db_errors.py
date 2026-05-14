import os
import sys
import types

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

api_key_manager = types.ModuleType("contracts_platform.auth.api_key_manager")


async def _validate_api_key(db, api_key):
    return None


api_key_manager.validate_api_key = _validate_api_key
sys.modules.setdefault("contracts_platform.auth.api_key_manager", api_key_manager)

from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from contracts_platform.api.dependencies import get_db
from contracts_platform.api.middleware.rate_limit_middleware import RateLimitMiddleware
from contracts_platform.api.main import app


class _FailingCollection:
    async def find_one(self, *args, **kwargs):
        raise ServerSelectionTimeoutError("tls handshake failed")


class _FailingDatabase:
    def __getitem__(self, name: str):
        return _FailingCollection()


def test_login_returns_503_when_mongodb_is_unavailable():
    async def override_get_db():
        return _FailingDatabase()

    app.dependency_overrides[get_db] = override_get_db
    original_is_limited = RateLimitMiddleware._is_limited
    RateLimitMiddleware._is_limited = lambda self, key, limit: False
    try:
        with TestClient(app) as client:
            response = client.post(
                "/auth/login",
                json={"email": "lawyer@test.com", "password": "testpass"},
            )
    finally:
        RateLimitMiddleware._is_limited = original_is_limited
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "type": "https://errors.contracts-platform.io/database-unavailable",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "Database temporarily unavailable.",
    }
