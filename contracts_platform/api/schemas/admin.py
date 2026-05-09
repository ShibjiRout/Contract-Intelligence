from pydantic import BaseModel, Field


class PlaybookRuleCreate(BaseModel):
    clause_type: str
    jurisdiction: str
    rule_type: str = Field(pattern="^(REQUIRED|FORBIDDEN|CONDITIONAL)$")
    description: str = Field(min_length=10)
    weight: float = Field(default=1.0, ge=0.0, le=10.0)


class PlaybookRuleUpdate(BaseModel):
    description: str | None = None
    weight: float | None = Field(default=None, ge=0.0, le=10.0)
    is_active: bool | None = None


class PlaybookRuleResponse(BaseModel):
    id: int
    clause_type: str
    jurisdiction: str
    rule_type: str
    description: str
    weight: float
    is_active: bool
