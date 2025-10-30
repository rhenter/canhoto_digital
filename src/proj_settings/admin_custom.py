from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _


class MyAdminSite(AdminSite):
    site_header = _(f"{settings.APP_NAME} Administration Panel")
    site_title = _(f"{settings.APP_NAME} Admin")
    index_title = _(f"{settings.APP_NAME} Admin Area")
    enable_nav_sidebar = False

    def get_app_list(self, request, app_label=None):
        """
        Override to organize models into custom functional groups
        """
        custom_groups = {
            _("Company"): [
                "company.Company",
                "invoice.Invoice",
            ],
            _("Delivery"): [
                "delivery.Delivery",
                "delivery.ProofOfDelivery",
            ],
            _("Celery - Background Tasks"): [
                "django_celery_beat.CrontabSchedule",
                "django_celery_beat.IntervalSchedule",
                "django_celery_beat.PeriodicTask",
                "celery_log.TaskLog",
                "celery_log.TaskLogStatistics",
            ],
            _("User Management"): [
                "user.User",
                "user.CustomGroup",
                "user.UserMetric",
                "authtoken.TokenProxy",
                "core.AuditLogEntry",
            ],
        }

        app_dict = self._build_app_dict(request, app_label)
        app_list = list(app_dict.values())

        # Create a lookup dictionary for quick model access
        model_lookup = {}
        for app in app_list:
            for model in app["models"]:
                model_id = f"{app['app_label']}.{model['object_name']}"
                model_lookup[model_id] = model

        # Convert to the expected list format, preserving the original order
        result = []
        for group_name, model_ids in custom_groups.items():
            group_models = []
            # Iterate through model_ids in the order defined in custom_groups
            for model_id in model_ids:
                if model_id in model_lookup:
                    group_models.append(model_lookup[model_id])

            # Only include groups that have models
            if group_models:
                result.append({
                    "name": group_name,
                    "app_label": group_name.lower().replace(" ", "_").replace("&", "and"),
                    "models": group_models,
                })

        return result


# Create an instance of the custom admin site
admin_site = MyAdminSite(name='custom_admin')


# Function to copy all registrations from default admin site to custom admin site
def register_all_models():
    """
    Copy all model registrations from the default admin site to the custom admin site.
    This should be called after all apps have been loaded.
    """
    for model, model_admin in admin.site._registry.items():
        if not admin_site.is_registered(model):
            admin_site.register(model, model_admin.__class__)


# This will be called when Django is ready
from django.core.exceptions import AppRegistryNotReady


def autodiscover_and_register():
    """
    Autodiscover admin modules and register all models with custom admin site
    """
    try:
        # First, let Django autodiscover all admin modules
        admin.autodiscover()
        # Then copy all registrations to our custom site
        register_all_models()
    except AppRegistryNotReady:
        # If apps aren't ready yet, this will be called later
        pass
