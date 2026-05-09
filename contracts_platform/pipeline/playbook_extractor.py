from __future__ import annotations

import asyncio
import json
import re
from typing import Literal

import openai
import structlog
from pydantic import BaseModel, Field

from contracts_platform.core.config import settings

logger = structlog.get_logger()


class ClauseRule(BaseModel):
    clause_type: Literal[
        "CONFIDENTIALITY", "INDEMNITY", "LIABILITY", "TERMINATION",
        "GOVERNING_LAW", "DISPUTE_RESOLUTION", "FORCE_MAJEURE",
        "PAYMENT", "INTELLECTUAL_PROPERTY", "NON_COMPETE",
        "NON_SOLICITATION", "WARRANTY",
    ]
    jurisdiction: str = Field(description="Inferred from document. Use 'UK' for England/Wales references, else 'US'.")
    rule_type: Literal["REQUIRED", "FORBIDDEN", "CONDITIONAL"]
    description: str = Field(min_length=15)
    weight: float = Field(ge=0.0, le=10.0)


class PlaybookExtraction(BaseModel):
    rules: list[ClauseRule]


_SYSTEM_PROMPT = (
    "You are a senior legal compliance engineer. Your task is to read the provided clause text "
    "and extract EVERY enforceable rule it contains. DO NOT STOP early. Process the entire text "
    "from start to finish before producing output.\n\n"
    "## SKIP — return {\"rules\": []} ONLY if the entire text contains nothing but:\n"
    "- APPROVAL AUTHORITY tables\n"
    "- PURPOSE AND SCOPE / HOW TO USE THIS PLAYBOOK\n"
    "- MISSING CLAUSES / ESCALATION CONTACTS / VERSION HISTORY\n"
    "- Cover pages, disclaimers, or table-of-contents\n\n"
    "## Extract a rule for EACH of: Preferred position, Fallback position, Do not accept position.\n\n"
    "## Clause type mapping\n"
    "- Definition of Confidential Information → CONFIDENTIALITY\n"
    "- Permitted Disclosures → CONFIDENTIALITY\n"
    "- Obligations of the Receiving Party → CONFIDENTIALITY\n"
    "- Purpose of Disclosure → CONFIDENTIALITY\n"
    "- Survival of Confidentiality Obligations → TERMINATION\n"
    "- Return or Destruction of Information → TERMINATION\n"
    "- Term of Agreement → TERMINATION\n"
    "- Liability / Limitation of Liability → LIABILITY\n"
    "- Governing Law / Jurisdiction → GOVERNING_LAW\n"
    "- Injunctive Relief / Dispute Resolution → DISPUTE_RESOLUTION\n\n"
    "## rule_type mapping\n"
    "- Preferred position → REQUIRED\n"
    "- Fallback position → CONDITIONAL\n"
    "- Do not accept position → FORBIDDEN\n\n"
    "## Weight guide\n"
    "9.0–10.0: unlimited liability or unilateral termination exposure\n"
    "7.0–8.9: significant financial or IP risk\n"
    "5.0–6.9: standard compliance obligations\n"
    "1.0–4.9: procedural or low-risk rules\n\n"
    "## Jurisdiction\n"
    "If text contains 'England and Wales', 'English law', 'English courts', or £ symbol → jurisdiction='UK'. "
    "Do not use 'US' unless explicitly stated."
)

