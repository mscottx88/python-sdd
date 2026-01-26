"""Contract tests for CLI interface.

These tests verify the CLI contract defined in contracts/cli.md.
They validate argument parsing, exit codes, and output formats.
"""

import logging
import os
import tempfile
from pathlib import Path

import pytest

from src.csv_postgres_pipeline.cli import (
    EXIT_CONNECTION_ERROR,
    EXIT_SUCCESS,
    EXIT_VALIDATION_ERROR,
    create_parser,
    main,
)


class TestCLIModule:
    """Tests for CLI module existence and basic structure."""

    def test_cli_module_exists(self) -> None:
        """Test that cli module can be imported."""
        try:
            from csv_postgres_pipeline import cli

            assert hasattr(cli, "main"), "cli module should have main() function"
        except ImportError:
            pytest.fail("cli.py module does not exist - need to implement Phase 6")


class TestCLIArguments:
    """Tests for CLI argument parsing per contracts/cli.md."""

    def test_cli_accepts_required_arguments(self) -> None:
        """Test CLI accepts source file and target table arguments."""
        parser = create_parser()
        help_text = parser.format_help().lower()

        assert help_text, "Should produce help output"
        assert (
            "source" in help_text or "file" in help_text
        ), "Should accept source file argument"
        assert (
            "target" in help_text or "table" in help_text
        ), "Should accept target table argument"

    def test_cli_accepts_database_options(self) -> None:
        """Test CLI accepts database connection options."""
        parser = create_parser()
        help_text = parser.format_help()

        assert "--host" in help_text, "Should accept --host option"
        assert (
            "--database" in help_text or "--dbname" in help_text
        ), "Should accept database name option"
        assert (
            "--username" in help_text or "--user" in help_text
        ), "Should accept username option"

    def test_cli_accepts_optional_flags(self) -> None:
        """Test CLI accepts optional configuration flags per FR-020."""

        parser = create_parser()
        help_text = parser.format_help()

        # Note: --threads flag was removed in FEATURE_REMOVAL_BATCH_PROCESSING.md
        assert "--dry-run" in help_text, "Should accept dry-run flag (FR-020)"
        assert "--delimiter" in help_text, "Should accept delimiter option (FR-017)"
        assert "--encoding" in help_text, "Should accept encoding option (FR-016)"

    def test_cli_accepts_phase3b_flags(self) -> None:
        """Test CLI accepts Phase 3b configuration flags."""
        parser = create_parser()
        help_text = parser.format_help()

        assert (
            "--create-table" in help_text
        ), "Should accept --create-table flag (Phase 3b)"
        assert (
            "--case-insensitive" in help_text
        ), "Should accept --case-insensitive flag (Phase 3b)"
        assert (
            "--allow-subset" in help_text
        ), "Should accept --allow-subset flag (Phase 3b)"
        assert (
            "--ignore-extra" in help_text
        ), "Should accept --ignore-extra flag (Phase 3b)"


class TestCLIExitCodes:
    """Tests for CLI exit codes."""

    def test_cli_exit_code_success(self, tmp_path: Path) -> None:
        """Test CLI returns exit code 0 on success."""
        # Create a simple CSV file
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,name\n1,Alice\n2,Bob\n")

        # Run in dry-run mode to avoid needing database
        exit_code = main(
            [
                str(csv_file),
                "test_table",
                "--dry-run",
            ]
        )

        assert exit_code == EXIT_SUCCESS, "Should return 0 on successful validation"

    def test_cli_exit_code_validation_error(self, tmp_path: Path) -> None:
        """Test CLI returns exit code 1 on validation errors."""
        # Non-existent file should cause validation error
        non_existent = tmp_path / "nonexistent.csv"

        exit_code = main(
            [
                str(non_existent),
                "test_table",
                "--dry-run",
            ]
        )

        assert exit_code == EXIT_VALIDATION_ERROR, "Should return 1 on validation error"

    def test_cli_exit_code_connection_error(self) -> None:
        """Test CLI returns appropriate exit code on connection errors."""
        # Create a temp CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id,name\n1,Alice\n")
            csv_path = f.name

        try:
            # Use invalid port to trigger connection error with short timeout for fast test
            exit_code = main(
                [
                    csv_path,
                    "test_table",
                    "--port",
                    "9999",  # Non-existent port
                    "--connection-timeout",
                    "2",  # Short timeout for fast test execution
                ]
            )

            assert (
                exit_code == EXIT_CONNECTION_ERROR
            ), "Should return 2 on connection error"
        finally:
            os.unlink(csv_path)


class TestCLIOutputFormat:
    """Tests for CLI output format (JSON to stderr per FR-012)."""

    def test_cli_json_output_format(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test CLI outputs logs to stderr."""
        # Create a simple CSV file
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,name\n1,Alice\n2,Bob\n")

        # Capture logs at INFO level
        with caplog.at_level(logging.INFO):
            # Run in dry-run mode
            main(
                [
                    str(csv_file),
                    "test_table",
                    "--dry-run",
                ]
            )

        # Should have log messages
        assert len(caplog.records) > 0, "Should output logs"
        log_text = " ".join(record.message for record in caplog.records)
        assert (
            "Validating" in log_text or "DRY-RUN" in log_text
        ), "Should log validation steps"

    def test_cli_supports_verbose_mode(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test CLI supports --verbose flag for detailed logging."""
        # Create a simple CSV file
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,name\n1,Alice\n")

        # Capture logs at DEBUG level for verbose mode
        with caplog.at_level(logging.DEBUG):
            # Run with verbose flag
            main(
                [
                    str(csv_file),
                    "test_table",
                    "--dry-run",
                    "--verbose",
                ]
            )

        # Verbose mode should produce log output
        assert len(caplog.records) > 0, "Should output verbose logs"
