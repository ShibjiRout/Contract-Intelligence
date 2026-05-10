from __future__ import annotations

from openai import AsyncOpenAI

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger
from contracts_platform.db.qdrant.repositories.clause_vector_repo import search_similar
from contracts_platform.orchestration.state import ContractReviewState

_SYSTEM_PROMPT = (
    "You are a senior legal analyst. You will be given:\n"
    "1. The legal intent of a contract clause submitted by the counterparty.\n"
    "2. The closest matching Gold Standard clause from our firm's playbook.\n\n"
    "Your job is to identify the gap between what they are proposing and what our standard requires. "
    "Write one clear sentence describing the gap. "
    "Output only the gap sentence. No explanation, no preamble."
)


async def gap_analysis_node(state: ContractReviewState) -> dict:
    """
    Step 2: Compare the extracted legal intent against the Gold Standard in Qdrant.
    Finds the closest matching playbook clause and asks LLM to describe the gap.
    e.g. 'Clause caps liability at 50% of fees; Gold Standard requires 100% of contract value.'
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    clause_type = state["clause_type"]
    legal_intent = state.get("legal_intent") or state["clause_text"]

    logger.info(
        "gap_analysis_node.start",
        contract_id=contract_id,
        clause_id=clause_id,
    )

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Embed the legal intent
        embedding_response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=legal_intent,
        )
        vector = embedding_response.data[0].embedding

        # Search Gold Standard (playbook collection)
        matches = await search_similar(
            tenant_id="playbook",
            vector=vector,
            clause_type=clause_type,
            status="accepted",
            limit=1,
        )

        if not matches:
            logger.info(
                "gap_analysis_node.no_gold_standard",
                contract_id=contract_id,
                clause_id=clause_id,
            )
            return {"gap_summary": "No Gold Standard found for this clause type."}

        gold_standard_text = matches[0]["payload"].get("description", "")
        gold_standard_score = matches[0]["score"]

        # Ask LLM to describe the gap
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Clause intent: {legal_intent}\n\n"
                        f"Gold Standard: {gold_standard_text}"
                    ),
                },
            ],
            max_tokens=200,
            temperature=0,
        )

        gap_summary = (response.choices[0].message.content or "").strip()

        logger.info(
            "gap_analysis_node.complete",
            contract_id=contract_id,
            clause_id=clause_id,
            gold_standard_score=gold_standard_score,
            gap_summary=gap_summary,
        )

        return {"gap_summary": gap_summary}

    except Exception as exc:
        logger.error(
            "gap_analysis_node.failed",
            contract_id=contract_id,
            clause_id=clause_id,
            error=str(exc),
        )
        failed_sources = list(state.get("failed_sources") or [])
        failed_sources.append("gap_analysis")
        return {
            "gap_summary": "Gap analysis unavailable.",
            "failed_sources": failed_sources,
        }
