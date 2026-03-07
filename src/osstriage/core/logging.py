"""Structured logging setup for OSSTriage."""

from __future__ import annotations

import logging
import sys

from rich.logging import RichHandler


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the root OSSTriage logger.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Configured logger instance for the ``osstriage`` namespace.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger("osstriage")
    logger.setLevel(numeric_level)

    # Avoid adding duplicate handlers on repeated calls
    if not logger.handlers:
        console_handler = RichHandler(
            level=numeric_level,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=False,
        )
        console_handler.setFormatter(
            logging.Formatter("%(message)s", datefmt="[%X]")
        )
        logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("github").setLevel(logging.WARNING)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the ``osstriage`` namespace.

    Args:
        name: Sub-logger name (e.g. ``github_client``).

    Returns:
        A child logger instance.
    """
    return logging.getLogger(f"osstriage.{name}")
