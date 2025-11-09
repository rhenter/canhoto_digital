import datetime
import json
import logging
import os
import sys
import urllib
import warnings
from urllib.parse import quote
from datetime import timedelta

import sentry_sdk
from corsheaders.defaults import default_headers
from dj_database_url import parse as parse_db_url
from django.core.management.utils import get_random_secret_key
from django.utils.translation import gettext_lazy as _
from django_cache_url import parse as parse_cache_url
from kombu import Exchange, Queue
from kombu.utils.url import safequote
from prettyconf import config
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from unipath import Path

from .logging import get_logging

# pkg_resources deprecated filter
warnings.filterwarnings("ignore", ".*pkg_resources is deprecated.*")

# Project Structure
BASE_DIR = Path(__file__).ancestor(3)
PROJECT_DIR = Path(__file__).ancestor(2)
FRONTEND_DIR = PROJECT_DIR.child("frontend")
SETTINGS_FOLDER = 'proj_settings'

# App version
APP_VERSION = '0.1.0'
APP_NAME = config("APP_NAME", default='Canhoto Digital')
APP_SLUG = config("APP_NAME", default='digital_delivery_receipt')

# Developer Info
ENV = config("ENVIRONMENT", default='dev')
ENVIRONMENT_TYPES = {
    'local': _('Local'),
    'dev': _('Development'),
    'qa': _('QA'),
    'prd': _('Production'),
}
ENVIRONMENT_NAME = ENVIRONMENT_TYPES.get(ENV, ENV)
DEVELOPER_NAME = config("DEVELOPER_NAME", default='Henter4Dev')
DEVELOPER_WEBSITE = config("DEVELOPER_WEBSITE", default='')

WEBSITE_DEFAULT = f'.{ENV}.henter.com.br'
WEBSITE = config("WEBSITE", default=WEBSITE_DEFAULT)

PROJECT_DOMAIN = config("PROJECT_DOMAIN", default=f'{ENV}.henter.com.br')

# Debug & Development
DEBUG = config("DEBUG", default=False, cast=config.boolean)

# Database
default_dburl = 'sqlite:///{}/db.sqlite3'.format(PROJECT_DIR)

REPLICA_DATABASES = config("REPLICA_DATABASES", default=[], cast=config.list)
PERSISTENT_CONNECTIONS = config("PERSISTENT_CONNECTIONS", default=False, cast=config.boolean)

DATABASES = {
    'default': config('DATABASE_URL', default=default_dburl, cast=parse_db_url),
}

if PERSISTENT_CONNECTIONS:
    DATABASES['default']['CONN_MAX_AGE'] = None  # unlimited persistent connections.

# Check if we're running tests
TESTING = 'test' in sys.argv or 'pytest' in sys.modules or os.environ.get('TESTING')

# Use SQLite for testing to avoid accessing real PostgreSQL database
if TESTING:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',  # Use in-memory database for faster tests
        }
    }
else:
    DATABASES = {
        'default': config('DATABASE_URL', default=default_dburl, cast=parse_db_url),
    }

if PERSISTENT_CONNECTIONS and not TESTING:
    DATABASES['default']['CONN_MAX_AGE'] = None  # unlimited persistent connections.

# Test database configuration (only needed for non-testing environments)
if not TESTING:
    test_name = config("TEST_DATABASE_NAME",
                       default=f"test_{DATABASES['default'].get('NAME', 'proj_settings_test')}", cast=str)
    DATABASES['default']['TEST'] = {'NAME': test_name}

DEFAULT_DATABASE_KEY = 'default'

if REPLICA_DATABASES and not TESTING:
    for i, replica_database_url in enumerate(REPLICA_DATABASES, 1):
        DATABASES[f'replica_{i}'] = parse_db_url(replica_database_url)

    REPLICA_DATABASES = list(filter(lambda key: key.startswith('replica'), DATABASES.keys()))
    DATABASE_ROUTERS = [
        f'{SETTINGS_FOLDER}.db_router.MasterReplicaRouter'
    ]

COLLECTORS_DATABASE_URL = config('COLLECTORS_DATABASE_URL', default='')
if COLLECTORS_DATABASE_URL:
    DATABASES[f'collectors'] = parse_db_url(COLLECTORS_DATABASE_URL)

