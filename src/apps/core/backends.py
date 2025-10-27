import threading

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.files.storage import FileSystemStorage
from django.core.mail.backends.smtp import EmailBackend
from storages.backends.s3boto3 import S3Boto3Storage
from storages.utils import clean_name

from .models import SMTPSettings

UserModel = get_user_model()


class DatabaseEmailBackend(EmailBackend):
    """
    A wrapper that manages the SMTP network connection.
    """

    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None,
                 **kwargs):
        super().__init__(host, port, username, password,
                         use_tls, fail_silently, use_ssl, timeout,
                         ssl_keyfile, ssl_certfile, **kwargs)

        smtp_settings = SMTPSettings.objects.first()
        if smtp_settings:
            self.host = smtp_settings.host
            self.port = smtp_settings.port
            self.username = smtp_settings.username
            self.password = smtp_settings.password
            self.use_tls = smtp_settings.use_tls
            self.use_ssl = smtp_settings.use_ssl
            self.timeout = smtp_settings.timeout
            self.ssl_keyfile = smtp_settings.ssl_keyfile
            self.ssl_certfile = smtp_settings.ssl_certfile
            if self.use_ssl and self.use_tls:
                raise ValueError(
                    "EMAIL_USE_TLS/EMAIL_USE_SSL are mutually exclusive, so only set "
                    "one of those settings to True.")
            self.connection = None
            self._lock = threading.RLock()


class MultipleLoginModelBackend(ModelBackend):

    def authenticate(self, request, username='', password=None, **kwargs):
        if '@' in username:
            username_data = {'email': username}
        else:
            username_data = {'username': username}
        try:
            user = UserModel.objects.get(**username_data)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except UserModel.DoesNotExist:
            return None


class OverwriteS3Boto3Storage(S3Boto3Storage):

    def get_available_name(self, name, max_length=None):
        """Overwrite existing file with the same name."""
        name = clean_name(name)
        if self.exists(name):
            self.delete(name)
        return name


class OverwriteFileSystemStorage(FileSystemStorage):

    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            self.delete(name)
        return name
