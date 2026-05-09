from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException

from contracts_platform.api.dependencies import get_current_user, get_db
from contracts_platform.api.schemas.clause import ClauseModifyRequest, RecommendationResponse
from contracts_platform.auth.rbac import require_role

router = APIRouter(prefix="/clauses", tags=["clauses"])
logger = structlog.get_logger()


async def _get_clause_or_404(db, clause_id: str) -> dict:
    doc = await db["clauses"].find_one({"clause_id": clause_id}, {"_id": 0})
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Clause '{clause_id}' not found.")
    return doc


def _dispatch_post_decision(contract_id: str, clause_id: str, decision: str, **kwargs):
    try:
        from contracts_platform.workers.tasks.post_decision_task import post_decision_task

        post_decision_task.apply_async(
            args=[contract_id, clause_id, decision],
            kwargs=kwargs,
            queue="post_decision",
        )
    except Exception as exc:
        logger.warning(
            "clauses.dispatch_failed",
            clause_id=clause_id,
            decision=decision,
            error=str(exc),
        )


@router.patch(
    "/{clause_id}/approve",
    dependencies=[Depends(require_role("senior_lawyer", "admin"))],
)
async def approve_clause(
    clause_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    clause = await _get_clause_or_404(db, clause_id)
    await db["clauses"].update_one(
        {"clause_id": clause_id},
        {"$set": {"status": "approved", "reviewed_by": current_user["sub"]}},
    )
    _dispatch_post_decision(clause["contract_id"], clause_id, "approved")
    logger.info("clauses.approved", clause_id=clause_id, user_id=current_user["sub"])
    return {"clause_id": clause_id, "status": "approved"}


@router.patch(
    "/{clause_id}/reject",
    dependencies=[Depends(require_role("senior_lawyer", "admin"))],
)
async def reject_clause(
    clause_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    clause = await _get_clause_or_404(db, clause_id)
    await db["clauses"].update_one(
        {"clause_id": clause_id},
        {"$set": {"status": "rejected", "reviewed_by": current_user["sub"]}},
    )
    _dispatch_post_decision(clause["contract_id"], clause_id, "rejected")
    logger.info("clauses.rejected", clause_id=clause_id, user_id=current_user["sub"])
    return {"clause_id": clause_id, "status": "rejected"}


@router.patch(
    "/{clause_id}/modify",
    dependencies=[Depends(require_role("senior_lawyer", "admin"))],
)
async def modify_clause(
    clause_id: str,
    body: ClauseModifyRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    clause = await _get_clause_or_404(db, clause_id)
    await db["clauses"].update_one(
        {"clause_id": clause_id},
        {
            "$set": {
                "status": "modified",
                "modified_text": body.modified_text,
                "reviewed_by": current_user["sub"],
            }
        },
    )
    _dispatch_post_decision(
        clause["contract_id"], clause_id, "modified", modified_text=body.modified_text
    )
    logger.info("clauses.modified", clause_id=clause_id, user_id=current_user["sub"])
    return {"clause_id": clause_id, "status": "modified"}


@router.get(
    "/{clause_id}/recommendation",
    response_model=RecommendationResponse,
    dependencies=[Depends(require_role("junior_lawyer", "senior_lawyer", "admin"))],
)
async def get_recommendation(clause_id: str, db=Depends(get_db)):
    clause = await _get_clause_or_404(db, clause_id)
    return RecommendationResponse(
        clause_id=clause_id,
        recommendation=clause.get("recommendation", ""),
        suggested_fix=clause.get("suggested_fix", ""),
        alternative_fixes=clause.get("alternative_fixes", []),
    )
