import asyncio

import redis

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
    queue="extraction",
    name="contracts_platform.workers.tasks.clause_extraction_task.clause_extraction_task",
    max_retries=RETRY_POLICY["clause_extraction_task"]["max_retries"],
    default_retry_delay=RETRY_POLICY["clause_extraction_task"]["countdown"],
)
def clause_extraction_task(self, contract_id: str) -> None:
    """Extract clauses from the OCR text stored in Redis."""

    async def _run() -> None:
        db = await get_database()
        try:
            publish(contract_id, "clause_extraction", 55, "clause extraction started")

            await contract_repo.update_status(
                db, contract_id, ContractStatus.PROCESSING, stage="clause_extraction"
            )

            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            text = r.get(f"ocr_text:{contract_id}") or ""
            auto_accept_flag = r.get(f"auto_accept_all:{contract_id}")
            auto_accept_all = bool(auto_accept_flag)

            from contracts_platform.pipeline.clause_extraction.extractor import extract_clauses

            # RAG: get ephemeral Qdrant collection name stored by ocr_task
            temp_name = r.get(f"temp_collection:{contract_id}") or ""

            clauses = await extract_clauses(contract_id, text)

            # Save clauses to permanent Qdrant + Neo4j
            contract_doc = await db["contracts"].find_one({"contract_id": contract_id}) or {}
            tenant_id = contract_doc.get("tenant_id", "default")

            for clause in (clauses or []):
                clause["contract_id"] = contract_id
                clause["tenant_id"] = tenant_id
                if auto_accept_all:
                    clause["status"] = "approved"
                    clause["risk_category"] = "GREEN"

            if clauses:
                await db["clauses"].insert_many(clauses)
            try:
                from contracts_platform.pipeline.embedder import embed_text
                from contracts_platform.db.qdrant.repositories.clause_vector_repo import upsert_clause
                from contracts_platform.db.neo4j.repositories.clause_graph_repo import create_clause_node
                for clause in (clauses or []):
                    try:
                        vector = await embed_text(clause.get("raw_text", ""))
                        await upsert_clause(
                            tenant_id=tenant_id,
                            clause_id=clause["clause_id"],
                            vector=vector,
                            payload={
                                "clause_type": clause.get("clause_type", ""),
                                "contract_id": contract_id,
                                "status": clause.get("status") or "pending",
                                "risk_level": clause.get("risk_category") or "UNKNOWN",
                                "created_at": str(clause.get("created_at", "")),
                            },
                        )
                        await create_clause_node(
                            clause_id=clause["clause_id"],
                            contract_id=contract_id,
                            tenant_id=tenant_id,
                            clause_type=clause.get("clause_type", ""),
                            risk_level=clause.get("risk_category") or "PENDING",
                            risk_score=float(clause.get("risk_score") or 0.0),
                            status=clause.get("status") or "pending",
                        )
                    except Exception as exc:
                        logger.warning("clause_extraction_task.clause_storage_failed",
                                       clause_id=clause.get("clause_id"), error=str(exc))
            except Exception as exc:
                logger.warning("clause_extraction_task.storage_import_failed", error=str(exc))

            # Cleanup ephemeral Qdrant collection
            if temp_name:
                try:
                    from contracts_platform.db.qdrant.repositories.clause_vector_repo import delete_temp_collection
                    await delete_temp_collection(temp_name)
                    r.delete(f"temp_collection:{contract_id}")
                    logger.info("clause_extraction_task.temp_collection.deleted", contract_id=contract_id)
                except Exception as exc:
                    logger.warning("clause_extraction_task.temp_cleanup_failed",
                                   contract_id=contract_id, error=str(exc))

            if auto_accept_all:
                from contracts_platform.core.constants import RiskLevel

                await contract_repo.update_final_risk(db, contract_id, RiskLevel.GREEN)
                await contract_repo.update_status(
                    db, contract_id, ContractStatus.COMPLETED, stage="auto_accept"
                )
                publish(
                    contract_id,
                    "auto_accept",
                    100,
                    "Playbook similarity >= 90%; all extracted clauses auto-approved",
                )
                r.delete(f"auto_accept_all:{contract_id}")
                logger.info(
                    "clause_extraction_task.auto_accepted",
                    contract_id=contract_id,
                    clauses=len(clauses or []),
                )
                return

            publish(contract_id, "clause_extraction", 75, "clauses extracted")

            from contracts_platform.workers.tasks.qdrant_check_task import qdrant_check_task

            qdrant_check_task.apply_async(args=[contract_id], queue="qdrant_check")

        except Exception as exc:
            await contract_repo.append_error(
                db, contract_id, stage="clause_extraction", message=str(exc)
            )
            logger.error("clause_extraction_task.error", contract_id=contract_id, error=str(exc))
            raise

    try:
        asyncio.run(_run())
    except Exception as exc:
        try:
            raise self.retry(exc=exc, countdown=RETRY_POLICY["clause_extraction_task"]["countdown"])
        except self.MaxRetriesExceededError:
            dead_letter_handler.apply_async(
                args=[contract_id, self.name, str(exc)],
                queue="dlq",
            )
