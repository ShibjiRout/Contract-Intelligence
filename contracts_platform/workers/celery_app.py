import sys

from celery import Celery

from contracts_platform.core.config import settings
from contracts_platform.workers.queues import QUEUES, TASK_ROUTES

app = Celery("contracts_platform")

app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_queues=QUEUES,
    task_routes=TASK_ROUTES,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Windows does not support prefork — use solo pool to avoid PermissionError
    worker_pool="solo" if sys.platform == "win32" else "prefork",
)

app.autodiscover_tasks(
    [
        "contracts_platform.workers.tasks.ingest_task",
        "contracts_platform.workers.tasks.ocr_task",
        "contracts_platform.workers.tasks.clause_extraction_task",
        "contracts_platform.workers.tasks.review_orchestration_task",
        "contracts_platform.workers.tasks.recommendation_task",
        "contracts_platform.workers.tasks.post_decision_task",
        "contracts_platform.workers.tasks.cleanup_task",
        "contracts_platform.workers.dead_letter",
    ]
)
