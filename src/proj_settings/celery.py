import os

from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger
from celery.utils.log import get_task_logger
from django.conf import settings

logger = get_task_logger(__name__)


@after_setup_logger.connect
def on_after_setup_logger(logger, *args, **kwargs):
    from json_log_formatter import VerboseJSONFormatter

    if settings.API_LOG_CELERY_JSON:
        formatter = VerboseJSONFormatter()
        for handler in list(logger.handlers):
            handler.setFormatter(formatter)
            handler.setLevel(settings.LOGGER_LEVEL)


@after_setup_task_logger.connect
def on_after_setup_task_logger(logger, *args, **kwargs):
    from json_log_formatter import VerboseJSONFormatter

    if settings.API_LOG_CELERY_JSON:
        formatter = VerboseJSONFormatter()
        for handler in list(logger.handlers):
            handler.setFormatter(formatter)
            handler.setLevel(settings.LOGGER_LEVEL)


# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"{settings.SETTINGS_FOLDER}.settings")
celery_app = Celery(f"{settings.SETTINGS_FOLDER}")
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.worker_hijack_root_logger = False


@after_setup_logger.connect
def configure_celery_logger(logger, **kwargs):
    import logging.config
    logging.config.dictConfig(settings.LOGGING)


@celery_app.task(bind=True)
def debug_task(self):
    logger.info("Request: {0!r}".format(self.request))
    return 42
