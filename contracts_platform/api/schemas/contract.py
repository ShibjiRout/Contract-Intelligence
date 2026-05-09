from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ContractUploadResponse(BaseModel):
    contract_id: str
    status: str
    message: str


class ContractDetailResponse(BaseModel):
    contract_id: str
    filename: str
    status: str
    current_stage: str | None
    final_risk: str | None
    created_at: datetime
    updated_at: datetime


class ContractStatusResponse(BaseModel):
    contract_id: str
    status: str
    current_stage: str | None
    progress_percent: int | None
    errors: list[dict]
