from datetime import datetime
from typing import TypedDict

from contracts_platform.core.constants import ContractStatus, RiskLevel


class ErrorEntry(TypedDict):
    stage: str
    message: str
    timestamp: str


class ContractDocument(TypedDict):
    contract_id: str
    user_id: str
    tenant_id: str
    file_name: str
    file_path: str
    file_hash: str
    status: str
    current_stage: str
    errors: list[ErrorEntry]
    final_risk: str
    jurisdiction: str
    ocr_confidence: float
    clause_count: int
    missing_clauses: list[str]
    created_at: datetime
    updated_at: datetime


class AuditDocument(TypedDict):
    contract_id: str
    summary: dict
    created_at: datetime


class CostTrackingDocument(TypedDict):
    contract_id: str
    task_name: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    timestamp: datetime
