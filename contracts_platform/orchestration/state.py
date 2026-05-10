from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class ContractReviewState(TypedDict):
    # Input — set before graph runs
    contract_id: str
    clause_id: str
    clause_type: str
    clause_text: str
    jurisdiction: str
    tenant_id: str

    # Step 1 — intent_extraction_node
    legal_intent: str | None

    # Step 2 — gap_analysis_node
    gap_summary: str | None

    # Step 3 — precedent_check_node
    precedent: dict | None          # {party, date, contract_id} or None

    # Step 4 — playbook_score_node
    risk_category: str              # GREEN / AMBER / RED
    violation_message: str | None

    # Step 5 — recommendation_node
    ai_recommendation: str | None

    # Error tracking
    failed_sources: list[str]
    messages: Annotated[list, add_messages]
