import time
from datetime import timedelta

from celery.utils.log import get_task_logger
from django.apps import apps as django_apps
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from proj_settings.celery import celery_app as app

logger = get_task_logger(__name__)


@app.task(name='clear_celery_task_logs')
def clear_celery_task_logs():
    start_time = time.perf_counter()
    logger.debug("Starting clear_celery_task_logs")

    TaskLog = django_apps.get_model('celery_log', 'TaskLog')
    cutoff = timezone.now() - timedelta(days=settings.CELERY_TASK_LOGS_EXPIRES)

    total_deleted = 0
    batch_size = 1000
    try:
        with transaction.atomic():
            qs = TaskLog.objects.filter(timestamp__lte=cutoff)
            while True:
                batch_ids = list(qs.values_list('id', flat=True)[:batch_size])
                if not batch_ids:
                    break
                deleted, _ = TaskLog.objects.filter(id__in=batch_ids).delete()
                total_deleted += deleted
    except Exception:
        logger.exception("clear_celery_task_logs failed during batch delete")

    duration = time.perf_counter() - start_time
    logger.info(f"clear_celery_task_logs completed: removed {total_deleted} entries in {duration:.2f}s")

    return {
        'status': 'Celery task logs cleaned',
        'deleted': total_deleted,
        'duration_s': round(duration, 2),
    }
