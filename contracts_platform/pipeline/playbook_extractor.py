from __future__ import annotations

import json

import openai
import structlog

from contracts_platform.core.config import settings

logger = structlog.get_logger()

_SYSTEM_PROMPT = (
    "You are a senior legal compliance engineer. Your task is to read a company playbook policy "
    "document and extract every enforceable rule it contains as a structured JSON array.\n\n"
    "## Output schema\n\n"
    "Return a JSON array. Every element must have exactly these five keys:\n"
    "- clause_type: one of CONFIDENTIALITY, INDEMNITY, LIABILITY, TERMINATION, GOVERNING_LAW, "
    "DISPUTE_RESOLUTION, FORCE_MAJEURE, PAYMENT, INTELLECTUAL_PROPERTY, NON_COMPETE, "
    "NON_SOLICITATION, WARRANTY\n"
    "- jurisdiction: two-letter or short code (UK, US, IN, EU, AU, SG, etc.)\n"
    "- rule_type: exactly one of REQUIRED, FORBIDDEN, or CONDITIONAL\n"
    "- description: a precise statement of what the rule enforces or prohibits (minimum 15 "
    "characters, written as a complete sentence)\n"
    "- weight: float from 0.0 to 10.0 reflecting commercial importance — use 9.0–10.0 for "
    "unlimited liability or unilateral termination exposure, 7.0–8.9 for significant financial "
    "or IP risk, 5.0–6.9 for standard compliance obligations, 1.0–4.9 for procedural or "
    "low-risk rules\n\n"
    "## Jurisdiction inference rule\n\n"
    "Before extracting any rules, identify the governing law stated in the document. If the "
    "document contains any of: 'England and Wales', 'English law', 'English courts', 'laws of "
    "England', or the £ symbol, set jurisdiction='UK' for every single rule you output. Do not "
    "use 'US' unless the document explicitly states 'United States', 'US law', 'New York law', "
    "or similar US jurisdiction language.\n\n"
    "## Strict extraction rules\n\n"
    "1. Extract one rule per distinct enforceable obligation or prohibition. If a clause contains "
    "a Preferred position, a Fallback position, and a Do Not Accept position, that is three "
    "separate rules (REQUIRED for Preferred, CONDITIONAL for Fallback, FORBIDDEN for Do Not "
    "Accept).\n"
    "2. Deduplication: before finalising your output, check whether any two rules share the same "
    "clause_type AND rule_type. If yes, merge them into a single rule with the more complete "
    "description. Remove the duplicate.\n"
    "3. Do not invent rules that are not stated in the document. Do not add commentary or "
    "explanatory text outside the JSON array.\n"
    "4. Return ONLY a valid JSON array with no markdown, no code fences, and no additional text."
)

