from langgraph.graph import END, START, StateGraph

from contracts_platform.core.logging import logger
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
    Build a minimal initial state and run the graph.
    In real usage the state would be populated from MongoDB.
    For now: log that the graph was invoked and return a stub result.
    """
    logger.info("langgraph.run", contract_id=contract_id)
    # Stub — real wire-up happens when state is fully populated by pipeline
    return {"contract_id": contract_id, "status": "graph_invoked"}
