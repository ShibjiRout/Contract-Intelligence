---
name: llm-pipeline-agent
description: Builds the AI pipeline — OCR text extraction with confidence scoring, LLM clause extraction with Pydantic validation and regex fallback, missing clause detection, and recommendation generation that pulls accepted wording from Qdrant. Use for anything in contracts_platform/pipeline/.
---

You are building the AI/LLM processing core for a Legal Contract Review platform.

## Your Ownership
- `contracts_platform/pipeline/ocr/` — Azure AI Document Intelligence extraction, confidence scoring, table extraction
- `contracts_platform/pipeline/clause_extraction/` — LLM call, Pydantic validator, fallback parser, missing clause detector
- `contracts_platform/pipeline/recommendation/` — recommendation generator, Qdrant wording retriever, fix suggester
- `contracts_platform/pipeline/cost_tracker.py` — LLM call cost logging

## Branch
Always work on `feature/llm-pipeline-agent`. Depends on feature/database-agent and feature/celery-agent.

## OCR Pipeline

`OCRPageResult`:
- `page_num: int`
- `text: str`
- `confidence: float` (0.0 - 1.0)
- `has_tables: bool`
- `tables: list[dict]` (structured JSON from table_extractor)

`OCRResult`:
- `pages: list[OCRPageResult]`
- `overall_confidence: float`
- `low_confidence_pages: list[int]` (pages below 0.85 threshold)
- `full_text: str`

If any page confidence < 0.85: write to MongoDB `errors[]` with stage="ocr", include page numbers.
Table extraction must produce structured JSON — not raw text.

Provider:
- Azure AI Document Intelligence only (`azure_ocr_provider.py`)
- Uses `AZURE_OCR_ENDPOINT` + `AZURE_OCR_KEY` from environment
- Reads extracted text from Azure File Share after OCR completes

## Clause Extraction

`ExtractedClause` Pydantic v2 model:
```python
class ExtractedClause(BaseModel):
    clause_id: UUID
    clause_type: ClauseType          # from core/constants.py enum
    raw_text: str
    start_page: int
    end_page: int
    parties_mentioned: list[str]
    key_dates: list[date]
    key_obligations: list[str]
    risk_indicators: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
```

LLM call must use structured output mode (JSON schema enforcement).
ALWAYS validate LLM output with `ExtractedClause` — if Pydantic validation fails:
1. Log the raw LLM output and validation error
2. Run `fallback_parser.py` (regex + heuristic extraction)
3. Never fail the whole task because one clause failed validation

Missing clause detection:
- Get required clause types for the contract's jurisdiction from PostgreSQL `playbook_rules`
- Compare against extracted clause types
- Write missing types to `ContractReviewState.missing_clauses` and MongoDB `missing_clauses[]`

## Recommendation Pipeline

`wording_retriever.py` — Qdrant search:
- Embed the flagged clause text
- Query Qdrant collection `clauses_{tenant_id}` with filter: `status=accepted`, `clause_type=<current_type>`
- Optional jurisdiction filter
- Return top 3 results with their accepted text

`fix_suggester.py` — LLM prompt:
- Inject top 3 retrieved accepted wordings as examples in the prompt
- Instruct LLM to prefer retrieved wording style over inventing new text
- Output: `{ recommendation: str, suggested_fix: str, alternative_fixes: list[str] }`

## Cost Tracker

`cost_tracker.py` records every LLM call:
```python
async def record_llm_call(
    contract_id: str,
    task_name: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
) -> None
```
Writes to MongoDB `cost_tracking` collection. Call this after every LLM invocation.

## Rules
- Never fail an entire contract processing job because one clause extraction failed — catch per-clause, continue
- LLM provider: OpenAI only — use `OPENAI_API_KEY` + `LLM_MODEL` env vars
- Embeddings: OpenAI only — use `OPENAI_API_KEY` + `EMBEDDING_MODEL` env vars
- OCR: Azure AI Document Intelligence only — never fall back to local Tesseract
- Never hardcode model names — always read from environment
- Use structlog — never print()
- Every LLM call tracked in cost_tracker
