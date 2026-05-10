"""Unit tests for compute_file_hash() and check_duplicate()."""
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

import hashlib
from unittest.mock import AsyncMock, patch

import pytest

from contracts_platform.file_handling.duplicate_detector import (
    check_duplicate,
    compute_file_hash,
)

SAMPLE_BYTES = b"%PDF-1.4 some contract content"
OTHER_BYTES = b"%PDF-1.4 completely different contract"


def test_compute_hash_deterministic():
    """Same bytes always produce the same hash."""
    hash1 = compute_file_hash(SAMPLE_BYTES)
    hash2 = compute_file_hash(SAMPLE_BYTES)
    assert hash1 == hash2


def test_compute_hash_different():
    """Different bytes produce different hashes."""
    hash1 = compute_file_hash(SAMPLE_BYTES)
    hash2 = compute_file_hash(OTHER_BYTES)
    assert hash1 != hash2


def test_compute_hash_is_sha256():
    """Result is a 64-character hex string (SHA-256 digest)."""
    result = compute_file_hash(SAMPLE_BYTES)
    assert len(result) == 64
    # Verify it's all hex characters
    int(result, 16)  # raises ValueError if not valid hex


def test_compute_hash_matches_stdlib():
    """Hash output matches hashlib.sha256 directly."""
    expected = hashlib.sha256(SAMPLE_BYTES).hexdigest()
    assert compute_file_hash(SAMPLE_BYTES) == expected


@pytest.mark.asyncio
async def test_check_duplicate_found():
    """Mock contract_repo.get_by_file_hash returns doc → (True, contract_id)."""
    mock_db = AsyncMock()
    existing_doc = {"contract_id": "contract-abc-123"}

    with patch(
        "contracts_platform.file_handling.duplicate_detector.contract_repo"
    ) as mock_repo:
        mock_repo.get_by_file_hash = AsyncMock(return_value=existing_doc)
        is_dup, contract_id = await check_duplicate(mock_db, SAMPLE_BYTES)

    assert is_dup is True
    assert contract_id == "contract-abc-123"


@pytest.mark.asyncio
async def test_check_duplicate_not_found():
    """Mock contract_repo.get_by_file_hash returns None → (False, None)."""
    mock_db = AsyncMock()

    with patch(
        "contracts_platform.file_handling.duplicate_detector.contract_repo"
    ) as mock_repo:
        mock_repo.get_by_file_hash = AsyncMock(return_value=None)
        is_dup, contract_id = await check_duplicate(mock_db, SAMPLE_BYTES)

    assert is_dup is False
    assert contract_id is None


@pytest.mark.asyncio
async def test_check_duplicate_uses_correct_hash():
    """Verify the hash passed to get_by_file_hash matches compute_file_hash output."""
    mock_db = AsyncMock()
    expected_hash = compute_file_hash(SAMPLE_BYTES)
    captured_hash = None

    async def capture_hash(db, file_hash, tenant_id=None):
        nonlocal captured_hash
        captured_hash = file_hash
        return None

    with patch(
        "contracts_platform.file_handling.duplicate_detector.contract_repo"
    ) as mock_repo:
        mock_repo.get_by_file_hash = capture_hash
        await check_duplicate(mock_db, SAMPLE_BYTES)

    assert captured_hash == expected_hash


@pytest.mark.asyncio
async def test_check_duplicate_passes_tenant_id():
    """Verify duplicate lookup can be scoped to the current tenant."""
    mock_db = AsyncMock()
    captured_tenant_id = None

    async def capture_tenant(db, file_hash, tenant_id=None):
        nonlocal captured_tenant_id
        captured_tenant_id = tenant_id
        return None

    with patch(
        "contracts_platform.file_handling.duplicate_detector.contract_repo"
    ) as mock_repo:
        mock_repo.get_by_file_hash = capture_tenant
        await check_duplicate(mock_db, SAMPLE_BYTES, tenant_id="tenant_abc")

    assert captured_tenant_id == "tenant_abc"
