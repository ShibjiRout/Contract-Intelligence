# /test-pipeline

Run a full end-to-end pipeline test with a sample contract and report per-stage results.

## Usage
```
/test-pipeline [--file <path>] [--verbose]
```

## Default
Uses `tests/e2e/fixtures/sample_nda.pdf` if no file specified.

## Steps
1. Run `/db-health` first — abort if any DB is down
2. Upload file via `POST /contracts/upload` — capture `contract_id`
3. Poll `GET /contracts/{contract_id}/status` every 5 seconds
4. Timeout after 5 minutes — fail with last known stage if not REVIEW_READY
5. On REVIEW_READY: fetch clause list and validate each against `ExtractedClause` schema
6. Validate `final_risk` is one of GREEN / AMBER / RED
7. Validate at least one clause has non-empty `suggested_fix`
8. Print per-stage timing report

## Output Format
```
Stage              Status    Duration
─────────────────────────────────────
Upload             ✓         0.3s
OCR                ✓         4.1s
Clause Extraction  ✓         8.7s
Risk Analysis      ✓         3.2s
Recommendation     ✓         5.4s
─────────────────────────────────────
Total              ✓         21.7s
Final Risk: AMBER
Clauses: 12 extracted, 2 missing (force_majeure, indemnity)
```
