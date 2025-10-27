import logging

from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _, get_language
from django_models.models import SignalsModel, UUIDModel
from django_models.models.generic import CodeModel
from django_models.models.managers import SignalsManager

TERMS_OF_SERVICE_TYPES = (
    ('user', _('User')),
    ('store', _('Store')),
)

logger = logging.getLogger(__name__)


class SortOrderModel(models.Model):
    """
    Abstract model that provides sort order functionality for models.
    
    Automatically manages sort order for model instances, ensuring proper
    sequencing when creating new records.
    """
    sort_order = models.PositiveIntegerField(default=0, blank=False, null=False, verbose_name=_("Sort"))

    class Meta:
        abstract = True

    def _get_next_sort_order(self):
        if self.sort_order:
            return self.sort_order

        sort_order = 0
        if self.sort_order == 0:
            sort_order = 1

        last_instance = type(self).objects.last()
        if last_instance:
            sort_order = last_instance.sort_order + 1
        return sort_order


class TimestampedModel(models.Model):
    """
    Abstract model that provides automatic timestamp tracking.
    
    Adds created_at and updated_at fields that are automatically
    managed by Django when records are created or modified.
    """
    created_at = models.DateTimeField(
        db_index=True, auto_now_add=True, verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_('Updated at')
    )

    class Meta:
        abstract = True


class BaseModel(CodeModel, TimestampedModel, UUIDModel, SignalsModel):
    """
    Base abstract model that combines common functionality.
    
    Inherits from CodeModel (provides code/name fields), TimestampedModel 
    (automatic timestamps), UUIDModel (UUID primary key), and SignalsModel 
    (Django signals integration).
    """

    class Meta:
        abstract = True

    _default_manager = SignalsManager


class TermsOfService(BaseModel):
    """
    Model to store Terms of Service content for different profile types.
    
    Allows different terms of service text for different user profiles
    (user, store, etc.) to be managed and displayed appropriately.
    """
    profile_type = models.CharField(
        max_length=18, choices=TERMS_OF_SERVICE_TYPES, null=True, blank=True,
        verbose_name=_('Profile Type'),
        help_text=_('Type of profile this terms of service applies to')
    )
    text = models.TextField(_('Terms of Service text'), blank=True,
                            help_text=_('The actual terms of service content')
                            )

    class Meta:
        verbose_name = _('Terms of Service')
        verbose_name_plural = _('Terms of service')


class SMTPSettings(BaseModel):
    """
    SMTP email server configuration settings.
    
    Stores email server connection details and security settings
    for sending emails from the application. Only one configuration
    can be active at a time.
    """
    host = models.CharField(max_length=200, blank=True, verbose_name=_('Host'),
                            help_text=_('SMTP server hostname or IP address'))
    port = models.IntegerField(blank=True, verbose_name=_('Port'),
                               help_text=_('SMTP server port (usually 587 for TLS or 465 for SSL)'))
    username = models.CharField(max_length=128, blank=True, verbose_name=_('User'),
                                help_text=_('Username for SMTP authentication'))
    password = models.CharField(max_length=128, blank=True, verbose_name=_('Password'),
                                help_text=_('Password for SMTP authentication'))
    use_tls = models.BooleanField(default=False, verbose_name=_('Use TLS'),
                                  help_text=_('Enable TLS encryption for secure connection'))
    use_ssl = models.BooleanField(default=False, verbose_name=_('Use SSL'),
                                  help_text=_('Enable SSL encryption for secure connection'))
    timeout = models.IntegerField(blank=True, default=10, verbose_name=_('Timeout'),
                                  help_text=_('Connection timeout in seconds'))
    ssl_keyfile = models.FileField(blank=True, null=True, verbose_name=_('SSL Keyfile'),
                                   help_text=_('SSL private key file for client certificate authentication'))
    ssl_certfile = models.FileField(blank=True, null=True, verbose_name=_('SSL Certfile'),
                                    help_text=_('SSL certificate file for client certificate authentication'))
    is_active = models.BooleanField(default=False, verbose_name=_('Active'),
                                    help_text=_('Whether this SMTP configuration is currently active'))

    class Meta:
        verbose_name = _('Email Settings')
        verbose_name_plural = _('Email Settings')

    def __str__(self):
        return '{}:{}'.format(self.host, self.port)

    def pre_save(self, save_kwargs):
        if save_kwargs["is_creation"] and type(self).objects.exists():
            raise ValueError("This model has already its record.")


class AuditLogEntry(LogEntry):
    """
    Proxy model for Django's LogEntry to provide audit logging functionality.
    
    Extends Django's built-in admin log to track administrative actions
    and changes made through the admin interface for auditing purposes.
    """

    class Meta:
        proxy = True
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        db_table = "django_admin_log"
        ordering = ['-action_time']


class TranslatableFieldMixin:
    label = None
    help_text = None
    title = None

    class Meta:
        abstract = True

    @property
    def label_text(self) -> str:
        return self._get_i18n(self.label)

    @property
    def help_text_text(self) -> str:
        return self._get_i18n(self.help_text)

    @property
    def title_text(self) -> str:
        return self._get_i18n(self.title)

    def _get_i18n(self, data, default_lang='en', fallbacks=("en", "pt-br", "es")) -> str:
        lang = (get_language() or default_lang).lower()
        # normalize pt-br
        if lang in {"pt", "pt_br", "pt-br"}: lang = "pt-br"
        if data is None:
            return ""
        # Handle string data - return as is
        if isinstance(data, str):
            return data
        # Handle dictionary data
        if isinstance(data, dict):
            if lang in data and data[lang]:
                return data[lang]
            # configurable fallbacks
            for fb in fallbacks:
                if fb in data and data[fb]:
                    return data[fb]
            # last resort: first value
            return next(iter(data.values()), "")
        # Handle other types by converting to string
        return str(data) if data else ""

    def pre_save(self, save_kwargs):
        # Ensure new instances have proper i18n structure
        if save_kwargs["is_creation"]:
            if not self.label or self.label == {}:
                self.label = {
                    "en": "",
                    "pt-br": "",
                    "es": ""
                }
            if not self.help_text or self.help_text == {}:
                self.help_text = {
                    "en": "",
                    "pt-br": "",
                    "es": ""
                }
