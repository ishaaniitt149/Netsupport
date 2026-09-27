"""Structured logging configuration for the platform."""

import logging
import sys

from app.core.config import get_settings


class StructuredFormatter(logging.Formatter):
    """Formats log records with structured metadata."""

    def format(self, record: logging.LogRecord) -> str:
        # Standard format
        return super().format(record)


def configure_logging(level: str | None = None) -> logging.Logger:
    """Initialize structured logging across the application."""
    settings = get_settings()
    log_level = level or settings.log_level.upper()

    numeric_level = getattr(logging, log_level, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers to prevent duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    logger = logging.getLogger(settings.app_name)
    logger.info("Logging configured with level: %s", log_level)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a namespaced logger instance."""
    return logging.getLogger(name)
