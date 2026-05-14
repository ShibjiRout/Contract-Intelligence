import os

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

import certifi
import pytest

from contracts_platform.db.mongodb import client as mongodb_client

TEST_MONGODB_SRV_URL = "mongodb+srv://user:pass@cluster.mongodb.net/?appName=test-app"


class _FakeClient:
    def __init__(self, url: str, **kwargs):
        self.url = url
        self.kwargs = kwargs
        self.closed = False

    def __getitem__(self, name: str):
        return {"name": name, "kwargs": self.kwargs}

    def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_get_database_uses_certifi_for_srv_connections(monkeypatch):
    created_clients: list[_FakeClient] = []

    def fake_client_factory(url: str, **kwargs):
        client = _FakeClient(url, **kwargs)
        created_clients.append(client)
        return client

    monkeypatch.setattr(mongodb_client, "AsyncIOMotorClient", fake_client_factory)
    monkeypatch.setattr(mongodb_client.settings, "MONGODB_URL", TEST_MONGODB_SRV_URL)
    monkeypatch.setattr(mongodb_client.settings, "MONGODB_DB_NAME", "contract_platform")
    mongodb_client._client = None
    mongodb_client._client_loop = None

    database = await mongodb_client.get_database()

    assert created_clients
    assert created_clients[0].kwargs["tlsCAFile"] == certifi.where()
    assert database["name"] == "contract_platform"