# Use PostGIS backend when PostgreSQL is configured
if not TESTING:
    engine = DATABASES['default'].get('ENGINE', '')
    if engine.endswith('postgresql') or engine.endswith('postgresql_psycopg2'):
        DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'

#  Security & Signup/Signin
ADMIN_USERNAME = config('ADMIN_USERNAME', default='admin')

_ALLOWED_HOSTS = f"*,{PROJECT_DOMAIN}"
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default=_ALLOWED_HOSTS, cast=config.list)
CSRF_TRUSTED_ORIGINS = [f"https://{PROJECT_DOMAIN}", f"http://{PROJECT_DOMAIN}"]
SECRET_KEY = config('SECRET_KEY', default=get_random_secret_key())
#  Media & Static
MEDIA_URL = "/media/"
MEDIA_ROOT = config('MEDIA_ROOT', default=FRONTEND_DIR.child("media"))

STATIC_URL = config('STATIC_URL', default='/static/')
STATIC_ROOT = config(
    'STATIC_ROOT', default=str(PROJECT_DIR.child('staticfiles'))
)

STATICFILES_DIRS = [
    FRONTEND_DIR.child("static"),
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
)

# Media Files
USE_S3_BACKEND = config('USE_S3_BACKEND', default=False, cast=bool)
USE_S3_FOR_STATICS = config('USE_S3_FOR_STATICS', default=False, cast=bool)
ASSESTS_STORAGE_ROOT = config('ASSESTS_STORAGE_ROOT', default='assets/')
DOCUMENTS_STORAGE_ROOT = config('DOCUMENTS_STORAGE_ROOT', default='documents/')

# Storage
STORAGES = {
    "default": {
        "BACKEND": 'apps.core.backends.OverwriteFileSystemStorage',
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Backend Storage AWS S3
if USE_S3_BACKEND:
    STORAGES["default"] = {"BACKEND": 'apps.core.backends.OverwriteS3Boto3Storage'}

    if USE_S3_FOR_STATICS:
        STORAGES["staticfiles"] = {"BACKEND": "storages.backends.s3boto3.S3StaticStorage"}
        ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_REGION_NAME = config('AWS_REGION_NAME', default='us-east-2')

AWS_DEFAULT_ACL = None
S3_AWS_STORAGE_BUCKET_NAME = config('S3_AWS_STORAGE_BUCKET_NAME', default='canhoto_digital')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default=S3_AWS_STORAGE_BUCKET_NAME)

AWS_LOCATION = config('AWS_LOCATION', default='')
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_S3_FILE_OVERWRITE = True
AWS_QUERYSTRING_EXPIRE = '3600'

AWS_CONFIG = {
    'aws_access_key_id': AWS_ACCESS_KEY_ID,
    'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
    'region_name': AWS_REGION_NAME
}

AWS_S3_REGION_NAME = AWS_REGION_NAME
AWS_S3_SIGNATURE_VERSION = 's3v4'

AWS_S3_HOST = AWS_REGION_NAME
S3_USE_SIGV4 = True

# SQS Settings
SQS_CONTENT_BASED_DEDUPLICATION = config("SQS_CONTENT_BASED_DEDUPLICATION", default=True, cast=config.boolean)
SQS_FIFO_QUEUE = config("SQS_FIFO_QUEUE", default=False, cast=config.boolean)
SQS_RECEIVE_MESSAGE_WAIT_TIME_SECONDS = config("SQS_RECEIVE_MESSAGE_WAIT_TIME_SECONDS", default="10", cast=int)
SQS_VISIBILITY_TIMEOUT = config("SQS_VISIBILITY_TIMEOUT", default="300", cast=int)

# Application definition
INSTALLED_APPS = (
    'clearcache',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    # 3rd party libs
    'django_filters',
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
    'django_celery_beat.apps.BeatConfig',
    'drf_yasg',
    'django_models',
    'django.forms',
    # Local
    'apps.user.apps.UserConfig',
    'apps.core.apps.CoreConfig',
    'apps.celery_log.apps.CeleryLogConfig',
    "apps.company.apps.CompanyConfig",
    "apps.invoice.apps.InvoiceConfig",
    "apps.delivery.apps.DeliveryConfig",
)

MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'proj_settings.audit.AuditLogMiddleware',
]

