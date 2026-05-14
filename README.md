# Contract Intelligence Platform

AI-powered contract review platform for legal teams. The system ingests PDF/DOCX contracts, extracts clauses, compares them against playbook standards, checks prior accepted precedents, and presents lawyer-ready recommendations for review.

## What It Does

- Upload PDF and DOCX contracts for asynchronous review
- Run OCR with Azure Document Intelligence
- Extract clauses with OpenAI structured outputs
- Perform a document-level playbook similarity pre-check after OCR
- Compare clause wording against playbook standards stored in Qdrant and PostgreSQL
- Use Neo4j relationship history to surface accepted precedents by party
- Generate AI recommendations and proposed counter-wording
- Support lawyer approval, rejection, and change-request workflows
- Provide an admin console for playbook rule management and user management

## System Overview

The codebase is split into a FastAPI backend, Celery worker pipeline, React frontend, and a multi-database storage model.

- Backend: `contracts_platform`
- Frontend: `frontend`
- Workers: Celery tasks under `contracts_platform/workers`
- API entrypoint: `contracts_platform/api/main.py`
- App runner: `main.py`

Core infrastructure used by the application:

- MongoDB for operational contract, clause, user, and audit state
- PostgreSQL for playbook rules and rule versioning
- Qdrant for vector similarity search
- Neo4j for contract-party-clause precedent relationships
- Redis for progress events, rate limiting, cache, and Celery broker/backend
- Azure Blob Storage for contract file storage
- Azure File Share for OCR text persistence
- OpenAI for clause extraction and recommendation generation
- Azure Document Intelligence for OCR

## Main Processing Flow

1. A lawyer uploads a contract through `/contracts/upload`.
2. The API stores metadata, uploads the file to Azure Blob Storage, and dispatches Celery ingestion.
3. `ingest_task` validates file type and duplicate status.
4. `ocr_task` runs OCR, stores extracted text, extracts parties for Neo4j linkage, and performs a document-level playbook similarity pre-check.
5. If the top playbook similarity score is at least 90%, the contract is flagged for clause-level auto-approval after extraction.
6. `clause_extraction_task` still extracts clauses, stores them in MongoDB, and indexes vectors in Qdrant.
7. If the auto-accept flag is set, all extracted clauses are marked approved and GREEN, and the contract is completed without deeper clause review.
8. Otherwise, `qdrant_check_task` auto-approves standard clauses or dispatches risky ones for orchestration.
9. `review_orchestration_task` runs the LangGraph review flow:
   - intent extraction
   - gap analysis
   - precedent lookup
   - playbook scoring
   - recommendation generation
10. Lawyers review the results in the frontend and approve, reject, or request changes.

## Orchestration Summary

The real orchestration logic lives in `contracts_platform/orchestration`.

- `graph.py`: builds and runs the LangGraph review flow
- `state.py`: shared clause review state object
- `nodes/intent_extraction_node.py`: derives clause legal intent
- `nodes/gap_analysis_node.py`: compares intent to the nearest playbook standard
- `nodes/precedent_check_node.py`: checks accepted precedents in Neo4j
- `nodes/playbook_score_node.py`: applies PostgreSQL rule checks and assigns risk
- `nodes/recommendation_node.py`: generates the final lawyer-facing recommendation

## Frontend

The React frontend provides:

- landing page
- login page
- dashboard
- upload flow
- review workspace with PDF preview and clause cards
- admin page for playbook rules and users

Important frontend paths:

- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/UploadPage.tsx`
- `frontend/src/pages/ReviewPage.tsx`
- `frontend/src/pages/AdminPage.tsx`

## Repository Layout

```text
.
├── contracts_platform
│   ├── api
│   ├── auth
│   ├── core
│   ├── db
│   ├── file_handling
│   ├── notifications
│   ├── orchestration
│   ├── pipeline
│   └── workers
├── frontend
├── scripts
├── docker
└── tests
```

## Local Development

### Backend

Install Python dependencies and run the API:

```powershell
.venv\Scripts\python.exe main.py
```

Or directly with Uvicorn:

```powershell
.venv\Scripts\uvicorn.exe contracts_platform.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

### Workers

```powershell
.venv\Scripts\celery.exe -A contracts_platform.workers.celery_app worker --loglevel=info -Q ingest,ocr,extraction,qdrant_check,orchestration,dlq
```

### Infrastructure

The repo includes Docker definitions for:

- PostgreSQL
- Qdrant
- Neo4j

Start them with:

```powershell
docker compose -f docker/docker-compose.yml up -d
```

## Docs

- System design: [System_Design.md](./System_Design.md)
- Demo link file: [Demo_Link.txt](./Demo_Link.txt)
- Full architecture audit: [CODEBASE_ARCHITECTURE_REPORT.txt](./CODEBASE_ARCHITECTURE_REPORT.txt)

## Notes

- The root README was empty before this update.
- I did not find a production-hosted demo URL in the codebase, so `Demo_Link.txt` points to the local URLs actually configured in the repository.
