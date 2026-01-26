"""Structured JSON logging for pipeline operations."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """Custom formatter to output logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.

        Args:
            record: Log record to format

        Returns:
            JSON string with timestamp, level, message, and context fields
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Add any extra fields from the record
        if hasattr(record, "context") and record.context:
            log_data["context"] = record.context

        return json.dumps(log_data)


def setup_logger(log_format: str = "json") -> logging.Logger:
    """Setup and configure the pipeline logger.

    Args:
        log_format: Output format - "json" or "text" (default: "json")

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logger("json")
        >>> logger.info("Processing started")
    """
    logger: logging.Logger = logging.getLogger("csv_postgres_pipeline")
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create stderr handler
    handler: logging.StreamHandler[Any] = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)

    # Set formatter based on format preference
    formatter: JSONFormatter | logging.Formatter
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        # Text format with timestamp
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def log_progress(message: str, context: dict[str, Any] | None = None) -> None:
    """Log progress information with optional context.

    Args:
        message: Progress message to log
        context: Optional dictionary of contextual information

    Example:
        >>> log_progress("Processing file", {"file": "data.csv", "rows": 1000})
    """
    logger: logging.Logger = logging.getLogger("csv_postgres_pipeline")
    logger.info(message, extra={"context": context or {}})


def log_error(message: str, context: dict[str, Any] | None = None) -> None:
    """Log error information with optional context.

    Args:
        message: Error message to log
        context: Optional dictionary of contextual information

    Example:
        >>> log_error(
        ...     "Validation failed",
        ...     {"file": "data.csv", "error": "Schema mismatch"}
        ... )
    """
    logger: logging.Logger = logging.getLogger("csv_postgres_pipeline")
    logger.error(message, extra={"context": context or {}})


def log_summary(message: str, context: dict[str, Any] | None = None) -> None:
    """Log summary information with optional context.

    Args:
        message: Summary message to log
        context: Optional dictionary of contextual information

    Example:
        >>> log_summary("Load complete", {"rows_loaded": 1000, "duration": 5.2})
    """
    logger: logging.Logger = logging.getLogger("csv_postgres_pipeline")
    logger.info(message, extra={"context": context or {}})


def log_warning(message: str, context: dict[str, Any] | None = None) -> None:
    """Log warning information with optional context.

    Args:
        message: Warning message to log
        context: Optional dictionary of contextual information

    Example:
        >>> log_warning("Empty CSV file", {"file": "data.csv", "rows": 0})
    """
    logger: logging.Logger = logging.getLogger("csv_postgres_pipeline")
    logger.warning(message, extra={"context": context or {}})
