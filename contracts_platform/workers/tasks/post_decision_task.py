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
    """Persist the lawyer's review decision into Qdrant and Neo4j.
    Cleanup is triggered manually by the lawyer — not automatically here."""

    async def _run() -> None:
        db = await get_database()
        try:
            from contracts_platform.db.qdrant.repositories.clause_vector_repo import upsert_clause
            from contracts_platform.db.neo4j.repositories.clause_graph_repo import record_clause_review

            clause = await db["clauses"].find_one({"clause_id": clause_id})

            # Resolve tenant_id: prefer clause doc, fall back to contract doc
            tenant_id = clause.get("tenant_id") if clause else None
            if not tenant_id:
                contract_doc = await db["contracts"].find_one({"contract_id": contract_id})
                tenant_id = (contract_doc or {}).get("tenant_id") or "unknown"

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=clause.get("raw_text", clause.get("clause_text", "")) if clause else "",
            )
            vector = response.data[0].embedding

            await upsert_clause(
                tenant_id=tenant_id,
                clause_id=clause_id,
                vector=vector,
                payload={
                    "clause_type": clause.get("clause_type") if clause else None,
                    "decision": decision,
                    "modified_text": modified_text,
                    "status": decision,
                },
            )

            await record_clause_review(
                reviewer_id=reviewer_id,
                tenant_id=tenant_id,
                clause_id=clause_id,
                outcome=decision,
            )

            publish(contract_id, "post_decision", 100, "decision recorded")

            # Auto-trigger cleanup once ALL clauses are decided.
            # Atomic flag prevents multiple cleanup dispatches even if tasks run concurrently.
            total = await db["clauses"].count_documents({"contract_id": contract_id})
            decided = await db["clauses"].count_documents(
                {"contract_id": contract_id, "status": {"$in": ["approved", "rejected", "modified"]}}
            )
            if decided >= total and total > 0:
                triggered = await db["contracts"].find_one_and_update(
                    {"contract_id": contract_id, "cleanup_triggered": {"$ne": True}},
                    {"$set": {"cleanup_triggered": True}},
                )
                if triggered is not None:
                    from contracts_platform.workers.tasks.cleanup_task import cleanup_task
                    cleanup_task.apply_async(args=[contract_id], queue="cleanup")
                    logger.info("post_decision_task.cleanup_dispatched", contract_id=contract_id)

            logger.info(
                "post_decision_task.complete",
                contract_id=contract_id,
                clause_id=clause_id,
                decision=decision,
            )

        except Exception as exc:
            await contract_repo.append_error(
                db, contract_id, stage="post_decision", message=str(exc)
            )
            logger.error("post_decision_task.error", contract_id=contract_id, error=str(exc))
            raise

    try:
        asyncio.run(_run())
    except Exception as exc:
        try:
            raise self.retry(exc=exc, countdown=RETRY_POLICY["post_decision_task"]["countdown"])
        except self.MaxRetriesExceededError:
            dead_letter_handler.apply_async(
                args=[contract_id, self.name, str(exc)],
                queue="dlq",
            )
