from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from contracts_platform.api.dependencies import get_current_user, get_db
from contracts_platform.api.schemas.clause import (
    ClauseAddRequest,
    ClauseModifyRequest,
    ClauseResponse,
    RecommendationResponse,
)
from contracts_platform.auth.rbac import require_role
from contracts_platform.db.neo4j.repositories.clause_graph_repo import record_clause_review

router = APIRouter(prefix="/clauses", tags=["clauses"])
logger = structlog.get_logger()


async def _get_clause_or_404(db, clause_id: str) -> dict:
    doc = await db["clauses"].find_one({"clause_id": clause_id}, {"_id": 0})
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Clause '{clause_id}' not found.")
    return doc


async def _get_clause_for_tenant_or_404(db, clause_id: str, tenant_id: str) -> dict:
    doc = await _get_clause_or_404(db, clause_id)
    clause_tenant_id = doc.get("tenant_id")
    if clause_tenant_id:
        if clause_tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=f"Clause '{clause_id}' not found.")
        return doc

    contract_id = doc.get("contract_id")
    contract = await db["contracts"].find_one(
        {"contract_id": contract_id, "tenant_id": tenant_id},
        {"_id": 0},
    )
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Clause '{clause_id}' not found.")
    return doc


async def _record_neo4j_decision(
    clause: dict,
    tenant_id: str,
    reviewer_id: str,
    outcome: str,
) -> None:
    """Record lawyer decision in Neo4j. Runs as a background task."""
    clause_id = clause.get("clause_id", "")
    try:
        await record_clause_review(
            reviewer_id=reviewer_id,
            tenant_id=tenant_id,
            clause_id=clause_id,
            outcome=outcome,
        )
        logger.info("clauses.neo4j_recorded", clause_id=clause_id, outcome=outcome)
    except Exception as exc:
        logger.error("clauses.neo4j_record_failed", clause_id=clause_id, error=str(exc))


@router.patch(
    "/{clause_id}/approve",
    dependencies=[Depends(require_role("senior_lawyer", "admin"))],
)
async def approve_clause(
    clause_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    clause = await _get_clause_for_tenant_or_404(db, clause_id, current_user["tenant_id"])
    await db["clauses"].update_one(
        {"clause_id": clause_id, "tenant_id": current_user["tenant_id"]},
        {"$set": {"status": "approved", "reviewed_by": current_user["sub"]}},
    )
    background_tasks.add_task(
        _record_neo4j_decision, clause, current_user["tenant_id"], current_user["sub"], "approved"
    )
    logger.info("clauses.approved", clause_id=clause_id, user_id=current_user["sub"])
    return {"clause_id": clause_id, "status": "approved"}


@router.patch(
    "/{clause_id}/reject",
    dependencies=[Depends(require_role("senior_lawyer", "admin"))],
)
async def reject_clause(
    clause_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    clause = await _get_clause_for_tenant_or_404(db, clause_id, current_user["tenant_id"])
    await db["clauses"].update_one(
        {"clause_id": clause_id, "tenant_id": current_user["tenant_id"]},
        {"$set": {"status": "rejected", "reviewed_by": current_user["sub"]}},
    )
    background_tasks.add_task(
        _record_neo4j_decision, clause, current_user["tenant_id"], current_user["sub"], "rejected"
    )
    logger.info("clauses.rejected", clause_id=clause_id, user_id=current_user["sub"])
    return {"clause_id": clause_id, "status": "rejected"}


@router.patch(
    "/{clause_id}/modify",
    dependencies=[Depends(require_role("senior_lawyer", "admin"))],
)
async def modify_clause(
    clause_id: str,
    body: ClauseModifyRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    clause = await _get_clause_for_tenant_or_404(db, clause_id, current_user["tenant_id"])

    update: dict = {
        "status": "need_changes",
        "reviewed_by": current_user["sub"],
        "lawyer_recommendation": body.lawyer_recommendation,
        "lawyer_mail_id": body.lawyer_mail_id,
    }
    if body.accept_ai_recommendation:
        update["lawyer_recommendation"] = clause.get("ai_recommendation", "")

    await db["clauses"].update_one(
        {"clause_id": clause_id, "tenant_id": current_user["tenant_id"]},
        {"$set": update},
    )
    background_tasks.add_task(
        _record_neo4j_decision,
        clause,
        current_user["tenant_id"],
        current_user["sub"],
        "need_changes",
    )
    logger.info("clauses.modified", clause_id=clause_id, user_id=current_user["sub"])
    return {"clause_id": clause_id, "status": "need_changes"}


@router.post(
    "/new",
    response_model=ClauseResponse,
    dependencies=[Depends(require_role("senior_lawyer", "admin"))],
)
async def add_clause(
    body: ClauseAddRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Lawyer adds a brand new clause to a contract — immediately approved."""
    contract = await db["contracts"].find_one(
        {"contract_id": body.contract_id, "tenant_id": current_user["tenant_id"]},
        {"_id": 0},
    )
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract '{body.contract_id}' not found.")

    clause_id = str(uuid.uuid4())
    doc = {
        "clause_id": clause_id,
        "contract_id": body.contract_id,
        "tenant_id": current_user["tenant_id"],
        "clause_type": body.clause_type,
        "raw_text": body.raw_text,
        "start_page": 0,
        "end_page": 0,
        "status": "approved",
        "risk_category": "GREEN",
        "reviewed_by": current_user["sub"],
        "confidence": 1.0,
        "parties_mentioned": [],
    }
    await db["clauses"].insert_one({**doc, "_id": clause_id})
    logger.info(
        "clauses.added",
        clause_id=clause_id,
        contract_id=body.contract_id,
        user_id=current_user["sub"],
    )
    return ClauseResponse(**doc)


@router.delete(
    "/{clause_id}",
    dependencies=[Depends(require_role("admin"))],
)
async def delete_clause(
    clause_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    await _get_clause_for_tenant_or_404(db, clause_id, current_user["tenant_id"])
    await db["clauses"].delete_one(
        {"clause_id": clause_id, "tenant_id": current_user["tenant_id"]}
    )
    logger.info("clauses.deleted", clause_id=clause_id)
    return {"clause_id": clause_id, "deleted": True}


@router.get(
    "/{clause_id}/recommendation",
    response_model=RecommendationResponse,
    dependencies=[Depends(require_role("junior_lawyer", "senior_lawyer", "admin"))],
)
async def get_recommendation(
    clause_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    clause = await _get_clause_for_tenant_or_404(db, clause_id, current_user["tenant_id"])
    return RecommendationResponse(
        clause_id=clause_id,
        ai_recommendation=clause.get("ai_recommendation", ""),
        legal_intent=clause.get("legal_intent"),
        gap_summary=clause.get("gap_summary"),
        violation_message=clause.get("violation_message"),
        precedent=clause.get("precedent"),
    )
