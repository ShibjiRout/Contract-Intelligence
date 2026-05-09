import json

from openai import AsyncOpenAI

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger
from contracts_platform.pipeline import cost_tracker
from contracts_platform.pipeline.clause_extraction import fallback_parser, validator

_SYSTEM_PROMPT = """You are a legal contract analysis assistant.
Extract all clauses from the provided contract text and return them as a JSON object
with a single key "clauses" whose value is an array of clause objects.

Each clause object must have:
- clause_id: a UUID v4 string
- clause_type: one of CONFIDENTIALITY, INDEMNITY, LIABILITY, TERMINATION, GOVERNING_LAW,
  DISPUTE_RESOLUTION, FORCE_MAJEURE, PAYMENT, INTELLECTUAL_PROPERTY, NON_COMPETE,
  NON_SOLICITATION, WARRANTY
- raw_text: the exact verbatim clause text
- start_page: integer page number where the clause starts
- end_page: integer page number where the clause ends
- parties_mentioned: list of party/entity names mentioned in the clause
- key_dates: list of dates in ISO format (YYYY-MM-DD)
- key_obligations: list of obligation sentences (containing shall/must/agrees to)
- risk_indicators: list of risk sentences (containing terminate/breach/penalty/liable)
- confidence: float between 0.0 and 1.0 representing extraction confidence
"""


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

    1. Builds an OpenAI prompt requesting a JSON array of clause objects.
    2. Parses the JSON response.
    3. Validates each clause with ExtractedClause; falls back to regex parser on failure.
    4. Records LLM cost via cost_tracker.
    5. Returns list of clause dicts — never raises even on per-clause errors.
    """
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    model = settings.LLM_MODEL

    logger.info("clause_extractor.start", contract_id=contract_id, text_length=len(text))

    response = await client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Extract all clauses from the following contract text:\n\n{text}",
            },
        ],
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
