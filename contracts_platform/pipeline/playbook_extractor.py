from __future__ import annotations

import json

import openai
import structlog

from contracts_platform.core.config import settings

logger = structlog.get_logger()

_SYSTEM_PROMPT = (
    "You are a legal compliance expert. Extract all company playbook rules from the following "
    "policy document. Return a JSON array of rules, each with: "
    "clause_type (one of: CONFIDENTIALITY, INDEMNITY, LIABILITY, TERMINATION, GOVERNING_LAW, "
    "DISPUTE_RESOLUTION, FORCE_MAJEURE, PAYMENT, INTELLECTUAL_PROPERTY, NON_COMPETE, "
    "NON_SOLICITATION, WARRANTY), "
    "jurisdiction (e.g. US, UK, IN, EU), "
    "rule_type (REQUIRED, FORBIDDEN, or CONDITIONAL), "
    "description (what the rule enforces, min 10 chars), "
    "weight (float 0.0-10.0, default 1.0). "
    "Return ONLY a valid JSON array with no additional text or markdown."
)


async def extract_playbook_rules_from_text(text: str) -> list[dict]:
    """
    Call OpenAI GPT-4o to extract playbook rules from policy document text.

    Returns a list of rule dicts, each containing:
    - clause_type: str
    - jurisdiction: str
    - rule_type: str
    - description: str
    - weight: float

    On JSON decode errors, logs the error and returns an empty list.
    """
    try:
        oai = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await oai.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
        )
        raw = response.choices[0].message.content or ""
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
            if raw.endswith("```"):
                raw = raw[:-3].strip()

        rules: list[dict] = json.loads(raw)
        if not isinstance(rules, list):
            logger.warning("playbook_extractor.unexpected_shape", type=type(rules).__name__)
            return []
        logger.info("playbook_extractor.rules_extracted", count=len(rules))
        return rules
    except json.JSONDecodeError as exc:
        logger.error("playbook_extractor.json_decode_error", error=str(exc))
        return []
    except Exception as exc:
        logger.error("playbook_extractor.llm_error", error=str(exc))
        return []
