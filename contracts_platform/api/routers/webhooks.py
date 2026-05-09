from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from contracts_platform.api.dependencies import get_db
from contracts_platform.auth.api_key_manager import validate_api_key

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = structlog.get_logger()


async def _require_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db=Depends(get_db),
) -> dict:
    key_doc = await validate_api_key(db, x_api_key)
    if key_doc is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return key_doc


@router.post("/contract-decision", dependencies=[Depends(_require_api_key)])
async def contract_decision_webhook(request: Request):
    """Stub endpoint for external contract-decision webhook events."""
    body = await request.json()
    logger.info(
        "webhook.contract_decision_received",
        content_type=request.headers.get("content-type"),
        keys=list(body.keys()) if isinstance(body, dict) else None,
    )
    return {"status": "received", "detail": "Webhook event logged successfully."}
