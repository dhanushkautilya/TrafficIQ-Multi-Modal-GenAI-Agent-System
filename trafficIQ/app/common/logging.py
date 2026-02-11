"""Structured logging configuration for TrafficIQ."""

import logging
import sys
from typing import Optional
import structlog


def setup_logging(log_level: str = "info", json_logging: bool = True) -> None:
    """Configure structured logging with JSON output."""
    log_level_num = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatter
    if json_logging:
        formatter_config = structlog.make_filtering_bound_logger(logging.INFO)
    else:
        formatter_config = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if not json_logging else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level_num)
    
    if json_logging:
        handler.setFormatter(logging.Formatter(
            fmt='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        ))
    else:
        handler.setFormatter(formatter_config)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_num)
    root_logger.addHandler(handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name)
