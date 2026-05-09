from __future__ import annotations

from typing import Optional

import openai
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contracts_platform.api.schemas.admin import (
    PlaybookRuleCreate,
    PlaybookRuleResponse,
    PlaybookRuleUpdate,
)
from contracts_platform.auth.rbac import require_role
from contracts_platform.core.config import settings
from contracts_platform.db.neo4j.repositories.clause_graph_repo import create_playbook_rule_node
from contracts_platform.db.postgresql.client import get_session
from contracts_platform.db.postgresql.models import PlaybookRule
from contracts_platform.db.postgresql.repositories import rule_repo
from contracts_platform.db.qdrant.repositories import clause_vector_repo

router = APIRouter(prefix="/admin", tags=["admin"])
logger = structlog.get_logger()


@router.get("/playbook-rules", response_model=list[PlaybookRuleResponse])
async def list_playbook_rules(
    jurisdiction: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_role("admin")),
) -> list[PlaybookRuleResponse]:
    """List all playbook rules, optionally filtered by jurisdiction."""
    stmt = select(PlaybookRule)
    if jurisdiction:
        stmt = stmt.where(PlaybookRule.jurisdiction == jurisdiction)
    result = await session.execute(stmt)
    rules = result.scalars().all()
    return [
        PlaybookRuleResponse(
            id=r.id,
            clause_type=r.clause_type,
            jurisdiction=r.jurisdiction,
            rule_type=r.rule_type,
            description=r.description,
            weight=r.weight,
            is_active=r.is_active,
        )
        for r in rules
    ]


@router.post("/playbook-rules", response_model=PlaybookRuleResponse, status_code=201)
async def create_playbook_rule(
    body: PlaybookRuleCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_role("admin")),
) -> PlaybookRuleResponse:
    """Create a new playbook rule."""
    rule_id = await rule_repo.create_rule(session, body.model_dump())
    result = await session.execute(select(PlaybookRule).where(PlaybookRule.id == rule_id))
    rule = result.scalar_one()
    logger.info("admin.playbook_rule.created", rule_id=rule_id, user=current_user.get("sub"))

    # --- Qdrant: embed description and upsert rule vector ---
    try:
        oai = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        embedding_response = await oai.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=body.description,
        )
        vector = embedding_response.data[0].embedding
        await clause_vector_repo.upsert_clause(
            tenant_id="playbook",
            clause_id=str(rule_id),
            vector=vector,
            payload={
                "clause_type": body.clause_type,
                "jurisdiction": body.jurisdiction,
                "rule_type": body.rule_type,
                "description": body.description,
                "weight": body.weight,
                "source": "playbook",
            },
        )
    except Exception as exc:
        logger.warning(
            "admin.playbook_rule.qdrant_sync_failed",
            rule_id=rule_id,
            error=str(exc),
        )

    # --- Neo4j: create PlaybookRule node with Jurisdiction and ClauseType links ---
    try:
        await create_playbook_rule_node(
            rule_id=rule_id,
            clause_type=body.clause_type,
            jurisdiction=body.jurisdiction,
            rule_type=body.rule_type,
            description=body.description,
        )
    except Exception as exc:
        logger.warning(
            "admin.playbook_rule.neo4j_sync_failed",
            rule_id=rule_id,
            error=str(exc),
        )

    return PlaybookRuleResponse(
        id=rule.id,
        clause_type=rule.clause_type,
        jurisdiction=rule.jurisdiction,
        rule_type=rule.rule_type,
        description=rule.description,
        weight=rule.weight,
        is_active=rule.is_active,
    )


@router.patch("/playbook-rules/{rule_id}", response_model=PlaybookRuleResponse)
async def update_playbook_rule(
    rule_id: int,
    body: PlaybookRuleUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_role("admin")),
) -> PlaybookRuleResponse:
    """Update a playbook rule's description, weight, or active status."""
    result = await session.execute(select(PlaybookRule).where(PlaybookRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found.")

    old_value = {
        "description": rule.description,
        "weight": rule.weight,
        "is_active": rule.is_active,
    }

    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(rule, field, value)

    await session.commit()
    await session.refresh(rule)

    new_value = {
        "description": rule.description,
        "weight": rule.weight,
        "is_active": rule.is_active,
    }
    await rule_repo.create_rule_version(
        session,
        rule_id=rule_id,
        old_value=old_value,
        new_value=new_value,
        changed_by=current_user.get("sub", "unknown"),
    )

    logger.info("admin.playbook_rule.updated", rule_id=rule_id, user=current_user.get("sub"))
    return PlaybookRuleResponse(
        id=rule.id,
        clause_type=rule.clause_type,
        jurisdiction=rule.jurisdiction,
        rule_type=rule.rule_type,
        description=rule.description,
        weight=rule.weight,
        is_active=rule.is_active,
    )


@router.delete("/playbook-rules/{rule_id}", status_code=204)
async def delete_playbook_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_role("admin")),
) -> None:
    """Soft-delete a playbook rule by setting is_active=False."""
    result = await session.execute(select(PlaybookRule).where(PlaybookRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found.")

    old_value = {"is_active": rule.is_active}
    rule.is_active = False
    await session.commit()

    await rule_repo.create_rule_version(
        session,
        rule_id=rule_id,
        old_value=old_value,
        new_value={"is_active": False},
        changed_by=current_user.get("sub", "unknown"),
    )

    logger.info("admin.playbook_rule.disabled", rule_id=rule_id, user=current_user.get("sub"))
