from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import Response

from contracts_platform.api.dependencies import get_current_user, get_db
from contracts_platform.api.schemas.clause import ClauseResponse
from contracts_platform.api.schemas.contract import (
    ContractDetailResponse,
    ContractStatusResponse,
    ContractUploadResponse,
)
from contracts_platform.auth.rbac import require_role
from contracts_platform.core.constants import ContractStatus
from contracts_platform.core.exceptions import DuplicateContractError, FileValidationError
from contracts_platform.db.mongodb.repositories import contract_repo
from contracts_platform.file_handling import storage
from contracts_platform.file_handling.validator import validate_upload
from contracts_platform.workers.tasks.ingest_task import ingest_task

router = APIRouter(prefix="/contracts", tags=["contracts"])
logger = structlog.get_logger()


@router.post(
    "/upload",
    response_model=ContractUploadResponse,
    dependencies=[Depends(require_role("junior_lawyer", "senior_lawyer", "admin"))],
)
async def upload_contract(
    file: UploadFile,
    jurisdiction: str = Form(default="UK"),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    file_bytes = await file.read()

    validate_upload(file_bytes, file.filename or "", file.content_type or "")

    # Duplicate detection via SHA-256
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing = await contract_repo.get_by_file_hash(
        db,
        file_hash,
        tenant_id=current_user["tenant_id"],
    )
    if existing:
        raise DuplicateContractError(
            f"Duplicate contract detected.",
            existing_contract_id=existing["contract_id"],
        )

    contract_id = str(uuid4())
    now = datetime.now(timezone.utc)

    doc = {
        "contract_id": contract_id,
        "filename": file.filename,
        "file_hash": file_hash,
        "status": ContractStatus.UPLOADED.value,
        "current_stage": None,
        "final_risk": None,
        "jurisdiction": jurisdiction.upper().strip(),
        "user_id": current_user["sub"],
        "tenant_id": current_user["tenant_id"],
        "errors": [],
        "created_at": now,
        "updated_at": now,
    }
    await contract_repo.create_contract(db, doc)

    try:
        from contracts_platform.db.neo4j.repositories.contract_graph_repo import create_contract_node

        await create_contract_node(
            contract_id=contract_id,
            tenant_id=current_user["tenant_id"],
            filename=file.filename or "",
            jurisdiction=doc["jurisdiction"],
            status=ContractStatus.UPLOADED.value,
        )
    except Exception as exc:
        logger.warning("contracts.graph_create_failed", contract_id=contract_id, error=str(exc))

    await storage.upload_contract(contract_id, file_bytes, file.filename or "")

    # Dispatch ingest task
    b64 = base64.b64encode(file_bytes).decode()
    ingest_task.apply_async(
        args=[contract_id, b64, file.filename, current_user["sub"], current_user["tenant_id"]],
        queue="ingest",
    )

    logger.info("contracts.uploaded", contract_id=contract_id, user_id=current_user["sub"])
    return ContractUploadResponse(
        contract_id=contract_id,
        status=ContractStatus.UPLOADED.value,
        message="Contract uploaded successfully and queued for processing.",
    )


@router.get(
    "/",
    response_model=list[ContractDetailResponse],
    dependencies=[Depends(require_role("junior_lawyer", "senior_lawyer", "admin"))],
)
async def list_contracts(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    cursor = (
        db["contracts"]
        .find({"tenant_id": current_user["tenant_id"]}, {"_id": 0})
        .sort("created_at", -1)
        .limit(100)
    )
    docs = await cursor.to_list(length=100)
    return [
        ContractDetailResponse(
            contract_id=d["contract_id"],
            filename=d["filename"],
            status=d["status"],
            current_stage=d.get("current_stage"),
            final_risk=d.get("final_risk"),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        )
        for d in docs
    ]


@router.get(
    "/{contract_id}",
    response_model=ContractDetailResponse,
    dependencies=[Depends(require_role("junior_lawyer", "senior_lawyer", "admin"))],
)
async def get_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    doc = await contract_repo.get_contract_for_tenant(
        db,
        contract_id,
        current_user["tenant_id"],
    )
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found.")
    return ContractDetailResponse(
        contract_id=doc["contract_id"],
        filename=doc["filename"],
        status=doc["status"],
        current_stage=doc.get("current_stage"),
        final_risk=doc.get("final_risk"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get(
    "/{contract_id}/status",
    response_model=ContractStatusResponse,
    dependencies=[Depends(require_role("junior_lawyer", "senior_lawyer", "admin"))],
)
async def get_contract_status(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    doc = await contract_repo.get_contract_for_tenant(
        db,
        contract_id,
        current_user["tenant_id"],
    )
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found.")
    return ContractStatusResponse(
        contract_id=doc["contract_id"],
        status=doc["status"],
        current_stage=doc.get("current_stage"),
        progress_percent=doc.get("progress_percent"),
        errors=doc.get("errors", []),
    )


@router.get(
    "/{contract_id}/file",
    dependencies=[Depends(require_role("junior_lawyer", "senior_lawyer", "admin"))],
)
async def get_contract_file(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    doc = await contract_repo.get_contract_for_tenant(
        db,
        contract_id,
        current_user["tenant_id"],
    )
    if not doc:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found.")
    if doc.get("status") == ContractStatus.COMPLETED.value:
        raise HTTPException(status_code=404, detail="Contract file has been removed.")

    filename = doc.get("filename") or ""
    try:
        data = await storage.download_contract(contract_id, filename)
    except Exception as exc:
        logger.warning("contracts.file_download_failed", contract_id=contract_id, error=str(exc))
        raise HTTPException(status_code=404, detail="Contract file unavailable.") from exc

    media_type = (
        "application/pdf"
        if filename.lower().endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return Response(content=data, media_type=media_type)


@router.post(
    "/{contract_id}/complete",
    dependencies=[Depends(require_role("senior_lawyer", "admin"))],
)
async def complete_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Complete a review and remove preview/temp files, without deleting review records."""
    doc = await contract_repo.get_contract_for_tenant(
        db,
        contract_id,
        current_user["tenant_id"],
    )
    if not doc:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found.")

    filename = doc.get("filename") or ""

    # Delete uploaded file from Azure Blob Storage so preview is no longer available.
    if filename:
        try:
            await storage.delete_contract(contract_id, filename)
        except Exception as exc:
            logger.warning("contracts.complete_blob_delete_failed", contract_id=contract_id, error=str(exc))

    # Delete OCR temp text from Azure File Share.
    try:
        from contracts_platform.file_handling.temp_storage import delete_temp_file
        await delete_temp_file(contract_id)
    except Exception as exc:
        logger.warning("contracts.complete_temp_delete_failed", contract_id=contract_id, error=str(exc))

    await contract_repo.update_status(db, contract_id, ContractStatus.COMPLETED, stage="cleanup")

    logger.info("contracts.completed", contract_id=contract_id)
    return {"contract_id": contract_id, "status": "COMPLETED"}


@router.delete(
    "/{contract_id}/data",
    dependencies=[Depends(require_role("senior_lawyer", "admin"))],
)
async def delete_contract_data(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete MongoDB contract + clauses only. Neo4j precedent history is preserved forever."""
    doc = await contract_repo.get_contract_for_tenant(
        db,
        contract_id,
        current_user["tenant_id"],
    )
    if not doc:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found.")

    mongo_deleted = await contract_repo.delete_contract_data(
        db, contract_id, current_user["tenant_id"]
    )
    logger.info(
        "contracts.data_deleted",
        contract_id=contract_id,
        tenant_id=current_user["tenant_id"],
        mongo_deleted=mongo_deleted,
    )
    return {"contract_id": contract_id, "deleted": True, "mongo_deleted": mongo_deleted}


@router.delete(
    "/{contract_id}",
    dependencies=[Depends(require_role("senior_lawyer", "admin"))],
)
async def delete_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Purge one contract from all contract-scoped stores. Playbook data is never touched."""
    doc = await contract_repo.get_contract_for_tenant(
        db,
        contract_id,
        current_user["tenant_id"],
    )
    if not doc:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found.")

    tenant_id = current_user["tenant_id"]
    filename = doc.get("filename") or ""
    clause_docs = await db["clauses"].find(
        {"contract_id": contract_id, "tenant_id": tenant_id},
        {"_id": 0, "clause_id": 1},
    ).to_list(length=None)
    clause_ids = [str(c["clause_id"]) for c in clause_docs if c.get("clause_id")]

    cleanup_errors: list[str] = []

    if filename:
        try:
            await storage.delete_contract(contract_id, filename)
        except Exception as exc:
            cleanup_errors.append("azure_blob")
            logger.warning("contracts.delete_blob_failed", contract_id=contract_id, error=str(exc))

    try:
        from contracts_platform.file_handling.temp_storage import delete_temp_file
        await delete_temp_file(contract_id)
    except Exception as exc:
        cleanup_errors.append("azure_file_share")
        logger.warning("contracts.delete_temp_failed", contract_id=contract_id, error=str(exc))

    try:
        from contracts_platform.db.qdrant.repositories.clause_vector_repo import delete_clauses
        await delete_clauses(tenant_id=tenant_id, clause_ids=clause_ids)
    except Exception as exc:
        cleanup_errors.append("qdrant")
        logger.warning("contracts.delete_qdrant_failed", contract_id=contract_id, error=str(exc))

    try:
        from contracts_platform.db.neo4j.repositories.contract_graph_repo import delete_contract_graph
        await delete_contract_graph(contract_id, tenant_id)
    except Exception as exc:
        cleanup_errors.append("neo4j")
        logger.warning("contracts.delete_neo4j_failed", contract_id=contract_id, error=str(exc))

    mongo_deleted = await contract_repo.delete_contract_data(db, contract_id, tenant_id)

    logger.info(
        "contracts.purged",
        contract_id=contract_id,
        tenant_id=tenant_id,
        clauses=len(clause_ids),
        cleanup_errors=cleanup_errors,
    )
    return {
        "contract_id": contract_id,
        "deleted": True,
        "mongo_deleted": mongo_deleted,
        "qdrant_clause_vectors_requested": len(clause_ids),
        "cleanup_errors": cleanup_errors,
    }


@router.get(
    "/{contract_id}/clauses",
    response_model=list[ClauseResponse],
    dependencies=[Depends(require_role("junior_lawyer", "senior_lawyer", "admin"))],
)
async def list_clauses(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    doc = await contract_repo.get_contract_for_tenant(
        db,
        contract_id,
        current_user["tenant_id"],
    )
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found.")

    cursor = db["clauses"].find(
        {"contract_id": contract_id, "tenant_id": current_user["tenant_id"]},
        {"_id": 0},
    )
    docs = await cursor.to_list(length=500)
    return [
        ClauseResponse(
            clause_id=d["clause_id"],
            clause_type=d["clause_type"],
            raw_text=d["raw_text"],
            start_page=d.get("start_page", 0),
            end_page=d.get("end_page", 0),
            status=d.get("status"),
            risk_category=d.get("risk_category"),
            legal_intent=d.get("legal_intent"),
            gap_summary=d.get("gap_summary"),
            violation_message=d.get("violation_message"),
            precedent=d.get("precedent"),
            ai_recommendation=d.get("ai_recommendation"),
            lawyer_recommendation=d.get("lawyer_recommendation"),
            lawyer_mail_id=d.get("lawyer_mail_id"),
            reviewed_by=d.get("reviewed_by"),
            confidence=d.get("confidence", 0.0),
            parties_mentioned=d.get("parties_mentioned", []),
            tenant_id=d.get("tenant_id"),
        )
        for d in docs
    ]
