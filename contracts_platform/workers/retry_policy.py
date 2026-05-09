RETRY_POLICY: dict[str, dict] = {
    "ingest_task": {
        "max_retries": 3,
        "countdown": 5,
        "retry_backoff": False,
    },
    "ocr_task": {
        "max_retries": 5,
        "countdown": 30,
        "retry_backoff": False,
    },
    "clause_extraction_task": {
        "max_retries": 3,
        "countdown": 60,
        "retry_backoff": False,
    },
    "review_orchestration_task": {
        "max_retries": 2,
        "countdown": 30,
        "retry_backoff": False,
    },
    "recommendation_task": {
        "max_retries": 3,
        "countdown": 60,
        "retry_backoff": False,
    },
    "post_decision_task": {
        "max_retries": 5,
        "countdown": 10,
        "retry_backoff": False,
    },
    "cleanup_task": {
        "max_retries": 3,
        "countdown": 30,
        "retry_backoff": False,
    },
}
