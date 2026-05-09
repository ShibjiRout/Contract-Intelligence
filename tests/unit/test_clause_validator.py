"""Unit tests for ExtractedClause Pydantic model and validate_clause()."""
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

from uuid import uuid4

import pytest

from contracts_platform.pipeline.clause_extraction.validator import (
    ExtractedClause,
    validate_clause,
)


def make_valid_clause(**overrides) -> dict:
    """Return a valid raw clause dict, with optional field overrides."""
    base = {
        "clause_id": str(uuid4()),
        "clause_type": "CONFIDENTIALITY",
        "raw_text": "Both parties agree to keep all information confidential.",
        "start_page": 1,
        "end_page": 2,
        "parties_mentioned": ["Party A", "Party B"],
        "key_dates": ["2025-01-01"],
        "key_obligations": ["Maintain confidentiality"],
        "risk_indicators": ["broad scope"],
        "confidence": 0.85,
    }
    base.update(overrides)
    return base


def test_valid_clause_dict():
    """All required fields present and valid → returns ExtractedClause."""
    raw = make_valid_clause()
    result = validate_clause(raw)
    assert result is not None
    assert isinstance(result, ExtractedClause)
    assert result.clause_type.value == "CONFIDENTIALITY"
    assert result.confidence == 0.85


def test_missing_clause_id():
    """clause_id absent → validate_clause returns None (doesn't raise)."""
    raw = make_valid_clause()
    del raw["clause_id"]
    result = validate_clause(raw)
    assert result is None


def test_invalid_clause_type():
    """clause_type not in ClauseType enum → returns None."""
    raw = make_valid_clause(clause_type="INVALID_TYPE")
    result = validate_clause(raw)
    assert result is None


def test_confidence_out_of_range():
    """confidence=1.5 → returns None."""
    raw = make_valid_clause(confidence=1.5)
    result = validate_clause(raw)
    assert result is None


def test_confidence_boundary_zero():
    """confidence=0.0 is valid."""
    raw = make_valid_clause(confidence=0.0)
    result = validate_clause(raw)
    assert result is not None
    assert result.confidence == 0.0


def test_confidence_boundary_one():
    """confidence=1.0 is valid."""
    raw = make_valid_clause(confidence=1.0)
    result = validate_clause(raw)
    assert result is not None
    assert result.confidence == 1.0


def test_empty_raw_text():
    """raw_text='' is still valid (no min_length constraint on raw_text)."""
    raw = make_valid_clause(raw_text="")
    result = validate_clause(raw)
    assert result is not None
    assert result.raw_text == ""


def test_invalid_key_dates():
    """key_dates contains non-date string → returns None."""
    raw = make_valid_clause(key_dates=["not-a-date"])
    result = validate_clause(raw)
    assert result is None


def test_valid_key_dates_empty():
    """key_dates as empty list → valid."""
    raw = make_valid_clause(key_dates=[])
    result = validate_clause(raw)
    assert result is not None
    assert result.key_dates == []


def test_multiple_valid_clause_types():
    """Other valid ClauseType values should also pass."""
    for clause_type in ["INDEMNITY", "LIABILITY", "TERMINATION", "GOVERNING_LAW"]:
        raw = make_valid_clause(clause_type=clause_type)
        result = validate_clause(raw)
        assert result is not None, f"Expected valid clause for type {clause_type}"
