import asyncio

from openai import AsyncOpenAI

from contracts_platform.core.config import settings
from contracts_platform.core.constants import ContractStatus
from contracts_platform.core.logging import logger
from contracts_platform.db.mongodb.client import get_database
from contracts_platform.db.mongodb.repositories import contract_repo
from contracts_platform.workers.celery_app import app
from contracts_platform.workers.dead_letter import dead_letter_handler
from contracts_platform.workers.progress_tracker import publish
from contracts_platform.workers.retry_policy import RETRY_POLICY

_FINAL_DECISIONS = {"approved", "rejected", "modified"}


@app.task(
    bind=True,
    queue="post_decision",
    name="contracts_platform.workers.tasks.post_decision_task.post_decision_task",
    max_retries=RETRY_POLICY["post_decision_task"]["max_retries"],
    default_retry_delay=RETRY_POLICY["post_decision_task"]["countdown"],
)
def post_decision_task(
    self,
    contract_id: str,
    clause_id: str,
    decision: str,
    modified_text: str | None = None,
    reviewer_id: str = "unknown",
) -> None:
    """Persist the lawyer's review decision into Qdrant and Neo4j, then trigger cleanup."""
    try:
        db = asyncio.run(get_database())
        asyncio.run(
            contract_repo.update_status(
                db, contract_id, ContractStatus.PROCESSING, stage="post_decision"
            )
        )

        # Stub calls — db agents will implement
        from contracts_platform.db.qdrant.repositories.clause_vector_repo import upsert_clause  # type: ignore[import]
        from contracts_platform.db.neo4j.repositories.clause_graph_repo import add_review_decision  # type: ignore[import]

        clause = asyncio.run(db["clauses"].find_one({"clause_id": clause_id}))

        async def _embed(text: str) -> list[float]:
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.embeddings.create(model=settings.EMBEDDING_MODEL, input=text)
            return response.data[0].embedding

        vector = asyncio.run(_embed(clause.get("clause_text", "") if clause else ""))

        asyncio.run(
            upsert_clause(
                tenant_id=clause["tenant_id"] if clause else "unknown",
                clause_id=clause_id,
                vector=vector,
                payload={
                    "clause_type": clause.get("clause_type") if clause else None,
                    "decision": decision,
                    "modified_text": modified_text,
                },
            )
        )  # type: ignore[arg-type]

        parties = clause.get("parties_mentioned", []) if clause else []
        party_id = parties[0] if parties else "unknown"
        asyncio.run(
            add_review_decision(
                party_id=party_id,
                contract_id=contract_id,
                reviewer_id=reviewer_id,
                outcome=decision,
            )
        )  # type: ignore[arg-type]

        publish(contract_id, "post_decision", 100, "decision recorded")

        if decision in _FINAL_DECISIONS:
            from contracts_platform.workers.tasks.cleanup_task import cleanup_task

            cleanup_task.apply_async(args=[contract_id], queue="cleanup")

    except Exception as exc:
        db = asyncio.run(get_database())
        asyncio.run(
            contract_repo.append_error(
                db, contract_id, stage="post_decision", message=str(exc)
            )
        )
        logger.error("post_decision_task.error", contract_id=contract_id, error=str(exc))
        try:
            raise self.retry(exc=exc, countdown=RETRY_POLICY["post_decision_task"]["countdown"])
        except self.MaxRetriesExceededError:
            dead_letter_handler.apply_async(
                args=[contract_id, self.name, str(exc)],
                queue="dlq",
            )
