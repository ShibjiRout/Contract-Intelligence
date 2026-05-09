"""Integration skeleton tests for MongoDB contract_repo (mocked — no real DB required)."""
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

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_create_and_get_contract(mock_db):
    """Verify create_contract inserts and returns the contract_id."""
    from contracts_platform.db.mongodb.repositories import contract_repo
    from contracts_platform.core.constants import ContractStatus

    mock_collection = AsyncMock()
    mock_collection.insert_one.return_value = AsyncMock(inserted_id="fake_object_id")
    mock_collection.find_one.return_value = {"contract_id": "c1", "status": "UPLOADED"}
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    doc = {"contract_id": "c1", "status": ContractStatus.UPLOADED.value}
    result_id = await contract_repo.create_contract(mock_db, doc)

    assert result_id == "c1"
    mock_collection.insert_one.assert_called_once_with(doc)


@pytest.mark.asyncio
async def test_update_status(mock_db):
    """Verify update_status calls update_one with correct contract_id filter."""
    from contracts_platform.db.mongodb.repositories import contract_repo
    from contracts_platform.core.constants import ContractStatus

    mock_collection = AsyncMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    await contract_repo.update_status(mock_db, "c1", ContractStatus.PROCESSING, "ocr")

    mock_collection.update_one.assert_called_once()
    call_args = mock_collection.update_one.call_args
    assert call_args[0][0] == {"contract_id": "c1"}


@pytest.mark.asyncio
async def test_update_status_sets_correct_values(mock_db):
    """Verify update_status sets status and current_stage in the $set payload."""
    from contracts_platform.db.mongodb.repositories import contract_repo
    from contracts_platform.core.constants import ContractStatus

    mock_collection = AsyncMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    await contract_repo.update_status(mock_db, "c2", ContractStatus.REVIEW_READY, "langgraph")

    call_args = mock_collection.update_one.call_args
    update_doc = call_args[0][1]
    assert update_doc["$set"]["status"] == "REVIEW_READY"
    assert update_doc["$set"]["current_stage"] == "langgraph"


@pytest.mark.asyncio
async def test_get_contract_not_found(mock_db):
    """Verify get_contract returns None when the document does not exist."""
    from contracts_platform.db.mongodb.repositories import contract_repo

    mock_collection = AsyncMock()
    mock_collection.find_one.return_value = None
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await contract_repo.get_contract(mock_db, "nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_get_by_file_hash_found(mock_db):
    """Verify get_by_file_hash returns the matching document."""
    from contracts_platform.db.mongodb.repositories import contract_repo

    mock_collection = AsyncMock()
    mock_collection.find_one.return_value = {"contract_id": "c3", "file_hash": "abc123"}
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await contract_repo.get_by_file_hash(mock_db, "abc123")
    assert result is not None
    assert result["contract_id"] == "c3"


@pytest.mark.asyncio
async def test_append_error_calls_update_one(mock_db):
    """Verify append_error calls update_one with $push on errors array."""
    from contracts_platform.db.mongodb.repositories import contract_repo

    mock_collection = AsyncMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    await contract_repo.append_error(mock_db, "c4", "ocr", "OCR service unavailable")

    mock_collection.update_one.assert_called_once()
    call_args = mock_collection.update_one.call_args
    assert call_args[0][0] == {"contract_id": "c4"}
    update_doc = call_args[0][1]
    assert "$push" in update_doc
    assert "errors" in update_doc["$push"]
