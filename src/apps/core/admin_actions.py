from django.contrib import messages
from django.utils.translation import gettext_lazy as _


def activate_instances(modeladmin, request, queryset):
    for item in queryset:
        item.is_active = True
        item.save()

    messages.add_message(request, messages.INFO, _('All items have been enabled.'))


def deactivate_instances(modeladmin, request, queryset):
    for item in queryset:
        item.is_active = False
        item.save()

    messages.add_message(request, messages.INFO, _('All items have been disabled.'))


def activate_notifications(modeladmin, request, queryset):
    for item in queryset:
        item.allow_email_notifications = True
        item.allow_push_notifications = True
        item.allow_sms_notifications = True
        item.allow_whatsapp_notifications = True
        item.save()

    messages.add_message(request, messages.INFO, _('All notifications have been enabled.'))


def deactivate_notifications(modeladmin, request, queryset):
    for item in queryset:
        item.allow_email_notifications = False
        item.allow_push_notifications = False
        item.allow_sms_notifications = False
        item.allow_whatsapp_notifications = False
        item.save()

    messages.add_message(request, messages.INFO, _('All notifications have been disabled.'))


activate_instances.allow_tags = True
activate_instances.short_description = _("Activate")

deactivate_instances.allow_tags = True
deactivate_instances.short_description = _("Deactivate")

deactivate_notifications.allow_tags = True
deactivate_notifications.short_description = _("Deactivate Notifications")

activate_notifications.allow_tags = True
activate_notifications.short_description = _("Re-enable Email Notifications")
