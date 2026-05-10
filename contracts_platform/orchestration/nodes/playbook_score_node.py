from __future__ import annotations

from contracts_platform.core.logging import logger
from contracts_platform.db.postgresql.client import get_fresh_session_factory
from contracts_platform.db.postgresql.repositories.rule_repo import get_rules_for_jurisdiction
from contracts_platform.orchestration.state import ContractReviewState


async def playbook_score_node(state: ContractReviewState) -> dict:
    """
    Step 4: Check the clause against PostgreSQL playbook rules.
    Assigns risk_category (RED / AMBER / GREEN) and a specific violation_message.

    FORBIDDEN rule found in clause text → violation
    REQUIRED rule missing from clause text → violation

    Score >= 0.7 → RED
    Score >= 0.4 or any violation → AMBER
    else → GREEN
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    clause_type = state["clause_type"]
    clause_text = state["clause_text"]
    jurisdiction = state["jurisdiction"]

    logger.info(
        "playbook_score_node.start",
        contract_id=contract_id,
        clause_id=clause_id,
        jurisdiction=jurisdiction,
    )

    try:
        async with get_fresh_session_factory()() as session:
            rules = await get_rules_for_jurisdiction(session, jurisdiction, clause_type)

        violation_messages: list[str] = []
        violation_weight_sum = 0.0
        total_weight_sum = 0.0

        for rule in rules:
            rule_type = rule.get("rule_type", "")
            description = rule.get("description", "")
            weight = float(rule.get("weight", 1.0))
            # Use admin-written violation_message if available, else build one
            custom_msg = rule.get("violation_message") or ""
            total_weight_sum += weight

            if rule_type == "FORBIDDEN":
                if description and description.lower() in clause_text.lower():
                    msg = custom_msg or f"Violation: FORBIDDEN clause detected — {description}"
                    violation_messages.append(msg)
                    violation_weight_sum += weight

            elif rule_type == "REQUIRED":
                if description and description.lower() not in clause_text.lower():
                    msg = custom_msg or f"Violation: REQUIRED content missing — {description}"
                    violation_messages.append(msg)
                    violation_weight_sum += weight

        score = (
            min(1.0, violation_weight_sum / max(total_weight_sum, 1.0))
            if total_weight_sum > 0
            else 0.0
        )

        if score >= 0.7:
            risk_category = "RED"
        elif score >= 0.4 or violation_messages:
            risk_category = "AMBER"
        else:
            risk_category = "GREEN"

        violation_message = " | ".join(violation_messages) if violation_messages else None

        logger.info(
            "playbook_score_node.complete",
            contract_id=contract_id,
            clause_id=clause_id,
            risk_category=risk_category,
            violations=len(violation_messages),
        )

        return {
            "risk_category": risk_category,
            "violation_message": violation_message,
        }

    except Exception as exc:
        logger.error(
            "playbook_score_node.failed",
            contract_id=contract_id,
            clause_id=clause_id,
            error=str(exc),
        )
        failed_sources = list(state.get("failed_sources") or [])
        failed_sources.append("postgresql")
        return {
            "risk_category": "AMBER",  # safe default when rules unavailable
            "violation_message": None,
            "failed_sources": failed_sources,
        }
