# Contract Intelligence Platform — CLAUDE.md

## What This Project Does
Lawyers upload PDF/DOCX contracts. The system:
1. Extracts text via OCR
2. Extracts clauses via LLM → structured JSON
3. Checks clauses against 3 sources in parallel:
   - PostgreSQL: playbook rules (allowed terms, jurisdiction, liability)
   - Qdrant: vector similarity (accepted past wording)
   - Neo4j: party relationship graph (counterparty risk history)
4. LangGraph orchestrates the 3 results → Risk Score (Green / Amber / Red)
5. LLM generates recommendation + suggested fix
6. Lawyer reviews on dashboard → Approve / Reject / Modify
7. Decisions feed back into Qdrant + Neo4j knowledge bases
8. Cleanup job removes temp data, keeps audit summary

---

## Python Version
Python 3.12+. All DB calls and task handlers must be async (no sync sessions in request handlers).

---

## Repository Layout & Agent Ownership

| Folder | Owner Agent | Branch |
|--------|-------------|--------|
| `contracts_platform/core/` | database-agent (bootstraps first) | feature/database-agent |
| `contracts_platform/db/` | database-agent | feature/database-agent |
| `contracts_platform/api/` | fastapi-agent | feature/fastapi-agent |
| `contracts_platform/auth/` | fastapi-agent | feature/fastapi-agent |
| `contracts_platform/notifications/` | fastapi-agent | feature/fastapi-agent |
| `contracts_platform/file_handling/` | fastapi-agent + celery-agent | feature/fastapi-agent |
| `contracts_platform/pipeline/` | llm-pipeline-agent | feature/llm-pipeline-agent |
| `contracts_platform/orchestration/` | langgraph-agent | feature/langgraph-agent |
| `contracts_platform/workers/` | celery-agent | feature/celery-agent |
| `frontend/` | frontend-agent | feature/frontend-agent |
| `tests/` | qa-agent | feature/qa-agent |
| `.github/workflows/` | qa-agent | feature/qa-agent |

---

## Branch Strategy

- `main` — protected. Merge only via PR after qa-agent review passes CI
- `feature/database-agent` — merge FIRST (all agents depend on core/ + db/)
- `feature/celery-agent` — merge SECOND
- `feature/llm-pipeline-agent` — merge after celery-agent
- `feature/langgraph-agent` — merge after celery-agent
- `feature/fastapi-agent` — merge after pipeline + langgraph
- `feature/frontend-agent` — merge after fastapi-agent
- `feature/qa-agent` — merge last

---

## Coding Standards

- Formatter: Black (line length 100)
- Imports: isort
- Linting: flake8
- All public functions: full type annotations
- Schemas: Pydantic v2 (never v1 syntax)
- ORM: SQLAlchemy 2.x async only
- MongoDB: Motor async only
- Secrets: environment variables only — never hardcoded
- Logging: structlog (JSON format) — never use `print()`
- Tracing: OpenTelemetry spans on every route and Celery task
- Errors: RFC 7807 Problem Detail JSON from all API endpoints

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.12+) |
| Task Queue | Celery + Redis |
| LLM | OpenAI (gpt-4o) |
| Embeddings | OpenAI (text-embedding-3-small) |
| OCR | Azure AI Document Intelligence |
| File Storage | Azure Blob Storage (permanent contract files) |
| Temp Storage | Azure File Share (extracted text — cleaned up post-audit) |
| Frontend | React 18 + TypeScript + Vite → deploy to Azure Static Web Apps |

## Database Roles

| Database | Purpose |
|----------|---------|
| MongoDB | Contract lifecycle tracking: status, stage, errors, final_risk, costs |
| PostgreSQL | Playbook rules, rule versions, jurisdictions, rule weights |
| Qdrant | Clause embeddings — similarity search + accepted wording retrieval |
| Neo4j | Party-contract relationship graph — conflict detection, counterparty history |
| Redis | Celery broker + result backend + LangGraph checkpoints + job progress pub/sub |

---

## Async Task Flow

```
Upload → ingest_task → ocr_task → clause_extraction_task
       → review_orchestration_task (LangGraph: parallel PostgreSQL + Qdrant + Neo4j)
       → recommendation_task
       → MongoDB: status = REVIEW_READY
       → Lawyer reviews on dashboard
       → post_decision_task (update Qdrant + Neo4j)
       → cleanup_task (remove temp data, write audit summary)
```

---

## LangGraph Graph

