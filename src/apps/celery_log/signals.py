from celery.signals import task_success, task_failure

from .utils import create_task_log


@task_success.connect
def log_task_success(sender=None, result=None, **kwargs):
    create_task_log(sender=sender, result=result)


@task_failure.connect
def log_task_failure(sender=None, exception=None, **kwargs):
    create_task_log(sender=sender, exception=exception)
