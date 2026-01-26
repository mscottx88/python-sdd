"""Unit tests for CSV loader."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.csv_postgres_pipeline.exceptions import FileProcessingError
from src.csv_postgres_pipeline.loader import load_csv_to_table
from src.csv_postgres_pipeline.models import (
    CSVFile,
    DatabaseConfig,
    JobStatus,
    ValidationStatus,
)


class TestLoadCSVToTable:
    """Tests for load_csv_to_table function."""

    def test_load_csv_dry_run_mode(self, tmp_path: Path) -> None:
        """Test dry-run mode counts rows without loading."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\nval3,val4\n")

        csv_file = CSVFile(file_path=test_file)
        csv_file.column_names = ["col1", "col2"]
        csv_file.validation_status = ValidationStatus.VALID

        config = DatabaseConfig(
            host="localhost", dbname="testdb", username="user", password="pass"
        )

        job = load_csv_to_table(csv_file, config, "test_table", dry_run=True)

        assert job.status == JobStatus.SUCCESS
        assert job.records_loaded == 2  # 2 data rows (header excluded)
        assert job.start_time is not None
        assert job.end_time is not None
        assert job.duration_seconds() is not None

    def test_load_csv_dry_run_with_file_error(self, tmp_path: Path) -> None:
        """Test dry-run mode handles file errors."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\n")

        csv_file = CSVFile(file_path=test_file)
        csv_file.column_names = ["col1", "col2"]

        # Delete file to cause error
        test_file.unlink()

        config = DatabaseConfig(
            host="localhost", dbname="testdb", username="user", password="pass"
        )

        # With Pydantic validation, FileNotFoundError is raised when LoadJob validates the CSVFile
        with pytest.raises(FileNotFoundError, match="CSV file not found"):
            load_csv_to_table(csv_file, config, "test_table", dry_run=True)

    def test_load_csv_with_mocked_database(self, tmp_path: Path) -> None:
        """Test actual load operation with mocked database."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\nval3,val4\n")

        csv_file = CSVFile(file_path=test_file)
        csv_file.column_names = ["col1", "col2"]
        csv_file.validation_status = ValidationStatus.VALID

        config = DatabaseConfig(
            host="localhost", dbname="testdb", username="user", password="pass"
        )

        # Mock the copy context manager
        mock_copy = MagicMock()
        mock_copy.__enter__ = Mock(return_value=mock_copy)
        mock_copy.__exit__ = Mock(return_value=False)

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.copy.return_value = mock_copy
        mock_cursor.rowcount = 2

        # Mock connection
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        # Mock pool
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.loader.create_connection_pool",
            return_value=mock_pool,
        ):
            job = load_csv_to_table(csv_file, config, "test_table")

            assert job.status == JobStatus.SUCCESS
            assert job.records_loaded == 2
            assert job.error_message is None
            mock_conn.commit.assert_called_once()
            mock_pool.close.assert_called_once()

    def test_load_csv_transaction_rollback_on_error(self, tmp_path: Path) -> None:
        """Test transaction rollback on database error."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\n")

        csv_file = CSVFile(file_path=test_file)
        csv_file.column_names = ["col1", "col2"]

        config = DatabaseConfig(
            host="localhost", dbname="testdb", username="user", password="pass"
        )

        # Mock cursor that raises error
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.copy.side_effect = Exception("Database error")

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.loader.create_connection_pool",
            return_value=mock_pool,
        ):
            with pytest.raises(FileProcessingError, match="Failed to load CSV"):
                load_csv_to_table(csv_file, config, "test_table")

            # Verify rollback was called
            mock_conn.rollback.assert_called_once()
            mock_pool.close.assert_called_once()

    def test_load_csv_uses_connection_pool(self, tmp_path: Path) -> None:
        """Test that loader uses connection pool (FR-021)."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\n")

        csv_file = CSVFile(file_path=test_file)
        csv_file.column_names = ["col1", "col2"]

        config = DatabaseConfig(
            host="localhost", dbname="testdb", username="user", password="pass"
        )

        mock_copy = MagicMock()
        mock_copy.__enter__ = Mock(return_value=mock_copy)
        mock_copy.__exit__ = Mock(return_value=False)

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.copy.return_value = mock_copy
        mock_cursor.rowcount = 1

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.loader.create_connection_pool",
            return_value=mock_pool,
        ) as mock_create_pool:
            load_csv_to_table(csv_file, config, "test_table")

            # Verify connection pool was created and used
            mock_create_pool.assert_called_once_with(config)
            mock_pool.connection.assert_called_once()
            mock_conn.__enter__.assert_called()
            mock_conn.__exit__.assert_called()
            mock_pool.close.assert_called_once()

    def test_load_csv_streaming_chunks(self, tmp_path: Path) -> None:
        """Test that CSV is read in chunks for memory efficiency."""
        test_file = tmp_path / "test.csv"
        # Create file with enough data to trigger multiple chunks (>8KB)
        rows = ["col1,col2\n"] + [f"value{i},value{i + 1000}\n" for i in range(500)]
        test_file.write_text("".join(rows))

        csv_file = CSVFile(file_path=test_file)
        csv_file.column_names = ["col1", "col2"]

        config = DatabaseConfig(
            host="localhost", dbname="testdb", username="user", password="pass"
        )

        mock_copy = MagicMock()
        mock_copy.__enter__ = Mock(return_value=mock_copy)
        mock_copy.__exit__ = Mock(return_value=False)
        write_calls: list[str] = []
        mock_copy.write.side_effect = lambda data: write_calls.append(data)

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.copy.return_value = mock_copy
        mock_cursor.rowcount = 500

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.loader.create_connection_pool",
            return_value=mock_pool,
        ):
            job = load_csv_to_table(csv_file, config, "test_table")

            # Verify data was written in chunks (multiple write calls for large file)
            assert (
                len(write_calls) >= 2
            ), "Large file should be written in multiple chunks"
            # Verify file size calculation (approx)
            total_written = "".join(write_calls)
            assert (
                len(total_written) > 8192
            ), "Should have written more than one chunk size"
            assert job.status == JobStatus.SUCCESS
            assert job.records_loaded == 500

    def test_load_csv_job_tracking(self, tmp_path: Path) -> None:
        """Test that LoadJob tracks operation details."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\n")

        csv_file = CSVFile(file_path=test_file)
        csv_file.column_names = ["col1", "col2"]

        config = DatabaseConfig(
            host="localhost", dbname="testdb", username="user", password="pass"
        )

        mock_copy = MagicMock()
        mock_copy.__enter__ = Mock(return_value=mock_copy)
        mock_copy.__exit__ = Mock(return_value=False)

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.copy.return_value = mock_copy
        mock_cursor.rowcount = 1

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.loader.create_connection_pool",
            return_value=mock_pool,
        ):
            job = load_csv_to_table(csv_file, config, "test_table")

            assert job.source_file == csv_file
            assert job.target_table == "test_table"
            assert job.start_time is not None
            assert job.end_time is not None
            assert job.duration_seconds() is not None
            duration = job.duration_seconds()
            assert duration is not None and duration >= 0
            assert job.is_complete() is True


class TestEmptyCSVHandling:
    """Tests for empty CSV file handling (T049a)."""

    def test_load_empty_csv_dry_run_success_with_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test dry-run mode with empty CSV (0 data rows) succeeds and logs warning."""
        test_file = tmp_path / "empty.csv"
        test_file.write_text("col1,col2\n")  # Header only, no data rows

        csv_file = CSVFile(file_path=test_file)
        csv_file.column_names = ["col1", "col2"]
        csv_file.validation_status = ValidationStatus.VALID

        config = DatabaseConfig(
            host="localhost", dbname="testdb", username="user", password="pass"
        )

        with caplog.at_level(logging.WARNING):
            job = load_csv_to_table(csv_file, config, "test_table", dry_run=True)

        # Verify job succeeded with 0 records
        assert job.status == JobStatus.SUCCESS
        assert job.records_loaded == 0
        assert job.error_message is None

        # Verify warning was logged
        assert any(
            "Empty CSV file" in record.message and record.levelname == "WARNING"
            for record in caplog.records
        ), "Expected warning log for empty CSV"

    def test_load_empty_csv_with_mocked_database(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test actual load of empty CSV (0 data rows) with warning."""
        test_file = tmp_path / "empty.csv"
        test_file.write_text("col1,col2\n")  # Header only, no data rows

        csv_file = CSVFile(file_path=test_file)
        csv_file.column_names = ["col1", "col2"]
        csv_file.validation_status = ValidationStatus.VALID

        config = DatabaseConfig(
            host="localhost", dbname="testdb", username="user", password="pass"
        )

        # Mock database with 0 rows loaded
        mock_copy = MagicMock()
        mock_copy.__enter__ = Mock(return_value=mock_copy)
        mock_copy.__exit__ = Mock(return_value=False)

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.copy.return_value = mock_copy
        mock_cursor.rowcount = 0  # Empty CSV results in 0 rows

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with (
            patch(
                "src.csv_postgres_pipeline.loader.create_connection_pool",
                return_value=mock_pool,
            ),
            caplog.at_level(logging.WARNING),
        ):
            job = load_csv_to_table(csv_file, config, "test_table")

        # Verify job succeeded with 0 records
        assert job.status == JobStatus.SUCCESS
        assert job.records_loaded == 0
        assert job.error_message is None

        # Verify warning was logged
        assert any(
            "Empty CSV file" in record.message and record.levelname == "WARNING"
            for record in caplog.records
        ), "Expected warning log for empty CSV"
