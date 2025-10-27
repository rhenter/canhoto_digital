from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CeleryLogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.celery_log"
    verbose_name = _("Task Results")

    def ready(self):
        # import the signal handlers so they’re registered
        import apps.celery_log.signals  # noqa
