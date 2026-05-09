from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class ContractReviewState(TypedDict):
    contract_id: str
    clause_id: str
    clause_type: str
    clause_text: str
    jurisdiction: str
    tenant_id: str
    # Node outputs (None until that node runs)
    playbook_result: dict | None
    vector_result: dict | None
    graph_result: dict | None
    # Aggregated
    risk_level: str  # GREEN / AMBER / RED
    risk_score: float  # 0.0 - 1.0
    degraded_mode: bool
    failed_sources: list[str]
    missing_clauses: list[str]
    # Recommendation
    recommendation: str | None
    suggested_fix: str | None
    # Explainability
    explanation: dict | None
    messages: Annotated[list, add_messages]
