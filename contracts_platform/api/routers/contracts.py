from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile

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

router = APIRouter(prefix="/contracts", tags=["contracts"])
logger = structlog.get_logger()


@router.post(
    "/upload",
    response_model=ContractUploadResponse,
    dependencies=[Depends(require_role("junior_lawyer", "senior_lawyer", "admin"))],
)
async def upload_contract(
    file: UploadFile,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    file_bytes = await file.read()

    validate_upload(file_bytes, file.filename or "", file.content_type or "")

    # Duplicate detection via SHA-256
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing = await contract_repo.get_by_file_hash(db, file_hash)
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
        "user_id": current_user["sub"],
        "tenant_id": current_user["tenant_id"],
        "errors": [],
        "created_at": now,
        "updated_at": now,
    }
    await contract_repo.create_contract(db, doc)

    await storage.upload_contract(contract_id, file_bytes, file.filename or "")

    # Dispatch ingest task
    try:
        from contracts_platform.workers.tasks import ingest_task  # type: ignore

        b64 = base64.b64encode(file_bytes).decode()
        ingest_task.apply_async(
            args=[contract_id, b64, file.filename, current_user["sub"], current_user["tenant_id"]],
            queue="ingest",
        )
    except Exception as exc:
        logger.warning("contracts.dispatch_failed", contract_id=contract_id, error=str(exc))

    logger.info("contracts.uploaded", contract_id=contract_id, user_id=current_user["sub"])
    return ContractUploadResponse(
        contract_id=contract_id,
        status=ContractStatus.UPLOADED.value,
        message="Contract uploaded successfully and queued for processing.",
    )


@router.get(
    "/{contract_id}",
    response_model=ContractDetailResponse,
    dependencies=[Depends(require_role("junior_lawyer", "senior_lawyer", "admin"))],
)
async def get_contract(contract_id: str, db=Depends(get_db)):
    doc = await contract_repo.get_contract(db, contract_id)
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
async def get_contract_status(contract_id: str, db=Depends(get_db)):
    doc = await contract_repo.get_contract(db, contract_id)
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
    "/{contract_id}/clauses",
    response_model=list[ClauseResponse],
    dependencies=[Depends(require_role("junior_lawyer", "senior_lawyer", "admin"))],
)
async def list_clauses(contract_id: str, db=Depends(get_db)):
    cursor = db["clauses"].find({"contract_id": contract_id}, {"_id": 0})
    docs = await cursor.to_list(length=500)
    return [
        ClauseResponse(
            clause_id=d["clause_id"],
            clause_type=d["clause_type"],
            raw_text=d["raw_text"],
            start_page=d["start_page"],
            end_page=d["end_page"],
            risk_level=d.get("risk_level"),
            recommendation=d.get("recommendation"),
            suggested_fix=d.get("suggested_fix"),
            confidence=d.get("confidence", 0.0),
        )
        for d in docs
    ]
