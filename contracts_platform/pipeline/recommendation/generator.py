import json

from openai import AsyncOpenAI

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger
from contracts_platform.pipeline import cost_tracker

_SYSTEM_PROMPT = """You are a senior commercial solicitor specialising in contract risk review. \
Given a risky contract clause, the playbook rule it violates, and accepted wording examples from \
approved past contracts, you must produce a structured JSON review with exactly three keys: \
recommendation, suggested_fix, and alternative_fixes.

## recommendation

Must do all three of the following in order:
1. Quote the exact problematic phrase from the clause text in double quotation marks — do not \
paraphrase it.
2. State precisely which playbook standard is violated, using the specific rule or threshold from \
the input (e.g. "This violates the requirement for a mutual £500,000 aggregate liability cap" or \
"This violates the requirement that governing law be English law with exclusive English \
jurisdiction").
3. State in one sentence exactly what must change to bring the clause into compliance.

## suggested_fix

Must be a complete, ready-to-paste legal English rewrite of the clause. Requirements:
- Use the actual party names found in the clause text if they are identifiable — do not use \
placeholders such as [PARTY A] or [COMPANY].
- Incorporate all necessary carve-outs that are standard for the clause type (e.g. fraud, \
personal injury, and wilful misconduct for liability caps; public domain and legally compelled \
disclosure for confidentiality).
- The rewrite must be self-contained: a lawyer must be able to paste it into the contract \
without editing.
- Prefer the style and phrasing of the accepted wording examples provided — do not invent \
new formulations when an accepted example covers the same ground.

## alternative_fixes

A JSON array of between 1 and 3 complete alternative rewritten sentences. Each element must be \
a full legal sentence ready to insert into a contract — not a description of what to change, \
not a bullet point summary. Minimum 1 alternative is required even if you believe the \
suggested_fix is optimal.

Respond only with valid JSON containing exactly the three keys above."""

# Few-shot pair 1 — GOVERNING_LAW: foreign jurisdiction → English law redline
_FEW_SHOT_GOVERNING_LAW_USER = (
    "Clause type: GOVERNING_LAW\n\n"
    "Clause text:\n"
    "This Agreement shall be governed by and construed in accordance with the laws of the State "
    "of Delaware, United States of America. Any dispute arising under or in connection with this "
    "Agreement shall be subject to the exclusive jurisdiction of the courts of Delaware.\n\n"
    "Risk indicators identified:\n"
    "- This Agreement shall be governed by and construed in accordance with the laws of the "
    "State of Delaware, United States of America.\n\n"
    "Playbook rule violated: Governing law must be English law with exclusive jurisdiction of "
    "the courts of England and Wales. US governing law is expressly forbidden.\n\n"
    "Accepted wording examples from similar contracts:\n"
    "1. This Agreement and any dispute or claim (including non-contractual disputes or claims) "
    "arising out of or in connection with it or its subject matter or formation shall be governed "
    "by and construed in accordance with the law of England and Wales.\n"
    "2. Each party irrevocably agrees that the courts of England and Wales shall have exclusive "
    "jurisdiction to settle any dispute or claim arising out of or in connection with this "
    "Agreement."
)

_FEW_SHOT_GOVERNING_LAW_ASSISTANT = json.dumps(
    {
        "recommendation": (
            'The phrase "governed by and construed in accordance with the laws of the State of '
            'Delaware, United States of America" violates the playbook requirement that all '
            "agreements be subject to English law with exclusive jurisdiction of the courts of "
            "England and Wales. The governing law and jurisdiction clause must be replaced in "
            "full with English law and exclusive English court jurisdiction."
        ),
        "suggested_fix": (
            "This Agreement and any dispute or claim (including non-contractual disputes or "
            "claims) arising out of or in connection with it or its subject matter or formation "
            "shall be governed by and construed in accordance with the law of England and Wales. "
            "Each party irrevocably agrees that the courts of England and Wales shall have "
            "exclusive jurisdiction to settle any dispute or claim arising out of or in "
            "connection with this Agreement or its formation."
        ),
        "alternative_fixes": [
            "This Agreement shall be governed by English law. The parties submit to the "
            "exclusive jurisdiction of the courts of England and Wales in respect of any "
            "dispute or claim arising under or in connection with this Agreement, including "
            "non-contractual disputes.",
            "This Agreement is governed by the laws of England and Wales. Any dispute "
            "relating to this Agreement shall be resolved exclusively by the courts of "
            "England and Wales, and each party waives any objection to proceedings in those "
            "courts on the grounds of inconvenient forum.",
        ],
    }
)

