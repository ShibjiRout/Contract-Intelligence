from __future__ import annotations

from openai import AsyncOpenAI

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger
from contracts_platform.orchestration.state import ContractReviewState

_SYSTEM_PROMPT = (
    "You are a senior legal analyst. Your job is to read a contract clause and extract "
    "its core legal intent in one clear sentence. Focus on what the clause is trying to "
    "achieve legally — the obligation, right, or limitation it creates. "
    "Output only the intent sentence. No explanation, no preamble."
)


async def intent_extraction_node(state: ContractReviewState) -> dict:
    """
    Step 1: Extract the legal intent of the clause using LLM.
    e.g. 'Limiting liability cap to 50% of total fees paid.'
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    clause_text = state["clause_text"]

    logger.info(
        "intent_extraction_node.start",
        contract_id=contract_id,
        clause_id=clause_id,
    )

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract the legal intent of this clause:\n\n{clause_text}"},
            ],
            max_tokens=150,
            temperature=0,
        )

        legal_intent = (response.choices[0].message.content or "").strip()

        logger.info(
            "intent_extraction_node.complete",
            contract_id=contract_id,
            clause_id=clause_id,
            legal_intent=legal_intent,
        )

        return {"legal_intent": legal_intent}

    except Exception as exc:
        logger.error(
            "intent_extraction_node.failed",
            contract_id=contract_id,
            clause_id=clause_id,
            error=str(exc),
        )
        failed_sources = list(state.get("failed_sources") or [])
        failed_sources.append("intent_extraction")
        return {
            "legal_intent": clause_text[:200],  # fallback: use raw text start
            "failed_sources": failed_sources,
        }