ROOT_URLCONF = '{}.urls'.format(SETTINGS_FOLDER)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': (
            FRONTEND_DIR.child("templates"),
        ),
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': config(
                "TEMPLATE_DEBUG",
                default=DEBUG,
                cast=config.boolean),
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.environment_info',
            ],
        },
    },
]
FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

WSGI_APPLICATION = f'{SETTINGS_FOLDER}.wsgi.application'

AUTHENTICATION_BACKENDS = (
    'apps.core.backends.MultipleLoginModelBackend',
    'django.contrib.auth.backends.ModelBackend'
)

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/
TIME_ZONE = 'UTC'
USE_I18N = True
# USE_L10N = True
USE_TZ = True
LANGUAGES = (
    ("en", "English"),
    ("es", "Spanish"),
    ("pt-br", "Portuguese (BR)"),
)
LANGUAGE_CODE = 'en'
LOCALE_PATHS = (
    PROJECT_DIR.child("locale"),
)

DECIMAL_SEPARATOR = ','
USE_THOUSAND_SEPARATOR = True

CORS_ALLOW_ALL_ORIGINS = True
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_HEADERS = (
    "accept",
    "accept-encoding",
    "accept-language",
    "accept-timezone",
    "access-control-allow-headers",
    "authorization",
    "content-disposition",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-timezone",
)

LOGIN_URL = "/"
LOGOUT_URL = "/logout/"
LOGIN_REDIRECT_URL = "/doc/"

# Logging
API_LOG_CELERY_JSON = config("API_LOG_CELERY_JSON", default=True, cast=config.boolean)
API_LOG_ROOT = config("API_LOG_ROOT", default='')

LOGGER_LEVEL = config("LOGGER_LEVEL", default="INFO")
LOG_FILE_SAVE = config("LOG_FILE_SAVE", default=False, cast=config.boolean)
LOG_PATH = config("LOG_PATH", default="/tmp")
LOG_NAME = config("LOG_NAME", default="django.log")

LOGGING_FORMATER = config("LOGGING_FORMATER", default="simple")

if LOG_FILE_SAVE:
    LOGGING_FORMATER = 'json'

LOGGING = get_logging(LOGGING_FORMATER)

SENTRY_DSN_URL = config("SENTRY_DSN_URL", default='')
if SENTRY_DSN_URL:
    sentry_sdk.init(
        dsn=SENTRY_DSN_URL,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True,
    )

API_LOG_APPLICATION_LEVEL = config("API_LOG_APPLICATION_LEVEL", default=LOGGER_LEVEL)
API_LOG_CELERY_LEVEL = config("API_LOG_CELERY_LEVEL", default='INFO')
API_LOG_ERROR_LEVEL = config("API_LOG_ERROR_LEVEL", default='DEBUG')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# EMAIL Authentication Settings
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

EMAIL_ADMIN = config("EMAIL_ADMIN", default='')

EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=config.boolean)
EMAIL_HOST = config("EMAIL_HOST", default='localhost')
EMAIL_PORT = config("EMAIL_PORT", default=25, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default='')
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default='')
DEFAULT_FROM_EMAIL = config("FROM_EMAIL", default='HenterDevs <donotreply@henter.com.br>')

SEND_EMAIL_NOTIFICATION = config('SEND_EMAIL_NOTIFICATION', default=False, cast=config.boolean)
SEND_EMAIL_SUPPORT_NOTIFICATION = config('SEND_EMAIL_SUPPORT_NOTIFICATION', default=False, cast=config.boolean)

PICTURES = {
    "BREAKPOINTS": {
        "xs": 356,
        "s": 768,
        "m": 992,
        "l": 1200,
        "xl": 1400,
    },
    "GRID_COLUMNS": 12,
    "CONTAINER_WIDTH": 1200,
    "FILE_TYPES": ["JPG"],
    "PIXEL_DENSITIES": [1, 2],
}

# Celery
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_CREATE_MISSING_QUEUES = True
CELERY_ENABLE_REMOTE_CONTROL = False
CELERY_ENABLE_UTC = True
CELERY_RESULT_SERIALIZER = 'json'
CELERY_SEND_EVENTS = False
CELERY_TIMEZONE = TIME_ZONE

