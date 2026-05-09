import json

from openai import AsyncOpenAI

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger
from contracts_platform.pipeline import cost_tracker
from contracts_platform.pipeline.clause_extraction import fallback_parser, validator

_SYSTEM_PROMPT = """You are a senior legal analyst performing exhaustive contract clause extraction. \
Your primary obligation is completeness — you must not stop early and must not skip any section.

## Extraction procedure (follow in order)

Step 1: Read the full contract text from beginning to end and list every numbered or lettered \
section heading you can identify (e.g. "1. Confidentiality", "3.2 Limitation of Liability", \
"Schedule A — Governing Law"). Write this list mentally before producing any output.

Step 2: For each heading identified in Step 1, extract exactly one clause object. Do not merge \
multiple headings into one clause object unless they share a single contiguous block of text with \
no intervening heading.

Step 3 — Completeness check: After completing your extraction, count the clauses you have produced. \
If you found fewer than 6 clauses in what appears to be a standard commercial NDA, service \
agreement, or supply contract, you have almost certainly missed sections. Re-read the contract \
from the beginning and add any missed clauses before finalising output.

## Field definitions

- clause_id: generate a fresh UUID v4 string for every clause.
- clause_type: classify as exactly one of: CONFIDENTIALITY, INDEMNITY, LIABILITY, TERMINATION, \
GOVERNING_LAW, DISPUTE_RESOLUTION, FORCE_MAJEURE, PAYMENT, INTELLECTUAL_PROPERTY, NON_COMPETE, \
NON_SOLICITATION, WARRANTY. If no type fits, omit the clause entirely rather than guessing.
- raw_text: verbatim text copied from the document. Never paraphrase, summarise, or truncate.
- start_page: 1-indexed integer page on which the clause begins.
- end_page: 1-indexed integer page on which the clause ends (equal to start_page if single-page).
- parties_mentioned: list of full legal entity names (e.g. "Acme Corporation Ltd") explicitly \
named in this clause. Empty list [] if none appear.
- key_dates: ISO 8601 dates (YYYY-MM-DD) that are explicitly stated in the clause text. Empty \
list [] if none.
- key_obligations: every sentence in the clause that contains the words shall, must, agrees to, \
is required to, or undertakes to. Include the full sentence. One sentence per list element.
- risk_indicators: every sentence in the clause that contains the words terminate, breach, \
penalty, liable, indemnify, unlimited, perpetual, waive, no limitation, or damages. Include the \
full sentence. One sentence per list element.
- confidence: float.
  - 0.97–1.00 for clauses anchored to an explicit numbered section heading.
  - 0.80–0.96 for clauses inferred from content without a clear heading.
  - below 0.80 for ambiguous fragments where the clause type is uncertain.

## Output format

Return a JSON object with a single key "clauses" whose value is an array of clause objects. \
Every field listed above must be present in every object; use empty lists for list fields when \
there is nothing to populate. Do not include any text outside the JSON object."""

_CLAUSE_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "clauses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "clause_id": {"type": "string"},
                    "clause_type": {
                        "type": "string",
                        "enum": [
                            "CONFIDENTIALITY",
                            "INDEMNITY",
                            "LIABILITY",
                            "TERMINATION",
                            "GOVERNING_LAW",
                            "DISPUTE_RESOLUTION",
                            "FORCE_MAJEURE",
                            "PAYMENT",
                            "INTELLECTUAL_PROPERTY",
                            "NON_COMPETE",
                            "NON_SOLICITATION",
                            "WARRANTY",
                        ],
                    },
                    "raw_text": {"type": "string"},
                    "start_page": {"type": "integer"},
                    "end_page": {"type": "integer"},
                    "parties_mentioned": {"type": "array", "items": {"type": "string"}},
                    "key_dates": {"type": "array", "items": {"type": "string"}},
                    "key_obligations": {"type": "array", "items": {"type": "string"}},
                    "risk_indicators": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
                "required": [
                    "clause_id",
                    "clause_type",
                    "raw_text",
                    "start_page",
                    "end_page",
                    "parties_mentioned",
                    "key_dates",
                    "key_obligations",
                    "risk_indicators",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["clauses"],
    "additionalProperties": False,
}

