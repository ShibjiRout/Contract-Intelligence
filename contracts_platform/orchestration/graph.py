from langgraph.graph import END, START, StateGraph

from contracts_platform.core.logging import logger
from contracts_platform.db.mongodb.client import get_database
from contracts_platform.orchestration.nodes.explainability_node import explainability_node
from contracts_platform.orchestration.nodes.graph_check_node import graph_check_node
from contracts_platform.orchestration.nodes.playbook_check_node import playbook_check_node
from contracts_platform.orchestration.nodes.recommendation_node import recommendation_node
from contracts_platform.orchestration.nodes.risk_aggregator_node import risk_aggregator_node
from contracts_platform.orchestration.nodes.vector_check_node import vector_check_node
from contracts_platform.orchestration.state import ContractReviewState


def _should_recommend(state: ContractReviewState) -> str:
    """Route to recommendation only when risk is AMBER or RED."""
    return "recommend" if state["risk_level"] != "GREEN" else "explain"


def build_graph() -> StateGraph:
    """
    Construct the LangGraph StateGraph for contract clause review.

    Topology:
      START -> [playbook_check, vector_check, graph_check]  (parallel fan-out)
            -> risk_aggregator
            -> recommendation (AMBER/RED) or directly -> explainability (GREEN)
            -> explainability -> END
    """
    graph = StateGraph(ContractReviewState)

    graph.add_node("playbook_check", playbook_check_node)
    graph.add_node("vector_check", vector_check_node)
    graph.add_node("graph_check", graph_check_node)
    graph.add_node("risk_aggregator", risk_aggregator_node)
    graph.add_node("recommendation", recommendation_node)
    graph.add_node("explainability", explainability_node)

    # True parallel fan-out from START to all three check nodes
    graph.add_edge(START, "playbook_check")
    graph.add_edge(START, "vector_check")
    graph.add_edge(START, "graph_check")

    # All three converge into risk_aggregator
    graph.add_edge("playbook_check", "risk_aggregator")
    graph.add_edge("vector_check", "risk_aggregator")
    graph.add_edge("graph_check", "risk_aggregator")

    # Conditional: skip recommendation for GREEN risk
    graph.add_conditional_edges(
        "risk_aggregator",
        _should_recommend,
        {
            "recommend": "recommendation",
            "explain": "explainability",
        },
    )

    graph.add_edge("recommendation", "explainability")
    graph.add_edge("explainability", END)

    return graph


async def run_review_graph(contract_id: str) -> dict:
    """
    Entry point called by review_orchestration_task.
    Loads all clauses for the contract from MongoDB, runs the compiled LangGraph
    for each clause, and persists risk results back to MongoDB.
    """
    logger.info("langgraph.run", contract_id=contract_id)

    db = await get_database()

    clauses = await db["clauses"].find({"contract_id": contract_id}).to_list(None)
    contract = await db["contracts"].find_one({"contract_id": contract_id})

    tenant_id: str = (contract or {}).get("tenant_id", "")

    compiled_graph = build_graph().compile()

    results = []
    for clause in clauses:
        state: ContractReviewState = {
            "contract_id": contract_id,
            "clause_id": str(clause.get("clause_id", clause.get("_id", ""))),
            "clause_type": clause.get("clause_type", ""),
            "clause_text": clause.get("clause_text", ""),
            "jurisdiction": clause.get("jurisdiction", contract.get("jurisdiction", "") if contract else ""),
            "tenant_id": tenant_id,
            "playbook_result": None,
            "vector_result": None,
            "graph_result": None,
            "risk_level": "GREEN",
            "risk_score": 0.0,
            "degraded_mode": False,
            "failed_sources": [],
            "missing_clauses": [],
            "recommendation": None,
            "suggested_fix": None,
            "explanation": None,
            "messages": [],
        }

        final_state = await compiled_graph.ainvoke(state)

        await db["clauses"].update_one(
            {"_id": clause["_id"]},
            {
                "$set": {
                    "risk_level": final_state.get("risk_level"),
                    "risk_score": final_state.get("risk_score"),
                    "playbook_result": final_state.get("playbook_result"),
                    "vector_result": final_state.get("vector_result"),
                    "graph_result": final_state.get("graph_result"),
                    "degraded_mode": final_state.get("degraded_mode"),
                }
            },
        )

        results.append(final_state)
        logger.info(
            "langgraph.clause_processed",
            contract_id=contract_id,
            clause_id=state["clause_id"],
            risk_level=final_state.get("risk_level"),
        )

    return {"contract_id": contract_id, "clauses_processed": len(results)}
