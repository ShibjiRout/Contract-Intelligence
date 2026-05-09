import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def sample_pdf_bytes():
    """Minimal valid PDF header bytes for testing."""
    return b"%PDF-1.4 fake content for testing"


@pytest.fixture
def sample_docx_bytes():
    """Minimal DOCX magic bytes."""
    # DOCX is a ZIP file starting with PK magic bytes
    return b"PK\x03\x04" + b"\x00" * 100


@pytest.fixture
def valid_jwt_payload():
    return {"sub": "user_123", "role": "senior_lawyer", "tenant_id": "tenant_abc"}


@pytest.fixture
def mock_db():
    """Mock AsyncIOMotorDatabase."""
    db = AsyncMock()
    db.__getitem__ = MagicMock(return_value=AsyncMock())
    return db
