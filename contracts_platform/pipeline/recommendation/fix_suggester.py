from contracts_platform.core.logging import logger
from contracts_platform.db.mongodb.client import get_database
from contracts_platform.pipeline.recommendation import generator, wording_retriever


async def generate_fixes(contract_id: str) -> None:
    """
    Entry point for fix generation called by recommendation_task.

    For each AMBER/RED clause in the contract:
    1. Retrieve accepted wording examples from Qdrant via wording_retriever.
    2. Call the LLM via generator to produce recommendation + suggested_fix.
    3. Store the results back to the MongoDB clause record.
    """
    logger.info("fix_suggester.called", contract_id=contract_id)
    db = await get_database()
    clauses = await db["clauses"].find(
        {"contract_id": contract_id, "risk_level": {"$in": ["AMBER", "RED"]}}
    ).to_list(None)
    for clause in clauses:
        clause_text = clause.get("raw_text", clause.get("clause_text", ""))
        accepted = await wording_retriever.retrieve_accepted_wording(
            clause.get("tenant_id", "default"), clause["clause_type"], clause_text
        )
        result = await generator.generate_recommendation(
            clause_text,
            clause["clause_type"],
            clause.get("risk_indicators", []),
            accepted,
        )
        await db["clauses"].update_one(
            {"_id": clause["_id"]},
            {"$set": {
                "recommendation": result.get("recommendation"),
                "suggested_fix": result.get("suggested_fix"),
            }},
        )
