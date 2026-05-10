from kombu import Queue

QUEUES = [
    Queue("ingest"),
    Queue("ocr"),
    Queue("extraction"),
    Queue("qdrant_check"),
    Queue("orchestration"),
    Queue("dlq"),
]

TASK_ROUTES: dict[str, dict[str, str]] = {
    "contracts_platform.workers.tasks.ingest_task.ingest_task": {"queue": "ingest"},
    "contracts_platform.workers.tasks.ocr_task.ocr_task": {"queue": "ocr"},
    "contracts_platform.workers.tasks.clause_extraction_task.clause_extraction_task": {"queue": "extraction"},
    "contracts_platform.workers.tasks.qdrant_check_task.qdrant_check_task": {"queue": "qdrant_check"},
    "contracts_platform.workers.tasks.review_orchestration_task.review_orchestration_task": {"queue": "orchestration"},
    "contracts_platform.workers.dead_letter.dead_letter_handler": {"queue": "dlq"},
}