# One user/assistant pair demonstrating a 3-section NDA excerpt producing 3 clause objects.
# All fields are populated, including non-empty key_obligations and risk_indicators.
_FEW_SHOT_MESSAGES: list[dict] = [
    {
        "role": "user",
        "content": (
            "Extract all clauses from the following contract text:\n\n"
            "MUTUAL NON-DISCLOSURE AGREEMENT\n\n"
            "1. Confidential Information\n"
            "Each party (the 'Receiving Party') agrees to hold in strict confidence all "
            "Confidential Information disclosed by the other party (the 'Disclosing Party') and "
            "shall not disclose such information to any third party without prior written consent "
            "of the Disclosing Party. This obligation shall not apply to information that is "
            "independently developed by the Receiving Party without use of the Confidential "
            "Information, or that is or becomes publicly available through no fault of the "
            "Receiving Party. GlobalTech Solutions Ltd and Meridian Advisory Partners LLP are "
            "each bound by this clause.\n\n"
            "2. Term and Termination\n"
            "This Agreement shall commence on 2024-03-01 and shall continue for a period of two "
            "(2) years unless terminated earlier by either party upon thirty (30) days written "
            "notice. Upon termination or expiry, each party must return or destroy all "
            "Confidential Information in its possession within fourteen (14) days. A party may "
            "terminate this Agreement immediately upon written notice if the other party commits "
            "a material breach of any obligation under this Agreement.\n\n"
            "3. Limitation of Liability\n"
            "Meridian Advisory Partners LLP's aggregate liability to GlobalTech Solutions Ltd "
            "under or in connection with this Agreement shall not exceed £500,000 (five hundred "
            "thousand pounds sterling) in any twelve-month period. Neither party shall be liable "
            "to the other for any indirect, consequential, or punitive damages arising from a "
            "breach of this Agreement. Each party acknowledges that damages alone may not be an "
            "adequate remedy for breach of this clause and that injunctive relief may be sought."
        ),
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "clauses": [
                    {
                        "clause_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "clause_type": "CONFIDENTIALITY",
                        "raw_text": (
                            "Each party (the 'Receiving Party') agrees to hold in strict "
                            "confidence all Confidential Information disclosed by the other "
                            "party (the 'Disclosing Party') and shall not disclose such "
                            "information to any third party without prior written consent of "
                            "the Disclosing Party. This obligation shall not apply to "
                            "information that is independently developed by the Receiving Party "
                            "without use of the Confidential Information, or that is or becomes "
                            "publicly available through no fault of the Receiving Party. "
                            "GlobalTech Solutions Ltd and Meridian Advisory Partners LLP are "
                            "each bound by this clause."
                        ),
                        "start_page": 1,
                        "end_page": 1,
                        "parties_mentioned": [
                            "GlobalTech Solutions Ltd",
                            "Meridian Advisory Partners LLP",
                        ],
                        "key_dates": [],
                        "key_obligations": [
                            "Each party (the 'Receiving Party') agrees to hold in strict "
                            "confidence all Confidential Information disclosed by the other "
                            "party (the 'Disclosing Party') and shall not disclose such "
                            "information to any third party without prior written consent of "
                            "the Disclosing Party."
                        ],
                        "risk_indicators": [],
                        "confidence": 0.98,
                    },
                    {
                        "clause_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                        "clause_type": "TERMINATION",
                        "raw_text": (
                            "This Agreement shall commence on 2024-03-01 and shall continue "
                            "for a period of two (2) years unless terminated earlier by either "
                            "party upon thirty (30) days written notice. Upon termination or "
                            "expiry, each party must return or destroy all Confidential "
                            "Information in its possession within fourteen (14) days. A party "
                            "may terminate this Agreement immediately upon written notice if "
                            "the other party commits a material breach of any obligation under "
                            "this Agreement."
                        ),
                        "start_page": 1,
                        "end_page": 1,
                        "parties_mentioned": [],
                        "key_dates": ["2024-03-01"],
                        "key_obligations": [
                            "Upon termination or expiry, each party must return or destroy all "
                            "Confidential Information in its possession within fourteen (14) days."
                        ],
                        "risk_indicators": [
                            "A party may terminate this Agreement immediately upon written "
                            "notice if the other party commits a material breach of any "
                            "obligation under this Agreement."
                        ],
                        "confidence": 0.98,
                    },
                    {
                        "clause_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                        "clause_type": "LIABILITY",
                        "raw_text": (
                            "Meridian Advisory Partners LLP's aggregate liability to GlobalTech "
                            "Solutions Ltd under or in connection with this Agreement shall not "
                            "exceed £500,000 (five hundred thousand pounds sterling) in any "
                            "twelve-month period. Neither party shall be liable to the other "
                            "for any indirect, consequential, or punitive damages arising from "
                            "a breach of this Agreement. Each party acknowledges that damages "
                            "alone may not be an adequate remedy for breach of this clause and "
                            "that injunctive relief may be sought."
                        ),
                        "start_page": 1,
                        "end_page": 1,
                        "parties_mentioned": [
                            "Meridian Advisory Partners LLP",
                            "GlobalTech Solutions Ltd",
                        ],
                        "key_dates": [],
                        "key_obligations": [
                            "Meridian Advisory Partners LLP's aggregate liability to GlobalTech "
                            "Solutions Ltd under or in connection with this Agreement shall not "
                            "exceed £500,000 (five hundred thousand pounds sterling) in any "
                            "twelve-month period."
                        ],
                        "risk_indicators": [
                            "Neither party shall be liable to the other for any indirect, "
                            "consequential, or punitive damages arising from a breach of this "
                            "Agreement."
                        ],
                        "confidence": 0.98,
                    },
                ]
            }
        ),
    },
]


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Rough USD cost estimate. Update pricing as needed."""
    pricing = {
        "gpt-4o": {"prompt": 2.50, "completion": 10.00},
        "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    }
    rates = pricing.get(model, {"prompt": 2.50, "completion": 10.00})
    return (prompt_tokens * rates["prompt"] + completion_tokens * rates["completion"]) / 1_000_000


async def extract_clauses(contract_id: str, text: str) -> list[dict]:
    """
    Main clause extraction entry point called by clause_extraction_task.

    1. Builds an OpenAI prompt requesting a JSON array of clause objects using
       json_schema structured output mode (strict field enforcement).
    2. Parses the JSON response.
    3. Validates each clause with ExtractedClause; falls back to regex parser on failure.
    4. Records LLM cost via cost_tracker.
    5. Returns list of clause dicts — never raises even on per-clause errors.
    """
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    model = settings.LLM_MODEL

    logger.info("clause_extractor.start", contract_id=contract_id, text_length=len(text))

    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        *_FEW_SHOT_MESSAGES,
        {
            "role": "user",
            "content": f"Extract all clauses from the following contract text:\n\n{text}",
        },
    ]

    response = await client.chat.completions.create(
        model=model,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "ContractClauses",
                "strict": True,
                "schema": _CLAUSE_JSON_SCHEMA,
            },
        },
        messages=messages,
    )

    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    cost_usd = _estimate_cost(model, prompt_tokens, completion_tokens)

    await cost_tracker.record_llm_call(
        contract_id=contract_id,
        task_name="clause_extraction",
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
    )

    raw_content = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw_content)
        raw_clauses: list[dict] = parsed.get("clauses", [])
    except json.JSONDecodeError as exc:
        logger.error(
            "clause_extractor.json_parse_failed",
            contract_id=contract_id,
            error=str(exc),
        )
        raw_clauses = []

    result: list[dict] = []
    for idx, raw in enumerate(raw_clauses):
        try:
            clause = validator.validate_clause(raw)
            if clause is not None:
                result.append(clause.model_dump(mode="json"))
            else:
                # LLM gave something but it failed Pydantic — use regex fallback
                raw_text = raw.get("raw_text", "")
                page_num = raw.get("start_page", 1)
                fallback = fallback_parser.parse_clause(contract_id, raw_text, page_num)
                # Preserve clause_type from LLM output if available
                if "clause_type" in raw:
                    fallback["clause_type"] = raw["clause_type"]
                result.append(fallback)
                logger.info(
                    "clause_extractor.fallback_used",
                    contract_id=contract_id,
                    clause_index=idx,
                )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "clause_extractor.clause_error",
                contract_id=contract_id,
                clause_index=idx,
                error=str(exc),
            )

    logger.info(
        "clause_extractor.complete",
        contract_id=contract_id,
        clauses_extracted=len(result),
    )
    return result