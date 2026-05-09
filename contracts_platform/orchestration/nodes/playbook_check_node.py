from contracts_platform.core.logging import logger
from contracts_platform.db.postgresql.repositories.rule_repo import get_rules_for_jurisdiction
from contracts_platform.orchestration.state import ContractReviewState


async def playbook_check_node(state: ContractReviewState) -> dict:
    """
    Query PostgreSQL rule_repo for rules matching state['clause_type'] and state['jurisdiction'].
    Check for REQUIRED rules that are missing, or FORBIDDEN rules present in clause_text.
    Returns a partial state dict with playbook_result.
    On exception: set degraded_mode=True, add 'postgresql' to failed_sources, return partial state.
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    clause_type = state["clause_type"]
    clause_text = state["clause_text"]
    jurisdiction = state["jurisdiction"]

    logger.info(
        "playbook_check_node.start",
        contract_id=contract_id,
        clause_id=clause_id,
        clause_type=clause_type,
        jurisdiction=jurisdiction,
    )

    try:
        from contracts_platform.db.postgresql.client import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            rules = await get_rules_for_jurisdiction(session, jurisdiction, clause_type)

        findings: list[str] = []
        violation_count = 0

        for rule in rules:
            rule_type = rule.get("rule_type", "")
            description = rule.get("description", "")

            if rule_type == "FORBIDDEN":
                if description and description.lower() in clause_text.lower():
                    findings.append(f"FORBIDDEN clause detected: {description}")
                    violation_count += 1
            elif rule_type == "REQUIRED":
                if description and description.lower() not in clause_text.lower():
                    findings.append(f"REQUIRED content missing: {description}")
                    violation_count += 1

        rules_checked = len(rules)
        score = min(1.0, violation_count / max(rules_checked, 1)) if rules_checked > 0 else 0.0

        logger.info(
            "playbook_check_node.complete",
            contract_id=contract_id,
            clause_id=clause_id,
            rules_checked=rules_checked,
            violations=violation_count,
            score=score,
        )

        return {
            "playbook_result": {
                "score": score,
                "findings": findings,
                "rules_checked": rules_checked,
            }
        }

    except Exception as exc:
        logger.error(
            "playbook_check_node.failed",
            contract_id=contract_id,
            clause_id=clause_id,
            error=str(exc),
        )
        failed_sources = list(state.get("failed_sources") or [])
        if "postgresql" not in failed_sources:
            failed_sources.append("postgresql")
        return {
            "degraded_mode": True,
            "failed_sources": failed_sources,
            "playbook_result": None,
        }
