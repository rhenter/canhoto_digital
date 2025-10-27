import logging
import warnings
from typing import Dict

from django.conf import settings

warnings.simplefilter("default")

logger = logging.getLogger(__name__)


def get_logging_as_simple_format() -> Dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
            },
        },
        "handlers": {
            "console": {
                "level": settings.LOGGER_LEVEL,
                "class": "logging.StreamHandler",
                "formatter": "simple",
            },
        },
        "root": {
            "level": settings.LOGGER_LEVEL,
            "handlers": [],
        },
        "loggers": {
            "django": {
                "handlers": ["console"],
                "level": settings.LOGGER_LEVEL,
                "propagate": True,
            },
            "django.request": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False,
            },
            'django.server': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'celery': {
                'handlers': ['console'],
                'level': settings.LOGGER_LEVEL,
                'propagate': True,
            },
            "celery.task": {
                "handlers": ["console"],
                "level": settings.LOGGER_LEVEL,
                "propagate": True,
            },
        },
    }


def get_logging_as_json_format() -> Dict:
    if logger.hasHandlers():
        logger.handlers.clear()

    logging_config = get_logging_as_simple_format()
    logging_config["formatters"]["json"] = {"()": "json_log_formatter.JSONFormatter"}
    logging_config["handlers"]["console"]["formatter"] = "json"
    logging_config["root"]["handlers"] = ["console"]
    logging_config["loggers"]["django"]["handlers"] = ["console"]
    logging_config["loggers"]["celery"]["handlers"] = ["console"]

    if settings.LOG_FILE_SAVE:
        logging_config["handlers"]["json_file"] = {
            "class": "logging.FileHandler",
            "filename": f"{settings.LOG_PATH}/{settings.LOG_NAME}",
            "formatter": "json",
        }
        logging_config["loggers"]["django"]["handlers"] = ["json_file"]
        logging_config["root"]["handlers"] = ["json_file"]

    return logging_config


def get_logging_as_systemd_format() -> Dict:
    if logger.hasHandlers():
        logger.handlers.clear()

    logging_config = get_logging_as_simple_format()
    try:
        from systemd.journal import JournalHandler
        logging_config["formatters"]["systemd"] = {"format": "%(message)s"}
        logging_config["handlers"]["systemd"] = {
            "level": settings.LOGGER_LEVEL,
            "class": "systemd.journal.JournalHandler",
            "formatter": "systemd",
        }
        logging_config["root"]["handlers"].append("systemd")
        logging_config["loggers"]["django"]["handlers"].append("systemd")
    except ImportError:
        # Fallback to console if systemd is not available
        pass

    return logging_config


def get_logging(log_formatter="simple") -> Dict:
    if log_formatter == "json":
        return get_logging_as_json_format()
    elif log_formatter == "systemd":
        return get_logging_as_systemd_format()
    else:
        return get_logging_as_simple_format()
