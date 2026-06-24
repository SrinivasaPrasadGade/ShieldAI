"""
Structured logging configuration for ShieldAI backend.

Uses structlog for JSON-formatted log output, suitable for production
log aggregation. Provides request ID injection and per-module loggers.
"""

import logging
import sys
import structlog
from contextvars import ContextVar

# Context variable for request ID propagation across async boundaries
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _add_request_id,
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the formatter for stdlib logging
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer()
            if log_level == "DEBUG"
            else structlog.processors.JSONRenderer(),
        ],
    )

    # Set up root handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Suppress noisy third-party loggers
    for noisy_logger in [
        "uvicorn.access",
        "httpcore",
        "httpx",
        "google.auth",
        "google.api_core",
        "grpc",
        "urllib3",
    ]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def _add_request_id(logger, method_name, event_dict):
    """Inject request ID from context variable into log entries."""
    rid = request_id_ctx.get("")
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger for a specific module.

    Args:
        name: Logger name, typically the module path (e.g., "shield_ai.scam")

    Returns:
        A structlog BoundLogger instance
    """
    return structlog.get_logger(name)
