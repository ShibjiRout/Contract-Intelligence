from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from contracts_platform.core.constants import ClauseType
from contracts_platform.core.logging import logger


class ExtractedClause(BaseModel):
    clause_id: UUID
    clause_type: ClauseType
    raw_text: str
    start_page: int
    end_page: int
    parties_mentioned: list[str]
    key_dates: list[date]
    key_obligations: list[str]
    risk_indicators: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


def validate_clause(raw: dict) -> "ExtractedClause | None":
    """Return a validated ExtractedClause or None on validation failure (logs the error)."""
    try:
        return ExtractedClause.model_validate(raw)
    except ValidationError as exc:
        logger.warning(
            "clause_validator.validation_failed",
            errors=exc.errors(),
            raw_keys=list(raw.keys()),
        )
        return None