CELERY_BROKER_URL = config('BROKER_URL', default='')
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_POOL_LIMIT = None  # Adjust depending on the workload
CELERY_BROKER_HEARTBEAT = 30  # Adjust depending on the workload
CELERY_BROKER_TRANSPORT = config('BROKER_TRANSPORT', default="redis")
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'max_retries': 10,
    'visibility_timeout': 3600,
    "worker_enable_remote_control": False,
    "retry_delay": 5,
}

if CELERY_BROKER_TRANSPORT == 'sqs':
    aws_access_key = safequote(AWS_ACCESS_KEY_ID)
    aws_secret_key = safequote(AWS_SECRET_ACCESS_KEY)
    CELERY_BROKER_URL = f"sqs://{aws_access_key}:{aws_secret_key}@"

    CELERY_BROKER_TRANSPORT_OPTIONS.update({
        'region': AWS_REGION_NAME,
        'polling_interval': 30,
        'wait_time_seconds': 2
    })

CELERY_DEFAULT_ROUTING_KEY = config('CELERY_DEFAULT_ROUTING_KEY', default='celery')
CELERY_DEFAULT_EXCHANGE = config('CELERY_DEFAULT_EXCHANGE', default='default')
CELERY_DEFAULT_EXCHANGE_TYPE = config('CELERY_DEFAULT_EXCHANGE_TYPE', default='direct')
CELERY_DEFAULT_QUEUE = config('CELERY_DEFAULT_QUEUE', default='celery')

CELERY_WORKER_CONCURRENCY = 2
CELERY_WORKER_DEDUPLICATE_SUCCESSFUL_TASKS = True
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

CELERY_TASK_DEFAULT_QUEUE = config('CELERY_TASK_DEFAULT_QUEUE', default=CELERY_DEFAULT_QUEUE)
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_SERIALIZER = 'json'
CELERY_TASK_SOFT_TIME_LIMIT = 3840
CELERY_TASK_TIME_LIMIT = 3900

# Celery Logs expires in days
CELERY_TASK_LOGS_EXPIRES = config('CELERY_TASK_LOGS_EXPIRES', default=2, cast=int)

CELERY_TASK_IGNORE_RESULT = True

CELERY_PREFETCH_MULTIPLIER = 1

# Celery Queues Names
CELERY_HIGH_PRIORITY_QUEUE = config('CELERY_HIGH_PRIORITY_QUEUE', default='highpriority')

# Celery Queues Configs
CELERY_MEDIA_EXCHANGE = config('CELERY_MEDIA_EXCHANGE', default='media')
CELERY_MEDIA_EXCHANGE_TYPE = config('CELERY_MEDIA_EXCHANGE_TYPE', default='media')
CELERY_MEDIA_ROUTING_KEY = config('CELERY_MEDIA_ROUTING_KEY', default='media.image')

DEFAULT_EXCHANGE = Exchange(CELERY_DEFAULT_EXCHANGE, type=CELERY_DEFAULT_EXCHANGE_TYPE)
MEDIA_EXCHANGE = Exchange(CELERY_MEDIA_EXCHANGE, type=CELERY_MEDIA_EXCHANGE_TYPE)

CELERY_QUEUES = (
    Queue(CELERY_DEFAULT_QUEUE, DEFAULT_EXCHANGE, routing_key=CELERY_DEFAULT_ROUTING_KEY),
    Queue(CELERY_HIGH_PRIORITY_QUEUE, MEDIA_EXCHANGE, routing_key=CELERY_HIGH_PRIORITY_QUEUE),
)
# Celery Results settings
CELERY_RESULT_EXTENDED = True

# Swagger configs
SWAGGER_SETTINGS = {
    'SUPPORTED_SUBMIT_METHODS': ['get', 'post', 'put', 'delete', 'patch'],  # default
    'JSON_EDITOR': False,
    'SECURITY_DEFINITIONS': {
        'Token': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        },
    },
    'LOGIN_URL': LOGIN_URL,
    'LOGOUT_URL': LOGOUT_URL,
}

REDOC_SETTINGS = {
    'NATIVE_SCROLLBARS': True,
}

MAP_WIDGETS = {
    "GooglePointFieldWidget": (
        ("zoom", 12),
        ("mapCenterLocationName", 'brazil'),
    ),
    "GOOGLE_MAP_API_KEY": config('GOOGLE_API_KEY', default=''),
}

# Django REST Framework

