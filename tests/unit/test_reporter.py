"""Unit tests for reporter module."""

import json
import logging
import sys
from io import StringIO

from src.csv_postgres_pipeline.reporter import (
    JSONFormatter,
    log_error,
    log_progress,
    log_summary,
    setup_logger,
)


class TestJSONFormatter:
    """Tests for JSONFormatter class."""

    def test_json_formatter_basic_message(self) -> None:
        """Test JSON formatter with basic message."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "timestamp" in data
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["timestamp"].endswith("Z")  # UTC timezone

    def test_json_formatter_with_context(self) -> None:
        """Test JSON formatter includes context field."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )
        record.context = {"file": "data.csv", "row": 42}

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "ERROR"
        assert data["message"] == "Error occurred"
        assert "context" in data
        assert data["context"]["file"] == "data.csv"
        assert data["context"]["row"] == 42

    def test_json_formatter_without_context(self) -> None:
        """Test JSON formatter handles missing context gracefully."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Simple message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "timestamp" in data
        assert "level" in data
        assert "message" in data
        # Context should not be present if not provided
        assert "context" not in data or data.get("context") is None


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_setup_logger_json_format(self) -> None:
        """Test logger setup with JSON format."""
        logger = setup_logger("json")

        assert logger.name == "csv_postgres_pipeline"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, JSONFormatter)
        assert not logger.propagate

    def test_setup_logger_text_format(self) -> None:
        """Test logger setup with text format."""
        logger = setup_logger("text")

        assert logger.name == "csv_postgres_pipeline"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, logging.Formatter)
        assert not isinstance(logger.handlers[0].formatter, JSONFormatter)

    def test_setup_logger_default_format(self) -> None:
        """Test logger setup with default format (JSON)."""
        logger = setup_logger()

        assert logger.name == "csv_postgres_pipeline"
        assert isinstance(logger.handlers[0].formatter, JSONFormatter)

    def test_setup_logger_removes_existing_handlers(self) -> None:
        """Test that setup_logger clears existing handlers."""
        # Setup logger twice
        logger1 = setup_logger("json")
        handler_count_1 = len(logger1.handlers)

        logger2 = setup_logger("json")
        handler_count_2 = len(logger2.handlers)

        # Should have same number of handlers (old ones removed)
        assert handler_count_1 == handler_count_2 == 1


class TestLogFunctions:
    """Tests for log_progress, log_error, log_summary functions."""

    def test_log_progress_basic(self) -> None:
        """Test log_progress with basic message."""
        # Setup logger with JSON format and capture handler
        # Get the logger and replace its handler's stream
        logger = setup_logger("json")
        fake_stream = StringIO()
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler), "Handler must be StreamHandler"
        handler.stream = fake_stream

        log_progress("Processing started")

        output = fake_stream.getvalue()
        data = json.loads(output.strip())

        assert data["level"] == "INFO"
        assert data["message"] == "Processing started"
        assert "timestamp" in data

    def test_log_progress_with_context(self) -> None:
        """Test log_progress with context data."""
        logger = setup_logger("json")
        fake_stream = StringIO()
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler), "Handler must be StreamHandler"
        handler.stream = fake_stream

        log_progress("Processing file", {"file": "data.csv", "rows": 1000})

        output = fake_stream.getvalue()
        data = json.loads(output.strip())

        assert data["level"] == "INFO"
        assert data["message"] == "Processing file"
        assert data["context"]["file"] == "data.csv"
        assert data["context"]["rows"] == 1000

    def test_log_error_basic(self) -> None:
        """Test log_error with basic message."""
        logger = setup_logger("json")
        fake_stream = StringIO()
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler), "Handler must be StreamHandler"
        handler.stream = fake_stream

        log_error("Validation failed")

        output = fake_stream.getvalue()
        data = json.loads(output.strip())

        assert data["level"] == "ERROR"
        assert data["message"] == "Validation failed"

    def test_log_error_with_context(self) -> None:
        """Test log_error with context data."""
        logger = setup_logger("json")
        fake_stream = StringIO()
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler), "Handler must be StreamHandler"
        handler.stream = fake_stream

        log_error("Schema mismatch", {"expected": "col1,col2", "found": "col1"})

        output = fake_stream.getvalue()
        data = json.loads(output.strip())

        assert data["level"] == "ERROR"
        assert data["message"] == "Schema mismatch"
        assert "context" in data
        assert data["context"]["expected"] == "col1,col2"
        assert data["context"]["found"] == "col1"

    def test_log_summary_basic(self) -> None:
        """Test log_summary with basic message."""
        logger = setup_logger("json")
        fake_stream = StringIO()
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler), "Handler must be StreamHandler"
        handler.stream = fake_stream

        log_summary("Load complete")

        output = fake_stream.getvalue()
        data = json.loads(output.strip())

        assert data["level"] == "INFO"
        assert data["message"] == "Load complete"

    def test_log_summary_with_context(self) -> None:
        """Test log_summary with context data."""
        logger = setup_logger("json")
        fake_stream = StringIO()
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler), "Handler must be StreamHandler"
        handler.stream = fake_stream

        log_summary("Load complete", {"rows": 1000, "duration": 5.23})

        output = fake_stream.getvalue()
        data = json.loads(output.strip())

        assert data["level"] == "INFO"
        assert data["message"] == "Load complete"
        assert data["context"]["rows"] == 1000
        assert data["context"]["duration"] == 5.23

    def test_log_functions_output_to_stderr(self) -> None:
        """Test that log functions output to stderr not stdout."""
        logger = setup_logger("json")

        # Verify handler is configured to use stderr
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler), "Handler must be StreamHandler"
        assert handler.stream == sys.stderr

    def test_multiple_log_calls(self) -> None:
        """Test multiple log calls produce separate JSON lines."""
        logger = setup_logger("json")
        fake_stream = StringIO()
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler), "Handler must be StreamHandler"
        handler.stream = fake_stream

        log_progress("Message 1")
        log_error("Message 2")
        log_summary("Message 3")

        output = fake_stream.getvalue()
        lines = [line for line in output.strip().split("\n") if line]

        assert len(lines) == 3

        data1 = json.loads(lines[0])
        data2 = json.loads(lines[1])
        data3 = json.loads(lines[2])

        assert data1["message"] == "Message 1"
        assert data1["level"] == "INFO"
        assert data2["message"] == "Message 2"
        assert data2["level"] == "ERROR"
        assert data3["message"] == "Message 3"
        assert data3["level"] == "INFO"
