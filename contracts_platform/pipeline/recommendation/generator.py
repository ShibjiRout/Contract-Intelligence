import json

from openai import AsyncOpenAI

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger
from contracts_platform.pipeline import cost_tracker

_SYSTEM_PROMPT = """You are a senior legal contract review specialist.
Given a risky contract clause and accepted wording examples from similar contracts,
provide a structured review with the following JSON keys:
- recommendation: a clear explanation of the risk and what should be changed
- suggested_fix: a rewritten version of the clause that removes or mitigates the risk
- alternative_fixes: a list of 1-3 alternative rewordings (may be empty if only one fix applies)

Respond only with valid JSON.
"""


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = {
        "gpt-4o": {"prompt": 2.50, "completion": 10.00},
        "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    }
    rates = pricing.get(model, {"prompt": 2.50, "completion": 10.00})
    return (prompt_tokens * rates["prompt"] + completion_tokens * rates["completion"]) / 1_000_000


async def generate_recommendation(
    clause_text: str,
    clause_type: str,
    risk_indicators: list[str],
    accepted_examples: list[dict],
) -> dict:
    """
    Generate a recommendation and suggested fix for a risky clause.

    Uses accepted_examples (from wording_retriever) as few-shot context.
    Records LLM cost via cost_tracker.
    Returns {"recommendation": str, "suggested_fix": str, "alternative_fixes": list[str]}.
    """
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    model = settings.LLM_MODEL

    examples_text = ""
    if accepted_examples:
        lines = [f"  {i + 1}. {ex['text']}" for i, ex in enumerate(accepted_examples)]
        examples_text = "Accepted wording examples from similar contracts:\n" + "\n".join(lines)

    user_message = (
        f"Clause type: {clause_type}\n\n"
        f"Clause text:\n{clause_text}\n\n"
        f"Risk indicators identified:\n- " + "\n- ".join(risk_indicators or ["(none)"]) + "\n\n"
        + (examples_text if examples_text else "No accepted examples available.")
    )

    response = await client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    cost_usd = _estimate_cost(model, prompt_tokens, completion_tokens)

    # We don't have a contract_id here; use clause_type as a proxy identifier
    await cost_tracker.record_llm_call(
        contract_id=f"recommendation:{clause_type}",
        task_name="generate_recommendation",
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
    )

    raw = response.choices[0].message.content or "{}"
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("generator.json_parse_failed", error=str(exc), clause_type=clause_type)
        result = {}

    return {
        "recommendation": result.get("recommendation", ""),
        "suggested_fix": result.get("suggested_fix", ""),
        "alternative_fixes": result.get("alternative_fixes", []),
    }
