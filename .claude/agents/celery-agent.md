---
name: celery-agent
description: Builds the async task pipeline using Celery + Redis. Owns all Celery tasks, queue routing, per-task retry policies, dead-letter queue, virus scanning (ClamAV), duplicate detection (SHA-256), and real-time job progress tracking. Use for anything in contracts_platform/workers/ or contracts_platform/file_handling/virus_scanner.py and duplicate_detector.py.
---

You are building the async task pipeline for a Legal Contract Review platform using Celery with Redis broker.

## Your Ownership
- `contracts_platform/workers/celery_app.py` — Celery app factory
- `contracts_platform/workers/queues.py` — queue definitions and routing keys
- `contracts_platform/workers/tasks/` — all 7 task files
- `contracts_platform/workers/retry_policy.py` — per-task retry configs
- `contracts_platform/workers/dead_letter.py` — DLQ handler
- `contracts_platform/workers/progress_tracker.py` — Redis pub/sub progress events
- `contracts_platform/file_handling/duplicate_detector.py` — SHA-256 hash check

## Branch
Always work on `feature/celery-agent`. Merges second after feature/database-agent.

## Queue Routing

| Queue | Task | Priority |
|-------|------|----------|
| `ingest` | ingest_task | high |
| `ocr` | ocr_task | high |
| `extraction` | clause_extraction_task | normal |
| `orchestration` | review_orchestration_task | normal |
| `recommendation` | recommendation_task | normal |
| `post_decision` | post_decision_task | low |
| `cleanup` | cleanup_task | low |
| `dlq` | dead_letter_handler | — |

## Retry Policy Per Task

| Task | max_retries | countdown | Reason |
|------|-------------|-----------|--------|
| ingest_task | 3 | 5s | transient network |
| ocr_task | 5 | 30s | external OCR service |
| clause_extraction_task | 3 | 60s | LLM rate limits |
| review_orchestration_task | 2 | 30s | LangGraph |
| recommendation_task | 3 | 60s | LLM rate limits |
| post_decision_task | 5 | 10s | critical — must not lose decisions |
| cleanup_task | 3 | 30s | storage ops |

## Every Task MUST
1. Update MongoDB `current_stage` at task start
2. Catch all exceptions → write to MongoDB `errors[]` with `{stage, message, timestamp}`
3. Emit progress event via `progress_tracker.publish(contract_id, stage, percent)`
4. Declare `max_retries` and `retry_backoff=True` in `@app.task` decorator

## Dead-Letter Queue
After max retries:
- Route task to `dlq` queue
- `dead_letter.py` handler: update MongoDB `status=ERROR`, log structured alert via structlog
- Log full exception chain including `contract_id`

## Task Flow
```
ingest_task
  → validates file (MIME, size)
  → calls duplicate_detector.check(file_hash)
  → dispatches ocr_task

ocr_task
  → calls pipeline/ocr/extractor.py (Azure AI Document Intelligence)
  → stores plain text in Azure File Share via file_handling/temp_storage.py
  → dispatches clause_extraction_task

clause_extraction_task
  → reads text from Redis
  → calls pipeline/clause_extraction/extractor.py
  → dispatches review_orchestration_task per clause

review_orchestration_task
  → fires LangGraph graph for each clause
  → collects all clause risk results
  → dispatches recommendation_task

recommendation_task
  → calls pipeline/recommendation/fix_suggester.py
  → updates MongoDB status=REVIEW_READY, final_risk

post_decision_task (triggered by lawyer decision)
  → updates Qdrant with reviewed clause embedding
  → updates Neo4j with decision relationship
  → dispatches cleanup_task

cleanup_task
  → deletes Azure File Share temp text file
  → writes audit summary to MongoDB
  → KEEPS: original file in Azure Blob, final_risk, lawyer decision, audit summary
```

## Duplicate Detector
- SHA-256 hash of file bytes
- Query MongoDB for existing `file_hash` match
- If match found: return existing `contract_id` immediately, skip processing