_FEW_SHOT_MESSAGES: list[dict] = [
    {
        "role": "user",
        "content": (
            "ACME LEGAL SERVICES LLP — CONTRACT PLAYBOOK (England and Wales)\n\n"
            "CLAUSE 1 — CONFIDENTIALITY\n"
            "Preferred: Mutual confidentiality obligations with a 5-year post-termination tail "
            "and standard carve-outs for public domain, independently developed, and legally compelled disclosure.\n"
            "Fallback: Accept a 3-year post-termination tail if counterparty insists, provided "
            "the carve-outs for public domain and legal disclosure are preserved.\n"
            "Do Not Accept: Unilateral confidentiality obligations binding only ACME Legal "
            "Services LLP, or any perpetual confidentiality obligation with no sunset clause.\n\n"
            "CLAUSE 2 — LIABILITY\n"
            "Preferred: Mutual aggregate liability cap of £1,000,000 per contract year, "
            "excluding fraud, death or personal injury, and wilful misconduct.\n"
            "Fallback: Accept £500,000 per contract year if deal value is below £250,000, "
            "provided the same exclusions apply.\n"
            "Do Not Accept: Any clause imposing unlimited liability on ACME Legal Services LLP."
        ),
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "rules": [
                {
                    "clause_type": "CONFIDENTIALITY",
                    "jurisdiction": "UK",
                    "rule_type": "REQUIRED",
                    "description": (
                        "Confidentiality obligations must be mutual with a minimum 5-year "
                        "post-termination tail and carve-outs for public domain, independently "
                        "developed, and legally compelled disclosure."
                    ),
                    "weight": 7.5,
                },
                {
                    "clause_type": "CONFIDENTIALITY",
                    "jurisdiction": "UK",
                    "rule_type": "CONDITIONAL",
                    "description": (
                        "A 3-year post-termination tail is acceptable only if the counterparty "
                        "requires it and public domain and legal disclosure carve-outs are preserved."
                    ),
                    "weight": 5.5,
                },
                {
                    "clause_type": "CONFIDENTIALITY",
                    "jurisdiction": "UK",
                    "rule_type": "FORBIDDEN",
                    "description": (
                        "Unilateral confidentiality clauses binding only ACME Legal Services LLP "
                        "and perpetual confidentiality obligations with no sunset clause are prohibited."
                    ),
                    "weight": 8.5,
                },
                {
                    "clause_type": "LIABILITY",
                    "jurisdiction": "UK",
                    "rule_type": "REQUIRED",
                    "description": (
                        "Aggregate liability must be capped mutually at £1,000,000 per contract year "
                        "with mandatory exclusions for fraud, death or personal injury, and wilful misconduct."
                    ),
                    "weight": 9.0,
                },
                {
                    "clause_type": "LIABILITY",
                    "jurisdiction": "UK",
                    "rule_type": "CONDITIONAL",
                    "description": (
                        "A mutual aggregate liability cap of £500,000 per contract year is acceptable "
                        "where the total contract value is below £250,000 and the same exclusions remain."
                    ),
                    "weight": 7.0,
                },
                {
                    "clause_type": "LIABILITY",
                    "jurisdiction": "UK",
                    "rule_type": "FORBIDDEN",
                    "description": (
                        "Any clause imposing unlimited liability on ACME Legal Services LLP is strictly prohibited."
                    ),
                    "weight": 9.5,
                },
            ]
        }),
    },
]


async def extract_playbook_rules_from_text(text: str) -> list[dict]:
    """
    Call OpenAI GPT-4o with structured output (Pydantic) to extract playbook rules.

    Returns a list of rule dicts with keys:
    clause_type, jurisdiction, rule_type, description, weight
    """
    try:
        oai = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        messages: list[dict] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            *_FEW_SHOT_MESSAGES,
            {"role": "user", "content": text},
        ]
        response = await oai.beta.chat.completions.parse(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=0.0,
            response_format=PlaybookExtraction,
        )
        extraction = response.choices[0].message.parsed
        if not extraction or not extraction.rules:
            return []
        logger.info("playbook_extractor.rules_extracted", count=len(extraction.rules))
        return [rule.model_dump() for rule in extraction.rules]
    except openai.BadRequestError as exc:
        logger.error("playbook_extractor.bad_request", error=str(exc))
        return []
    except Exception as exc:
        logger.error("playbook_extractor.llm_error", error=str(exc), exc_type=type(exc).__name__)
        return []


_MAX_CONCURRENT = 3


async def process_entire_playbook(pages: list[dict]) -> list[dict]:
    """
    Extract rules from each page concurrently using Pydantic structured output.
    Azure DI page splits are reliable — no regex needed.
    """
    valid_pages = [p for p in pages if len(p.get("text", "").strip()) > 50]
    logger.info("playbook_extractor.pages_to_process", total=len(valid_pages))

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    async def _extract_page(page: dict) -> list[dict]:
        async with semaphore:
            page_num = page.get("heading", page.get("page_num", "?"))
            rules = await extract_playbook_rules_from_text(page["text"])
            logger.info("playbook_extractor.page_done", page_num=page_num, rules=len(rules))
            return rules

    results = await asyncio.gather(
        *[_extract_page(p) for p in valid_pages],
        return_exceptions=True,
    )

    all_rules: list[dict] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("playbook_extractor.page_failed", page_index=i, error=str(result), exc_type=type(result).__name__)
            continue
        all_rules.extend(result)

    logger.info("playbook_extractor.processing_complete", total_rules=len(all_rules))
    return all_rules