# Few-shot pair 2 — LIABILITY: unlimited liability → specific £500k cap redline
_FEW_SHOT_LIABILITY_USER = (
    "Clause type: LIABILITY\n\n"
    "Clause text:\n"
    "Notwithstanding any other provision of this Agreement, Meridian Data Systems Limited shall "
    "be liable to FinServ Holdings PLC for any and all losses, damages, costs and expenses of "
    "whatever nature suffered or incurred by FinServ Holdings PLC arising out of or in "
    "connection with any breach of this Agreement by Meridian Data Systems Limited, without "
    "limitation.\n\n"
    "Risk indicators identified:\n"
    "- Meridian Data Systems Limited shall be liable to FinServ Holdings PLC for any and all "
    "losses, damages, costs and expenses of whatever nature suffered or incurred by FinServ "
    "Holdings PLC arising out of or in connection with any breach of this Agreement by Meridian "
    "Data Systems Limited, without limitation.\n\n"
    "Playbook rule violated: Aggregate liability must be capped mutually at £500,000 per "
    "contract year with exclusions for fraud, death or personal injury caused by negligence, "
    "and wilful misconduct. Unlimited liability clauses are expressly forbidden.\n\n"
    "Accepted wording examples from similar contracts:\n"
    "1. The aggregate liability of either party to the other under or in connection with this "
    "Agreement, whether in contract, tort (including negligence) or otherwise, shall not exceed "
    "£500,000 in any twelve-month period.\n"
    "2. Neither party excludes liability for fraud, death or personal injury caused by its "
    "negligence, or wilful misconduct."
)

_FEW_SHOT_LIABILITY_ASSISTANT = json.dumps(
    {
        "recommendation": (
            'The phrase "liable to FinServ Holdings PLC for any and all losses, damages, costs '
            'and expenses of whatever nature suffered or incurred by FinServ Holdings PLC '
            'arising out of or in connection with any breach of this Agreement by Meridian Data '
            'Systems Limited, without limitation" violates the playbook requirement for a mutual '
            "aggregate liability cap of £500,000 per contract year with standard exclusions for "
            "fraud, personal injury, and wilful misconduct. The clause must be replaced with a "
            "mutual capped liability provision at the prescribed threshold."
        ),
        "suggested_fix": (
            "The aggregate liability of each of Meridian Data Systems Limited and FinServ "
            "Holdings PLC to the other under or in connection with this Agreement, whether "
            "arising in contract, tort (including negligence), misrepresentation, or otherwise, "
            "shall not exceed £500,000 (five hundred thousand pounds sterling) in any "
            "twelve-month period. Nothing in this Agreement shall limit or exclude either "
            "party's liability for fraud, for death or personal injury caused by its negligence, "
            "or for wilful misconduct."
        ),
        "alternative_fixes": [
            "Subject to the exceptions set out below, the total aggregate liability of Meridian "
            "Data Systems Limited to FinServ Holdings PLC and of FinServ Holdings PLC to "
            "Meridian Data Systems Limited under or in connection with this Agreement shall in "
            "no circumstances exceed £500,000 per contract year. The foregoing cap shall not "
            "apply to liability arising from fraud, wilful misconduct, or death or personal "
            "injury caused by negligence.",
            "Each party's aggregate liability to the other for all claims arising under or in "
            "connection with this Agreement in any twelve-month period shall be limited to "
            "£500,000. This limitation shall not apply to claims for fraud, death or personal "
            "injury caused by negligence, or wilful default.",
        ],
    }
)

_FEW_SHOT_MESSAGES: list[dict] = [
    {"role": "user", "content": _FEW_SHOT_GOVERNING_LAW_USER},
    {"role": "assistant", "content": _FEW_SHOT_GOVERNING_LAW_ASSISTANT},
    {"role": "user", "content": _FEW_SHOT_LIABILITY_USER},
    {"role": "assistant", "content": _FEW_SHOT_LIABILITY_ASSISTANT},
]


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
    playbook_rule: str = "",
    contract_id: str = "",
) -> dict:
    """
    Generate a recommendation and suggested fix for a risky clause.

    Uses accepted_examples (from wording_retriever) as few-shot context.
    Uses playbook_rule to name the specific standard violated in the recommendation.
    Records LLM cost via cost_tracker.
    Returns {"recommendation": str, "suggested_fix": str, "alternative_fixes": list[str]}.
    """
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    model = settings.LLM_MODEL

    examples_text = ""
    if accepted_examples:
        lines = [f"  {i + 1}. {ex['text']}" for i, ex in enumerate(accepted_examples)]
        examples_text = "Accepted wording examples from similar contracts:\n" + "\n".join(lines)

    rule_section = (
        f"Playbook rule violated: {playbook_rule}\n\n" if playbook_rule else ""
    )

    user_message = (
        f"Clause type: {clause_type}\n\n"
        f"Clause text:\n{clause_text}\n\n"
        "Risk indicators identified:\n- "
        + "\n- ".join(risk_indicators or ["(none)"])
        + "\n\n"
        + rule_section
        + (examples_text if examples_text else "No accepted examples available.")
    )

    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        *_FEW_SHOT_MESSAGES,
        {"role": "user", "content": user_message},
    ]

    response = await client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=messages,
    )

    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    cost_usd = _estimate_cost(model, prompt_tokens, completion_tokens)

    tracking_id = contract_id if contract_id else f"recommendation:{clause_type}"
    await cost_tracker.record_llm_call(
        contract_id=tracking_id,
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