AUTH_USER_MODEL = "user.User"
DATE_FORMAT = '%d/%m/%Y'
DATETIME_FORMAT = 'iso-8601'
DATE_INPUT_FORMATS = (
    '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d',
    '%m-%d-%Y', '%d-%m-%Y',
)
DATETIME_INPUT_FORMATS = [
    '%m/%d/%Y',  # '2006-10-25'
    '%Y-%m-%d',  # '2006-10-25'
    '%d/%m/%Y',  # '25/10/2006'
    '%Y-%m-%d %H:%M',  # '2006-10-25 14:30'
    '%d/%m/%Y %H:%M',  # '25/10/2006 14:30'
    '%d/%m/%Y %H:%M:%S',  # '25/10/2006 14:30:00'
    '%d/%m/%Y %H:%M:%S.%f',  # '25/10/2006 14:30:00.1234123'
    '%m/%d/%Y %H:%M',  # '10/25/2006 14:30'
    '%m/%d/%Y %H:%M:%S',  # '10/25/2006 14:30:00'
    '%m/%d/%Y %H:%M:%S %Z',  # '10/25/2006 14:30:00 UTC'
    '%m/%d/%Y %H:%M:%S %z',  # '10/25/2006 14:30:00 +0000'
    '%m/%d/%Y %H:%M:%S.%f',  # '10/25/2006 14:30:00.12332'
    'iso-8601',
]

DEFAULT_USER_RATE = config("DRF_USER_RATE", default="200", cast=int)
DEFAULT_ANON_RATE = config("DRF_ANON_RATE", default="30", cast=int)

REST_FRAMEWORK = {
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication'
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter'
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    # 'DEFAULT_THROTTLE_CLASSES': (
    #     "rest_framework.throttling.UserRateThrottle",
    #     "rest_framework.throttling.AnonRateThrottle",
    # ),
    # 'DEFAULT_THROTTLE_RATES': (
    #     ('user', DEFAULT_USER_RATE),
    #     ('anon', DEFAULT_ANON_RATE),
    # ),
    "DATE_INPUT_FORMATS": DATE_INPUT_FORMATS,
    "DATE_FORMAT": DATE_FORMAT,
    "DATETIME_INPUT_FORMATS": DATETIME_INPUT_FORMATS
}

CACHES = {
    'default': config('CACHE_URL', default='redis://localhost', cast=parse_cache_url)
}

CACHE_KEY_PREFIX = "digital_delivery_receipt:"

CACHE_TIMEOUTS = {
    "core": config("CACHE_CORE_TIMEOUT", default=300, cast=int),
    "dashboard": config("CACHE_DASH_TIMEOUT", default=120, cast=int),
}

CACHE_CORE_KEY = f"{CACHE_KEY_PREFIX}core*"
CACHE_DASHBOARD_KEY = f"{CACHE_KEY_PREFIX}dashboard*"

if 'redis' in CACHES['default']['LOCATION']:
    CACHES['default']['BACKEND'] = "django_redis.cache.RedisCache"
    CACHES['default']['KEY_PREFIX'] = CACHE_KEY_PREFIX
    CACHES['default']['TIMEOUT'] = CACHE_TIMEOUTS["core"]
    CACHES['default']["OPTIONS"] = {
        "CLIENT_CLASS": "django_redis.client.DefaultClient",
        "IGNORE_EXCEPTIONS": True,
    }

CACHED_SERIALIZER_TIMEOUT = config(
    'CACHED_SERIALIZER_TIMEOUT',
    default='120',
    cast=config.eval)

APPEND_SLASH = True

DATA_UPLOAD_MAX_NUMBER_FIELDS = 20240

# This value is in minutes
ACTIVATE_CODE_EXPIRATION = config(
    'ACTIVATE_CODE_EXPIRATION',
    default='3',
    cast=config.eval)

# Integrations
# Authentication: OAuth2
OAUTH2_PROVIDER = {
    'SCOPES': {
        'read': 'Read scope',
        'write': 'Write scope',
        'groups': 'Access to your groups'
    },
    # Default 20 days
    'ACCESS_TOKEN_EXPIRE_SECONDS': config('ACCESS_TOKEN_EXPIRE_SECONDS', default=1728000),
    # Default 30 days
    'REFRESH_TOKEN_EXPIRE_SECONDS': config('REFRESH_TOKEN_EXPIRE_SECONDS', default=2592000),
}

