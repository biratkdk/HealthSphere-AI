import json
import logging
from datetime import UTC, datetime
from logging.config import dictConfig

# Standard LogRecord attributes that should not be forwarded as structured fields
_LOG_RECORD_ATTRS = frozenset(
    {
        "name", "msg", "args", "created", "filename", "funcName", "levelname",
        "levelno", "lineno", "module", "msecs", "message", "pathname",
        "process", "processName", "relativeCreated", "stack_info", "thread",
        "threadName", "exc_info", "exc_text",
    }
)


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter.

    Emits a JSON line per log record. All extra fields passed via the ``extra``
    kwarg are included automatically, so callers do not need to know the fixed
    list of fields supported by this formatter.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Ensure record.message is populated
        record.message = record.getMessage()

        payload: dict = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.message,
        }

        # Forward all caller-supplied extra fields that aren't standard attrs
        for key, value in record.__dict__.items():
            if key not in _LOG_RECORD_ATTRS and not key.startswith("_") and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {"()": JsonFormatter}
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                }
            },
            "root": {"level": level, "handlers": ["default"]},
        }
    )
