from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from contracts_platform.core.constants import ContractStatus
from contracts_platform.core.logging import logger
from contracts_platform.db.mongodb.client import get_database
from contracts_platform.db.mongodb.repositories import contract_repo
from contracts_platform.orchestration.nodes.intent_extraction_node import intent_extraction_node
from contracts_platform.orchestration.nodes.gap_analysis_node import gap_analysis_node
from contracts_platform.orchestration.nodes.precedent_check_node import precedent_check_node
from contracts_platform.orchestration.nodes.playbook_score_node import playbook_score_node
from contracts_platform.orchestration.nodes.recommendation_node import recommendation_node
from contracts_platform.orchestration.state import ContractReviewState


def build_graph() -> StateGraph:
    """
    Sequential LangGraph pipeline for a single risky clause:

    START
      → intent_extraction   (LLM: what is this clause trying to do?)
      → gap_analysis        (LLM + Qdrant: how does it differ from Gold Standard?)
      → precedent_check     (Neo4j: have we accepted this before? for who?)
      → playbook_score      (PostgreSQL: does it violate our rules? RED/AMBER?)
      → recommendation      (LLM: write the AI recommendation using all context)
      → END
    """
    graph = StateGraph(ContractReviewState)

    graph.add_node("intent_extraction", intent_extraction_node)
    graph.add_node("gap_analysis", gap_analysis_node)
    graph.add_node("precedent_check", precedent_check_node)
    graph.add_node("playbook_score", playbook_score_node)
    graph.add_node("recommendation", recommendation_node)

    graph.add_edge(START, "intent_extraction")
    graph.add_edge("intent_extraction", "gap_analysis")
    graph.add_edge("gap_analysis", "precedent_check")
    graph.add_edge("precedent_check", "playbook_score")
    graph.add_edge("playbook_score", "recommendation")
    graph.add_edge("recommendation", END)

    return graph


async def run_review_graph(contract_id: str, clause_id: str) -> dict:
    """
    Entry point called by review_orchestration_task for a single risky clause.
    Runs the full sequential pipeline and saves results back to MongoDB.
    After all risky clauses are processed, sets contract status to REVIEW_READY.
    """
    logger.info("langgraph.run", contract_id=contract_id, clause_id=clause_id)

    db = await get_database()

    clause = await db["clauses"].find_one({"clause_id": clause_id})
    contract = await db["contracts"].find_one({"contract_id": contract_id})

    if not clause or not contract:
        logger.error(
            "langgraph.clause_not_found",
            contract_id=contract_id,
            clause_id=clause_id,
        )
        return {}

    tenant_id: str = contract.get("tenant_id", "")
    jurisdiction: str = contract.get("jurisdiction", "UK")

    compiled_graph = build_graph().compile()

    state: ContractReviewState = {
        "contract_id": contract_id,
        "clause_id": clause_id,
        "clause_type": clause.get("clause_type", ""),
        "clause_text": clause.get("raw_text", ""),
        "jurisdiction": jurisdiction,
        "tenant_id": tenant_id,
        "legal_intent": None,
        "gap_summary": None,
        "precedent": None,
        "risk_category": "GREEN",
        "violation_message": None,
        "ai_recommendation": None,
        "failed_sources": [],
        "messages": [],
    }

    final_state = await compiled_graph.ainvoke(state)

    # Save all results back to MongoDB clause document
    await db["clauses"].update_one(
        {"clause_id": clause_id},
        {
            "$set": {
                "legal_intent": final_state.get("legal_intent"),
                "gap_summary": final_state.get("gap_summary"),
                "precedent": final_state.get("precedent"),
                "risk_category": final_state.get("risk_category", "GREEN"),
                "violation_message": final_state.get("violation_message"),
                "ai_recommendation": final_state.get("ai_recommendation"),
                "status": "ai_flagged",
            }
        },
    )

    logger.info(
        "langgraph.clause_processed",
        contract_id=contract_id,
        clause_id=clause_id,
        risk_category=final_state.get("risk_category"),
    )

    # Check if all risky clauses are now processed
    # A clause is "processed" if it has ai_recommendation set or status is approved
    total = await db["clauses"].count_documents({"contract_id": contract_id})
    processed = await db["clauses"].count_documents({
        "contract_id": contract_id,
        "status": {"$in": ["approved", "ai_flagged"]},
    })

    if processed >= total and total > 0:
        await contract_repo.update_status(
            db, contract_id, ContractStatus.REVIEW_READY, stage="orchestration"
        )
        logger.info("langgraph.contract_review_ready", contract_id=contract_id)

    return final_state
