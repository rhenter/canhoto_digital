from django.db import models
from django.utils.translation import gettext_lazy as _


class TaskLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILURE = "FAILURE", "Failure"

    task_id = models.CharField(max_length=255, unique=True)
    task_name = models.CharField(max_length=255)
    periodic_task_name = models.CharField(max_length=255, null=True, blank=True)
    queue_name = models.CharField(max_length=255, null=True, blank=True)
    worker = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=Status.choices)
    task_args = models.JSONField(null=True, blank=True)
    task_kwargs = models.JSONField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    traceback = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Task Log')
        verbose_name_plural = _('Task Logs')

    def __str__(self):
        return f"{self.task_id} ({self.task_name}) → {self.status}"


class TaskLogStatistics(TaskLog):
    """
    Proxy model for TaskLog to provide statistics functionality
    """
    class Meta:
        proxy = True
        verbose_name = _('Task Log Statistics')
        verbose_name_plural = _('Task Log Statistics')
