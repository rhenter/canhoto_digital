from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.contenttypes.models import ContentType

from .models import SMTPSettings, TermsOfService, AuditLogEntry

admin.site.site_header = f'{settings.APP_NAME} Admin'
admin.site.site_title = settings.APP_NAME
admin.site.enable_nav_sidebar = False


class TermsOfServiceForm(forms.ModelForm):
    class Meta:
        model = TermsOfService
        fields = '__all__'


@admin.register(SMTPSettings)
class SMTPSettingsAdmin(admin.ModelAdmin):
    model = SMTPSettings
    list_display = [
        'host',
        'port',
        'username',
        'timeout',
        'use_tls',
        'use_ssl',
        'is_active',
    ]
    exclude = ['code']

    def has_add_permission(self, *args, **kwargs):
        return not SMTPSettings.objects.exists()


class OrderedContentTypeFilter(SimpleListFilter):
    title = 'content type'
    parameter_name = 'content_type'

    def lookups(self, request, model_admin):
        """Return a list of tuples for the filter options, ordered alphabetically by model name"""
        # Get all content types that are referenced in LogEntry
        exclude_models = [
            'adminlogentry',
            'contenttype',
            'session',
            'permission'
        ]

        content_types = ContentType.objects.filter(
            logentry__isnull=False
        ).distinct().order_by('app_label', 'model')

        return [(ct.id, f"{ct.app_label} | {ct.model}") for ct in content_types]

    def queryset(self, request, queryset):
        """Filter the queryset based on the selected content type"""
        if self.value():
            return queryset.filter(content_type=self.value())
        return queryset


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    model = AuditLogEntry
    list_display = [
        'action_time',
        'user',
        'content_type',
        'object_repr',
        'action_flag',
        'change_message',
    ]
    list_filter = [
        'action_flag',
        'action_time',
        OrderedContentTypeFilter,
        'user'
    ]
    search_fields = [
        'object_repr',
        'change_message'
    ]
    readonly_fields = [
        'action_time',
        'user',
        'content_type',
        'object_id',
        'object_repr',
        'action_flag',
        'change_message'
    ]
    date_hierarchy = 'action_time'
    ordering = ['-action_time']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
