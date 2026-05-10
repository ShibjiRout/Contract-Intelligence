from __future__ import annotations

from openai import AsyncOpenAI

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger
from contracts_platform.orchestration.state import ContractReviewState

_SYSTEM_PROMPT = (
    "You are a senior legal counsel writing a recommendation for a junior lawyer. "
    "You will receive:\n"
    "1. The legal intent of the clause submitted by the counterparty.\n"
    "2. The gap between their clause and our Gold Standard.\n"
    "3. A precedent note (if we have accepted a similar clause before).\n"
    "4. Any policy violations from our playbook.\n\n"
    "Write a concise recommendation (3-5 sentences) that:\n"
    "- Explains what is wrong with the clause\n"
    "- References the precedent if one exists\n"
    "- Proposes a specific counter-edit with exact legal wording\n\n"
    "End with a section labelled 'Proposed Counter:' containing the exact replacement wording."
)


async def recommendation_node(state: ContractReviewState) -> dict:
    """
    Step 5: Generate AI recommendation using all context from previous nodes.
    Combines: legal_intent + gap_summary + precedent + violation_message
    → writes a lawyer-ready recommendation with a proposed counter-edit.
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]

    legal_intent = state.get("legal_intent") or "Not available"
    gap_summary = state.get("gap_summary") or "Not available"
    violation_message = state.get("violation_message") or "No policy violations detected"
    precedent = state.get("precedent")

    if precedent:
        precedent_note = (
            f"Precedent: We previously accepted a similar clause for "
            f"{precedent.get('party')} on {precedent.get('date')} "
            f"(Contract ID: {precedent.get('contract_id')})."
        )
    else:
        precedent_note = "Precedent: No prior acceptance of this clause type found."

    logger.info(
        "recommendation_node.start",
        contract_id=contract_id,
        clause_id=clause_id,
    )

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        user_message = (
            f"Legal Intent: {legal_intent}\n\n"
            f"Gap from Gold Standard: {gap_summary}\n\n"
            f"Policy Violations: {violation_message}\n\n"
            f"{precedent_note}"
        )

        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=500,
            temperature=0.2,
        )

        ai_recommendation = (response.choices[0].message.content or "").strip()

        logger.info(
            "recommendation_node.complete",
            contract_id=contract_id,
            clause_id=clause_id,
        )

        return {"ai_recommendation": ai_recommendation}

    except Exception as exc:
        logger.error(
            "recommendation_node.failed",
            contract_id=contract_id,
            clause_id=clause_id,
            error=str(exc),
        )
        failed_sources = list(state.get("failed_sources") or [])
        failed_sources.append("recommendation")
        return {
            "ai_recommendation": "Unable to generate recommendation. Please review manually.",
            "failed_sources": failed_sources,
        }
