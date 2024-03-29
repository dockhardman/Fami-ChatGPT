import dataclasses
import json
import logging
from pathlib import Path
from typing import Any, Dict, Text

from pydantic import BaseModel, BaseSettings
from rich.console import Console

from app.version import VERSION


console = Console()


def is_serializable(obj: Any):
    try:
        if isinstance(obj, BaseModel):
            obj.json()
        elif dataclasses.is_dataclass(obj):
            json.dumps(dataclasses.asdict(obj))
        else:
            json.dumps(obj)
        return True
    except TypeError:
        return False


class Settings(BaseSettings):
    # General
    app_name: str = "GPT-API"
    app_version: str = VERSION
    app_timezone: str = "Asia/Taipei"
    data_dir: Text = "data"

    # Logging Config
    logger_name: str = "gpt_api"
    app_logger_name = logger_name
    app_logger_level: str = "DEBUG"
    log_error_filename: Text = "error.log"
    log_service_filename: Text = "service.log"
    openai_record_logger_name: str = "openai_record"

    log_dir: Text = "log"
    log_openai_record_filename: Text = "openai_record.log"

    # OpenAI Config
    openai_api_key: str = "sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    openai_organization: str = "org-************************"

    # External Service Config


settings = Settings()


class LoggingConfig(BaseSettings):
    version = 1
    disable_existing_loggers = False
    formatters = {
        "basic_formatter": {
            "format": "%(asctime)s %(levelname)-8s %(name)s  - %(message)s",
        },
        "json_formatter": {
            "format": "%(json_message)s",
        },
    }
    handlers = {
        "console_handler": {
            "level": settings.app_logger_level,
            "class": "rich.logging.RichHandler",
            "rich_tracebacks": True,
            "show_path": False,
            "tracebacks_show_locals": False,
        },
        "file_handler": {
            "level": settings.app_logger_level,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": (
                Path(settings.log_dir).joinpath(settings.log_service_filename).resolve()
            ),
            "formatter": "basic_formatter",
            "maxBytes": 2097152,
            "backupCount": 10,
        },
        "error_handler": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": (
                Path(settings.log_dir).joinpath(settings.log_error_filename).resolve()
            ),
            "formatter": "basic_formatter",
        },
        "openai_handler": {
            "level": settings.app_logger_level,
            "class": "logging.FileHandler",
            "filename": (
                Path(settings.log_dir)
                .joinpath(settings.log_openai_record_filename)
                .resolve()
            ),
            "formatter": "json_formatter",
        },
    }
    loggers = {
        settings.app_logger_name: {
            "level": settings.app_logger_level,
            "handlers": ["console_handler", "file_handler", "error_handler"],
            "propagate": True,
        },
        settings.openai_record_logger_name: {
            "level": settings.app_logger_level,
            "handlers": ["openai_handler"],
            "propagate": True,
        },
    }


default_log_record_factory = logging.getLogRecordFactory()


def custom_log_record_factory(*args, **kwargs):
    record = default_log_record_factory(*args, **kwargs)

    if is_serializable(record.msg):
        if isinstance(record.msg, BaseModel):
            record.json_message = record.msg.json(ensure_ascii=False)
        elif dataclasses.is_dataclass(record.msg):
            record.json_message = json.dumps(
                dataclasses.asdict(record.msg), ensure_ascii=False
            )
        elif isinstance(record.msg, Dict):
            record.json_message = json.dumps(record.msg, ensure_ascii=False)
    return record


logging_config = LoggingConfig()
logging.config.dictConfig(logging_config)

default_factory = logging.getLogRecordFactory()
logging.setLogRecordFactory(custom_log_record_factory)

logger = logging.getLogger(settings.app_logger_name)
openai_logger = logging.getLogger(settings.openai_record_logger_name)
