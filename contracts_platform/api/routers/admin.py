from __future__ import annotations

import uuid
from typing import Optional

import openai
import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contracts_platform.api.schemas.admin import (
    PlaybookRuleCreate,
    PlaybookRulePDFUploadResponse,
    PlaybookRuleResponse,
    PlaybookRuleUpdate,
)
from contracts_platform.auth.rbac import require_role
from contracts_platform.core.config import settings
from contracts_platform.db.neo4j.repositories.clause_graph_repo import (
    create_playbook_rule_node,
    delete_playbook_rule_node,
)
from contracts_platform.db.postgresql.client import AsyncSessionLocal, get_session
from contracts_platform.db.postgresql.models import PlaybookRule
from contracts_platform.db.postgresql.repositories import rule_repo
from contracts_platform.db.qdrant.repositories import clause_vector_repo
from contracts_platform.db.qdrant.repositories.clause_vector_repo import (
    create_temp_collection,
    delete_temp_collection,
    search_collection,
    upsert_chunk,
)
from contracts_platform.pipeline.embedder import embed_text
from contracts_platform.pipeline.ocr.extractor import extract_pages, extract_text
from contracts_platform.pipeline.playbook_extractor import extract_playbook_rules_from_text

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
    """Hard-delete a playbook rule from PostgreSQL, Qdrant, and Neo4j."""
    result = await session.execute(select(PlaybookRule).where(PlaybookRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found.")

    await session.delete(rule)
    await session.commit()

    try:
        await clause_vector_repo.delete_clause(tenant_id="playbook", clause_id=str(rule_id))
    except Exception as exc:
        logger.warning("admin.playbook_rule.qdrant_delete_failed", rule_id=rule_id, error=str(exc))

    try:
        await delete_playbook_rule_node(rule_id=rule_id)
    except Exception as exc:
        logger.warning("admin.playbook_rule.neo4j_delete_failed", rule_id=rule_id, error=str(exc))

    logger.info("admin.playbook_rule.deleted", rule_id=rule_id, user=current_user.get("sub"))


@router.post(
    "/playbook-rules/upload-pdf",
    response_model=PlaybookRulePDFUploadResponse,
    status_code=201,
    include_in_schema=True,
)
async def upload_playbook_pdf(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("admin")),
) -> PlaybookRulePDFUploadResponse:
    """
    Upload a company policy PDF, extract playbook rules via OCR + LLM, and persist each rule
    to PostgreSQL, Qdrant, and Neo4j.
    """
    async with AsyncSessionLocal() as session:
        return await _do_upload_playbook_pdf(file, session, current_user)


async def _do_upload_playbook_pdf(file: UploadFile, session: AsyncSession, current_user: dict) -> PlaybookRulePDFUploadResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=415,
            detail={
                "type": "https://httpstatuses.com/415",
                "title": "Unsupported Media Type",
                "status": 415,
                "detail": (
                    f"Only PDF files are accepted (application/pdf). "
                    f"Received: {file.content_type}"
                ),
            },
        )

    file_bytes = await file.read()
    filename = file.filename or "upload.pdf"

    logger.info(
        "admin.playbook_pdf.received",
        filename=filename,
        size_bytes=len(file_bytes),
        user=current_user.get("sub"),
    )

    try:
        pages = await extract_pages(file_bytes, filename)
    except Exception as exc:
        logger.error("admin.playbook_pdf.ocr_failed", filename=filename, error=str(exc))
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://httpstatuses.com/422",
                "title": "OCR Extraction Failed",
                "status": 422,
                "detail": "Could not extract text from the uploaded PDF.",
            },
        )

    # Build ephemeral Qdrant collection for cross-page RAG context
    temp_name = ""
    try:
        temp_name = f"playbook_ingest_{uuid.uuid4().hex}"
        await create_temp_collection(temp_name)
        for page in pages:
            page_text = page.get("text", "").strip()
            if not page_text:
                continue
            vector = await embed_text(page_text)
            await upsert_chunk(
                temp_name,
                str(page.get("page_num", 0)),
                vector,
                {"text": page_text, "page_num": page.get("page_num", 0)},
            )
        logger.info("admin.playbook_pdf.temp_collection.ready", temp_name=temp_name, filename=filename)
    except Exception as exc:
        logger.warning("admin.playbook_pdf.temp_collection.failed", error=str(exc))
        temp_name = ""

    created_responses: list[PlaybookRuleResponse] = []

    for page in pages:
        page_text = page.get("text", "").strip()
        if not page_text:
            continue

        page_num = page.get("page_num", "?")
        logger.info("admin.playbook_pdf.processing_page", page_num=page_num, filename=filename)

        # Retrieve cross-page context from ephemeral collection
        context = ""
        if temp_name:
            try:
                vector = await embed_text(page_text)
                context_chunks = await search_collection(temp_name, vector, limit=4)
                other_chunks = [c for c in context_chunks if c["payload"].get("page_num") != page_num]
                context = "\n---\n".join(c["payload"]["text"] for c in other_chunks)
            except Exception as exc:
                logger.warning("admin.playbook_pdf.rag_retrieval_failed", page_num=page_num, error=str(exc))

        raw_rules = await extract_playbook_rules_from_text(page_text, context=context)

        logger.info(
            "admin.playbook_pdf.page_done",
            page_num=page_num,
            rules_this_page=len(raw_rules),
        )

        for rule_dict in raw_rules:
            # Normalise / validate required fields — skip malformed entries
            try:
                rule_create = PlaybookRuleCreate(
                    clause_type=rule_dict["clause_type"],
                    jurisdiction=rule_dict["jurisdiction"],
                    rule_type=rule_dict["rule_type"],
                    description=rule_dict["description"],
                    weight=float(rule_dict.get("weight", 1.0)),
                )
            except Exception as exc:
                logger.warning(
                    "admin.playbook_pdf.rule_validation_failed",
                    rule=rule_dict,
                    error=str(exc),
                )
                continue

            try:
                rule_id = await rule_repo.create_rule(session, rule_create.model_dump())
                result = await session.execute(
                    select(PlaybookRule).where(PlaybookRule.id == rule_id)
                )
                rule = result.scalar_one()
            except Exception as exc:
                logger.error(
                    "admin.playbook_pdf.postgres_insert_failed",
                    rule=rule_create.model_dump(),
                    error=str(exc),
                )
                continue

            # Qdrant: embed description and upsert rule vector
            try:
                oai = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                embedding_response = await oai.embeddings.create(
                    model=settings.EMBEDDING_MODEL,
                    input=rule_create.description,
                )
                vector = embedding_response.data[0].embedding
                await clause_vector_repo.upsert_clause(
                    tenant_id="playbook",
                    clause_id=str(rule_id),
                    vector=vector,
                    payload={
                        "clause_type": rule_create.clause_type,
                        "jurisdiction": rule_create.jurisdiction,
                        "rule_type": rule_create.rule_type,
                        "description": rule_create.description,
                        "weight": rule_create.weight,
                        "source": "playbook",
                    },
                )
            except Exception as exc:
                logger.warning(
                    "admin.playbook_pdf.qdrant_sync_failed",
                    rule_id=rule_id,
                    error=str(exc),
                )

            # Neo4j: create PlaybookRule node
            try:
                await create_playbook_rule_node(
                    rule_id=rule_id,
                    clause_type=rule_create.clause_type,
                    jurisdiction=rule_create.jurisdiction,
                    rule_type=rule_create.rule_type,
                    description=rule_create.description,
                )
            except Exception as exc:
                logger.warning(
                    "admin.playbook_pdf.neo4j_sync_failed",
                    rule_id=rule_id,
                    error=str(exc),
                )

            logger.info(
                "admin.playbook_pdf.rule_created",
                rule_id=rule_id,
                clause_type=rule_create.clause_type,
                user=current_user.get("sub"),
            )
            created_responses.append(
                PlaybookRuleResponse(
                    id=rule.id,
                    clause_type=rule.clause_type,
                    jurisdiction=rule.jurisdiction,
                    rule_type=rule.rule_type,
                    description=rule.description,
                    weight=rule.weight,
                    is_active=rule.is_active,
                )
            )

    if temp_name:
        try:
            await delete_temp_collection(temp_name)
        except Exception as exc:
            logger.warning("admin.playbook_pdf.temp_cleanup_failed", error=str(exc))

    logger.info(
        "admin.playbook_pdf.completed",
        filename=filename,
        rules_created=len(created_responses),
        user=current_user.get("sub"),
    )
    return PlaybookRulePDFUploadResponse(
        rules_created=len(created_responses),
        rules=created_responses,
    )