# Push Notification Integrations
ONE_SIGNAL_API_URL = config('ONE_SIGNAL_API_URL', default='https://onesignal.com/api/v1')
PUSH_NOTIFICATION_API_URL = config('PUSH_NOTIFICATION_API_URL', default=f'{ONE_SIGNAL_API_URL}/notifications')
PUSH_NOTIFICATION_API_TOKEN = config('PUSH_NOTIFICATION_API_TOKEN', default='')
PUSH_NOTIFICATION_API_TIMEOUT = config('PUSH_NOTIFICATION_API_TIMEOUT', default=4, cast=int)
PUSH_NOTIFICATION_APP_ID = config('PUSH_NOTIFICATION_APP_ID', default='')
SEND_PUSH_NOTIFICATION = all((PUSH_NOTIFICATION_APP_ID, PUSH_NOTIFICATION_API_TOKEN))

# WhatsApp
WHATSAPP_PROVIDERS = {
    'WaboxApp': {
        'class': 'WaboxAppProvider',
        'access_token': config('WABOXAPP_TOKEN', default=''),
        'instance_id': config('WABOXAPP_UID', default=''),
        'timeout': config('WHATSAPP_API_TIMEOUT', default=20, cast=int)
    },
    'ChatAPI': {
        'class': 'ChatAPIProvider',
        'access_token': config('CHAT-API_TOKEN', default=''),
        'instance_id': config('CHAT-API_INSTANCE_ID', default=''),
        'timeout': config('WHATSAPP_API_TIMEOUT', default=20, cast=int)
    }
}
DEFAULT_WHATSAPP_PROVIDER = config(
    'DEFAULT_WHATSAPP_PROVIDER',
    default='ChatAPI')
SEND_WHATSAPP_NOTIFICATION = bool(
    WHATSAPP_PROVIDERS['WaboxApp']['access_token'] or WHATSAPP_PROVIDERS['ChatAPI']['access_token'])

CKEDITOR_BASEPATH = STATIC_URL + "ckeditor/ckeditor/"
CKEDITOR_UPLOAD_PATH = "uploads/"

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['heading', '|', 'bold', 'italic', 'link',
                    'bulletedList', 'numberedList', 'blockQuote', 'imageUpload', ],

    },
    'extends': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': ['heading', '|', 'outdent', 'indent', '|', 'bold', 'italic', 'link', 'underline', 'strikethrough',
                    'highlight', '|', 'codeBlock', 'sourceEditing', 'insertImage',
                    'bulletedList', 'numberedList', 'todoList', '|', 'blockQuote', 'imageUpload', '|',
                    'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', 'mediaEmbed', 'removeFormat',
                    'insertTable', ],
        'image': {
            'toolbar': ['imageTextAlternative', '|', 'imageStyle:alignLeft',
                        'imageStyle:alignRight', 'imageStyle:alignCenter', 'imageStyle:side', '|'],
            'styles': [
                'full',
                'side',
                'alignLeft',
                'alignRight',
                'alignCenter',
            ]

        },

    },
    'list': {
        'properties': {
            'styles': 'true',
            'startIndex': 'true',
            'reversed': 'true',
        }
    }
}

DRF_YASG_EXCLUDE_VIEWS = [
    'health_check',
]

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("JWT_ACCESS_MINUTES", default="30", cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("JWT_REFRESH_DAYS", default="7", cast=int)),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

TOKEN_OBTAIN_SERIALIZER = 'core.serializers.CustomTokenObtainPairSerializer'

GDAL_LIBRARY_PATH = config('GDAL_LIBRARY_PATH', default='/opt/homebrew/opt/gdal/lib/libgdal.dylib')
GEOS_LIBRARY_PATH = config('GEOS_LIBRARY_PATH', default='/opt/homebrew/opt/geos/lib/libgeos_c.dylib')


# Business Rules
TERMS_OF_USE_VERSION_CURRENT = 1

# SEFAZ e Integrations
SEFAZ_HTTP_TIMEOUT_SECONDS = config('SEFAZ_HTTP_TIMEOUT_SECONDS', default='60', cast=config.eval)
SEFAZ_COOLDOWN_MINUTES = config('SEFAZ_COOLDOWN_MINUTES', default=60, cast=int)