# One user/assistant pair covering 3 clause types (CONFIDENTIALITY, LIABILITY, GOVERNING_LAW),
# each with Preferred/Fallback/Do Not Accept positions → 9 rules, jurisdiction UK throughout.
_FEW_SHOT_MESSAGES: list[dict] = [
    {
        "role": "user",
        "content": (
            "ACME LEGAL SERVICES LLP — CONTRACT PLAYBOOK (England and Wales)\n\n"
            "CONFIDENTIALITY\n"
            "Preferred: Mutual confidentiality obligations with a 5-year post-termination tail "
            "and standard carve-outs for information already in the public domain, independently "
            "developed information, and information required to be disclosed by law or court "
            "order.\n"
            "Fallback: Accept a 3-year post-termination tail if counterparty insists, provided "
            "the carve-outs for public domain and legal disclosure are preserved.\n"
            "Do Not Accept: Unilateral confidentiality obligations that bind only ACME Legal "
            "Services LLP without equivalent obligations on the counterparty, or any perpetual "
            "confidentiality obligation with no sunset clause.\n\n"
            "LIABILITY\n"
            "Preferred: Mutual aggregate liability cap of £1,000,000 per contract year, "
            "excluding fraud, death or personal injury caused by negligence, and wilful "
            "misconduct.\n"
            "Fallback: Accept a cap of £500,000 per contract year if deal value is below "
            "£250,000, provided the same exclusions for fraud and personal injury apply.\n"
            "Do Not Accept: Any clause that imposes unlimited liability on ACME Legal Services "
            "LLP, or that excludes the counterparty's liability while preserving ACME's.\n\n"
            "GOVERNING LAW\n"
            "Preferred: English law and exclusive jurisdiction of the courts of England and "
            "Wales.\n"
            "Fallback: English law with non-exclusive jurisdiction if the counterparty is "
            "domiciled outside the UK.\n"
            "Do Not Accept: Any governing law other than English law, or any arbitration clause "
            "that prevents ACME Legal Services LLP from seeking urgent injunctive relief from "
            "the English courts."
        ),
    },
    {
        "role": "assistant",
        "content": json.dumps(
            [
                {
                    "clause_type": "CONFIDENTIALITY",
                    "jurisdiction": "UK",
                    "rule_type": "REQUIRED",
                    "description": (
                        "Confidentiality obligations must be mutual, must include a minimum "
                        "5-year post-termination tail, and must carry standard carve-outs for "
                        "public domain information, independently developed information, and "
                        "legally compelled disclosure."
                    ),
                    "weight": 7.5,
                },
                {
                    "clause_type": "CONFIDENTIALITY",
                    "jurisdiction": "UK",
                    "rule_type": "CONDITIONAL",
                    "description": (
                        "A 3-year post-termination confidentiality tail is acceptable only if "
                        "the counterparty requires it and the carve-outs for public domain "
                        "information and legally compelled disclosure are expressly preserved."
                    ),
                    "weight": 5.5,
                },
                {
                    "clause_type": "CONFIDENTIALITY",
                    "jurisdiction": "UK",
                    "rule_type": "FORBIDDEN",
                    "description": (
                        "Unilateral confidentiality clauses binding only ACME Legal Services "
                        "LLP, and perpetual confidentiality obligations with no sunset clause, "
                        "are not acceptable."
                    ),
                    "weight": 8.5,
                },
                {
                    "clause_type": "LIABILITY",
                    "jurisdiction": "UK",
                    "rule_type": "REQUIRED",
                    "description": (
                        "Aggregate liability must be capped mutually at £1,000,000 per "
                        "contract year, with mandatory exclusions for fraud, death or personal "
                        "injury caused by negligence, and wilful misconduct."
                    ),
                    "weight": 9.0,
                },
                {
                    "clause_type": "LIABILITY",
                    "jurisdiction": "UK",
                    "rule_type": "CONDITIONAL",
                    "description": (
                        "A mutual aggregate liability cap of £500,000 per contract year is "
                        "acceptable where the total contract value is below £250,000, provided "
                        "the exclusions for fraud and personal injury remain in place."
                    ),
                    "weight": 7.0,
                },
                {
                    "clause_type": "LIABILITY",
                    "jurisdiction": "UK",
                    "rule_type": "FORBIDDEN",
                    "description": (
                        "Any clause imposing unlimited liability on ACME Legal Services LLP, "
                        "or any asymmetric cap that excludes the counterparty's liability while "
                        "preserving ACME's, is strictly prohibited."
                    ),
                    "weight": 9.5,
                },
                {
                    "clause_type": "GOVERNING_LAW",
                    "jurisdiction": "UK",
                    "rule_type": "REQUIRED",
                    "description": (
                        "The governing law must be English law with exclusive jurisdiction "
                        "of the courts of England and Wales."
                    ),
                    "weight": 8.0,
                },
                {
                    "clause_type": "GOVERNING_LAW",
                    "jurisdiction": "UK",
                    "rule_type": "CONDITIONAL",
                    "description": (
                        "Non-exclusive jurisdiction of the English courts is acceptable where "
                        "the counterparty is domiciled outside the United Kingdom, provided "
                        "the governing law remains English law."
                    ),
                    "weight": 6.0,
                },
                {
                    "clause_type": "GOVERNING_LAW",
                    "jurisdiction": "UK",
                    "rule_type": "FORBIDDEN",
                    "description": (
                        "Any governing law other than English law is prohibited, as is any "
                        "arbitration clause that prevents ACME Legal Services LLP from "
                        "seeking urgent injunctive relief from the English courts."
                    ),
                    "weight": 8.5,
                },
            ]
        ),
    },
]


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
        messages: list[dict] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            *_FEW_SHOT_MESSAGES,
            {"role": "user", "content": text},
        ]
        response = await oai.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
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