- State: `ContractReviewState` (see `orchestration/state.py`)
- Parallel nodes: `playbook_check_node`, `vector_check_node`, `graph_check_node`
- Sequential: `risk_aggregator_node` → `recommendation_node` → `explainability_node`
- Recommendation node skipped if `risk_level == GREEN`
- Weights loaded from PostgreSQL `rule_weights` table (5-min cache)
- Checkpoints: Redis (`redis_checkpointer.py`) — survives worker restarts
- Partial failure: if one node fails, continue with `degraded_mode=True`

---

## Auth & Roles

- JWT (HS256): access token 15 min, refresh token 7 days
- Refresh tokens rotate on every use
- JWT stored in httpOnly cookies — never localStorage

| Role | Permissions |
|------|-------------|
| `junior_lawyer` | View contracts and clauses, add comments |
| `senior_lawyer` | Approve / Reject / Modify clauses, export |
| `admin` | Manage users, manage playbook rules, system health |

---

## File Upload Rules

- Max size: 50 MB
- Allowed types: PDF, DOCX only
- SHA-256 hash checked for duplicates — returns existing `contract_id` if duplicate
- Files stored encrypted at rest in Azure Blob Storage
- Extracted plain text stored temporarily in Azure File Share — deleted by cleanup_task after audit

---

## LLM & OCR

- LLM: OpenAI only — use `LLM_MODEL` env var (default `gpt-4o`). Never hardcode model names.
- Embeddings: OpenAI only — use `EMBEDDING_MODEL` env var (default `text-embedding-3-small`)
- OCR: Azure AI Document Intelligence only — use `AZURE_OCR_ENDPOINT` + `AZURE_OCR_KEY` env vars

## LLM Cost Tracking

Every LLM call must record to MongoDB `cost_tracking` collection:
`contract_id`, `task_name`, `model`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `timestamp`
Use `pipeline/cost_tracker.py` for all LLM calls.

---

## Celery Task Rules

Every task must:
1. Update MongoDB `current_stage` at start
2. Write to MongoDB `errors[]` array on failure
3. Emit progress event via Redis pub/sub (consumed by WebSocket manager)
4. Declare explicit `max_retries` and `retry_backoff` in `@app.task` decorator
5. After max retries: route to `dlq` queue, set MongoDB `status=ERROR`, log alert via structlog

## Storage Rules

- Permanent files (PDF/DOCX): Azure Blob Storage via `file_handling/storage.py`
- Temp text files: Azure File Share via `file_handling/temp_storage.py`
- Never write files to local disk in production
- `cleanup_task` must delete Azure File Share temp entry after audit completes

---

## Commit Convention

Format: `<type>(<scope>): <summary in present tense>`

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `security`
Scopes: `api`, `db`, `pipeline`, `orchestration`, `workers`, `frontend`, `core`, `auth`, `infra`, `skills`

Examples:
```
feat(api): add contract upload endpoint with virus scan dispatch
feat(db): add PostgreSQL playbook rule versioning table
fix(workers): handle LLM rate limit in clause_extraction_task retry
security(auth): enforce refresh token rotation on every use
test(orchestration): add parallel node fan-out unit tests
```

---

## Skills Available

| Skill | What It Does |
|-------|-------------|
| `/scaffold-module` | Generates route + schema + service + test for a new module |
| `/test-pipeline` | Runs end-to-end pipeline test with a sample contract file |
| `/add-clause-type` | Adds a new clause type across all layers consistently |
| `/db-health` | Checks all 5 DB/service connections with latency |
| `/review-security` | Audits routes, auth, file upload for vulnerabilities |

---

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | LLM + embeddings |
| `AZURE_OCR_ENDPOINT` / `AZURE_OCR_KEY` | Azure AI Document Intelligence |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Blob Storage for contract files |
| `AZURE_FILE_SHARE_CONNECTION_STRING` / `AZURE_FILE_SHARE_NAME` | Temp text storage |
| `MONGODB_URL` | MongoDB connection |
| `POSTGRES_DSN` | PostgreSQL connection |
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant vector DB |
| `NEO4J_URL` / `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j graph DB |
| `REDIS_URL` | Redis (Celery + checkpoints + pub/sub) |
| `JWT_SECRET` | Auth token signing |
| `ENCRYPTION_KEY` | AES-256 PII encryption |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Tracing export (leave blank to disable) |

Never commit `.env` — only `.env.example` with placeholder values.
