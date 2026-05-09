from __future__ import annotations

from pydantic import BaseModel, Field


class ClauseResponse(BaseModel):
    clause_id: str
    clause_type: str
    raw_text: str
    start_page: int
    end_page: int
    risk_level: str | None
    recommendation: str | None
    suggested_fix: str | None
    confidence: float


class ClauseModifyRequest(BaseModel):
    modified_text: str = Field(min_length=10)


class RecommendationResponse(BaseModel):
    clause_id: str
    recommendation: str
    suggested_fix: str
    alternative_fixes: list[str]
