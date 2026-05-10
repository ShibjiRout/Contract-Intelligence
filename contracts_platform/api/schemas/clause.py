from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class ClauseResponse(BaseModel):
    clause_id: str
    clause_type: str
    raw_text: str
    start_page: int
    end_page: int
    status: str | None = None                      # approved / rejected / need_changes
    risk_category: str | None = None               # GREEN / AMBER / RED
    legal_intent: str | None = None                # LLM extracted intent
    gap_summary: str | None = None                 # gap vs Gold Standard
    violation_message: str | None = None           # PostgreSQL rule violation
    precedent: dict | None = None                  # {party, date, contract_id} from Neo4j
    ai_recommendation: str | None = None           # LLM written recommendation
    lawyer_recommendation: str | None = None       # Lawyer's own note (need_changes only)
    lawyer_mail_id: str | None = None              # Lawyer email (need_changes only)
    reviewed_by: str | None = None                 # Lawyer user_id
    confidence: float = 0.0
    parties_mentioned: list[str] = []
    tenant_id: str | None = None


class ClauseModifyRequest(BaseModel):
    lawyer_recommendation: str = Field(min_length=10)
    lawyer_mail_id: EmailStr
    accept_ai_recommendation: bool = False         # True = lawyer accepts AI suggestion as-is


class ClauseAddRequest(BaseModel):
    contract_id: str
    clause_type: str
    raw_text: str = Field(min_length=10)


class RecommendationResponse(BaseModel):
    clause_id: str
    ai_recommendation: str
    legal_intent: str
    gap_summary: str
    violation_message: str | None
    precedent: dict | None
