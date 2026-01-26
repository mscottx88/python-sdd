"""
Integration tests for User Story 1: Single CSV File Ingestion (Priority: P1)

Tests the end-to-end flow: CSV file → validation → COPY → verify DB rows

Acceptance Scenarios:
1. Given a valid CSV file with 1000 rows and target table exists,
   When the pipeline processes the file,
   Then all 1000 rows are inserted into the table

2. Given a CSV file with headers matching table columns,
   When the pipeline processes the file,
   Then data is mapped correctly to corresponding columns

3. Given a successfully loaded file,
   When the process completes,
   Then the system reports the number of records loaded and processing time

Note: Common fixtures (db_config, test_table_name, create_test_table, fixtures_dir)
are defined in tests/conftest.py and automatically available to all tests.
Environment variables are loaded via load_dotenv() in tests/conftest.py.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool

from src.csv_postgres_pipeline.database import get_table_schema
from src.csv_postgres_pipeline.loader import load_csv_to_table
from src.csv_postgres_pipeline.models import (
    CSVFile,
    DatabaseConfig,
    JobStatus,
    PipelineConfig,
    ValidationStatus,
)
from src.csv_postgres_pipeline.reporter import setup_logger
from src.csv_postgres_pipeline.validator import (
    validate_csv_file,
    validate_csv_schema,
)


# T023: Integration test for single file load success
def test_single_file_load_success(
    db_config: dict[str, Any], create_test_table: str, fixtures_dir: Path
) -> None:  # noqa: F811
    """
    T023 [US1] - Test successful loading of a valid CSV file with 1000 rows.

    Acceptance Scenario 1:
    Given a valid CSV file with 1000 rows and a target table exists,
    When the pipeline processes the file,
    Then all 1000 rows are inserted into the table.
    """
    # Arrange
    csv_file_path = fixtures_dir / "valid_1000_rows.csv"
    assert csv_file_path.exists(), f"Test fixture not found: {csv_file_path}"

    csv_file = CSVFile(file_path=csv_file_path)
    db_cfg = DatabaseConfig(**db_config)
    table_name = create_test_table

    # Act
    result = load_csv_to_table(csv_file, db_cfg, table_name)

    # Assert
    assert result.status == JobStatus.SUCCESS, f"Load failed: {result.error_message}"
    assert (
        result.records_loaded == 1000
    ), f"Expected 1000 rows, got {result.records_loaded}"

    # Verify data in database using connection pool
    conninfo = make_conninfo(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["dbname"],
        user=db_config["username"],
        password=db_config["password"],
    )
    pool = ConnectionPool(conninfo, min_size=1, max_size=2)
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name))
            )
            row = cur.fetchone()
            assert row is not None
            row_count = row[0]
            assert row_count == 1000, f"Expected 1000 rows in DB, found {row_count}"

            # Verify first row data
            cur.execute(
                sql.SQL(
                    "SELECT customer_id, first_name, last_name, email FROM {} ORDER BY customer_id LIMIT 1"
                ).format(sql.Identifier(table_name))
            )
            first_row = cur.fetchone()
            assert first_row is not None
            assert first_row[0] == 1, "First customer_id should be 1"
            assert first_row[1] is not None, "First name should not be null"
            assert first_row[2] is not None, "Last name should not be null"
            assert "@" in first_row[3], "Email should contain @"
    finally:
        pool.close()


# T024: Integration test for CSV validation pass/fail
def test_csv_validation_pass_and_fail(
    db_config: dict[str, Any], create_test_table: str, fixtures_dir: Path
) -> None:  # noqa: F811
    """
    T024 [US1] - Test CSV validation correctly identifies valid and invalid files.

    Valid CSV should pass validation.
    Invalid CSV (wrong schema) should fail validation before database operations.
    """

    db_cfg = DatabaseConfig(**db_config)
    table_name = create_test_table

    # Test 1: Valid CSV passes validation
    valid_csv = fixtures_dir / "valid_1000_rows.csv"
    csv_file_valid = CSVFile(file_path=valid_csv)

    # File structure validation
    is_valid_structure = validate_csv_file(csv_file_valid)
    assert is_valid_structure is True, "Valid CSV should pass file structure validation"
    assert (
        csv_file_valid.validation_status == ValidationStatus.VALID
    ), "Status should be VALID"
    assert len(csv_file_valid.column_names) > 0, "Should have parsed column names"

    # Schema matching validation
    table_schema = get_table_schema(db_cfg, table_name)
    config = PipelineConfig()
    is_valid_schema = validate_csv_schema(csv_file_valid, table_schema, config)
    assert is_valid_schema is True, "Valid CSV should match table schema"

    # Test 2: Invalid CSV fails validation
    invalid_csv = fixtures_dir / "invalid_schema.csv"
    csv_file_invalid = CSVFile(file_path=invalid_csv)

    # File structure validation should pass (it's a valid CSV file)
    is_valid_structure = validate_csv_file(csv_file_invalid)
    assert (
        is_valid_structure is True
    ), "File structure should be valid even if schema doesn't match"

    # Schema matching validation should fail
    with pytest.raises(Exception) as exc_info:
        validate_csv_schema(csv_file_invalid, table_schema, config)

    assert (
        "schema" in str(exc_info.value).lower() or "column" in str(exc_info.value).lower()
    ), "Error message should mention schema or column mismatch"
    assert (
        csv_file_invalid.validation_status == ValidationStatus.INVALID
    ), "Status should be INVALID"


# T025: Integration test for schema matching validation
def test_schema_matching_validation(
    db_config: dict[str, Any], create_test_table: str, fixtures_dir: Path
) -> None:  # noqa: F811
    """
    T025 [US1] - Test that CSV columns are correctly matched to table columns.

    Acceptance Scenario 2:
    Given a CSV file with headers matching table columns,
    When the pipeline processes the file,
    Then data is mapped correctly to corresponding columns.
    """
    # Arrange
    csv_file_path = fixtures_dir / "valid_1000_rows.csv"
    csv_file = CSVFile(file_path=csv_file_path)
    db_cfg = DatabaseConfig(**db_config)
    table_name = create_test_table
    config = PipelineConfig()

    # Act - First validate the CSV file itself
    validate_csv_file(csv_file)

    # Then validate schema matching
    table_schema = get_table_schema(db_cfg, table_name)
    is_valid = validate_csv_schema(csv_file, table_schema, config)

    # Assert
    assert is_valid is True, "CSV schema should match table schema"

    # Verify column names are extracted correctly
    expected_columns = ["customer_id", "first_name", "last_name", "email", "created_at"]
    assert (
        csv_file.column_names == expected_columns
    ), f"Expected columns {expected_columns}, got {csv_file.column_names}"

    # Verify all CSV columns exist in table schema
    table_column_names = [col.name for col in table_schema.columns]
    for csv_col in csv_file.column_names:
        assert (
            csv_col in table_column_names
        ), f"CSV column '{csv_col}' not found in table schema {table_column_names}"


# T027c: Integration test for empty CSV file handling (edge case)
def test_empty_csv_file_handling(
    db_config: dict[str, Any], create_test_table: str, fixtures_dir: Path
) -> None:  # noqa: F811
    """
    T027c [US1] - Test handling of empty CSV file (0 data rows, headers only).

    Edge Case: What happens when a CSV file is empty (0 data rows, only headers)?
    Expected: Should complete successfully with 0 rows loaded, no errors.
    """

    csv_file_path = fixtures_dir / "empty.csv"
    assert csv_file_path.exists(), f"Test fixture not found: {csv_file_path}"

    csv_file = CSVFile(file_path=csv_file_path)
    db_cfg = DatabaseConfig(**db_config)
    table_name = create_test_table

    # Act
    result = load_csv_to_table(csv_file, db_cfg, table_name)

    # Assert
    assert (
        result.status == JobStatus.SUCCESS
    ), "Empty CSV should complete successfully (not an error)"
    assert result.records_loaded == 0, f"Expected 0 rows, got {result.records_loaded}"

    # Verify no data in database using connection pool
    conninfo = make_conninfo(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["dbname"],
        user=db_config["username"],
        password=db_config["password"],
    )
    pool = ConnectionPool(conninfo, min_size=1, max_size=2)
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name))
            )
            row = cur.fetchone()
            assert row is not None
            row_count = row[0]
            assert row_count == 0, f"Expected 0 rows in DB, found {row_count}"
    finally:
        pool.close()


# Additional test for acceptance scenario 3
def test_progress_reporting(
    db_config: dict[str, Any], create_test_table: str, fixtures_dir: Path
) -> None:  # noqa: F811
    """
    Test for Acceptance Scenario 3:
    Given a successfully loaded file,
    When the process completes,
    Then the system reports the number of records loaded and processing time.
    """

    csv_file_path = fixtures_dir / "valid_1000_rows.csv"
    csv_file = CSVFile(file_path=csv_file_path)
    db_cfg = DatabaseConfig(**db_config)
    table_name = create_test_table

    # Act
    result = load_csv_to_table(csv_file, db_cfg, table_name)

    # Assert
    assert result.records_loaded == 1000, "Should report correct record count"
    duration = result.duration_seconds()
    assert duration is not None, "Should report processing time"
    assert duration > 0, "Duration should be positive"
    assert result.start_time is not None, "Should track start time"
    assert result.end_time is not None, "Should track end time"
    assert result.end_time > result.start_time, "End time should be after start time"


# Transaction rollback test
def test_transaction_rollback_on_error(
    db_config: dict[str, Any], create_test_table: str, fixtures_dir: Path
) -> None:  # noqa: F811
    """
    Test that transaction is rolled back on error, leaving no partial data.

    Validates FR-011: System MUST use database transactions to ensure
    atomic loading (all or nothing per file).
    """

    # Arrange - use invalid schema CSV to trigger error
    csv_file_path = fixtures_dir / "invalid_schema.csv"
    csv_file = CSVFile(file_path=csv_file_path)
    db_cfg = DatabaseConfig(**db_config)
    table_name = create_test_table

    # Act
    with pytest.raises(Exception):
        load_csv_to_table(csv_file, db_cfg, table_name)

    # Assert - verify no data was committed using connection pool
    conninfo = make_conninfo(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["dbname"],
        user=db_config["username"],
        password=db_config["password"],
    )
    pool = ConnectionPool(conninfo, min_size=1, max_size=2)
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name))
            )
            row = cur.fetchone()
            assert row is not None
            row_count = row[0]
            assert row_count == 0, f"Transaction should rollback - found {row_count} rows"
    finally:
        pool.close()


# Column matching configuration tests
def test_column_matching_configuration(
    db_config: dict[str, Any], fixtures_dir: Path
) -> None:
    """Test configurable column matching modes work end-to-end.

    Validates FR-010: System MUST support configurable column matching
    policies (case-insensitive, subset, ignore extra).
    """

    db_cfg = DatabaseConfig(**db_config)

    # Create test table with lowercase column names
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    table_name = f"test_column_matching_{timestamp}"

    conninfo = make_conninfo(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["dbname"],
        user=db_config["username"],
        password=db_config["password"],
    )
    pool = ConnectionPool(conninfo, min_size=1, max_size=2)

    try:
        # Create table
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                CREATE TABLE {} (
                    customer_id INTEGER PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    created_at TIMESTAMP
                )
            """
                ).format(sql.Identifier(table_name))
            )
            conn.commit()

        table_schema = get_table_schema(db_cfg, table_name)

        # Test 1: Case-insensitive matching
        uppercase_csv = fixtures_dir / "uppercase_columns.csv"
        csv_uppercase = CSVFile(file_path=uppercase_csv)
        validate_csv_file(csv_uppercase)

        # Should fail with strict mode (default)
        strict_config = PipelineConfig()
        with pytest.raises(Exception, match="not in table|schema mismatch"):
            validate_csv_schema(csv_uppercase, table_schema, strict_config)

        # Reset validation status
        csv_uppercase.validation_status = ValidationStatus.VALID

        # Should pass with case-insensitive mode
        case_config = PipelineConfig(case_insensitive=True)
        result = validate_csv_schema(csv_uppercase, table_schema, case_config)
        assert result is True, "Case-insensitive matching should pass"

        # Test 2: Subset matching (missing optional column)
        subset_csv = fixtures_dir / "subset_columns.csv"
        csv_subset = CSVFile(file_path=subset_csv)
        validate_csv_file(csv_subset)

        # Should fail with strict mode
        with pytest.raises(Exception, match="missing optional columns|schema mismatch"):
            validate_csv_schema(csv_subset, table_schema, strict_config)

        # Reset validation status
        csv_subset.validation_status = ValidationStatus.VALID

        # Should pass with allow_subset mode
        subset_config = PipelineConfig(allow_subset=True)
        result = validate_csv_schema(csv_subset, table_schema, subset_config)
        assert result is True, "Subset matching should pass for missing optional column"

        # Test 3: Ignore extra columns
        extra_csv = fixtures_dir / "extra_columns.csv"
        csv_extra = CSVFile(file_path=extra_csv)
        validate_csv_file(csv_extra)

        # Should fail with strict mode
        with pytest.raises(Exception, match="not in table|schema mismatch"):
            validate_csv_schema(csv_extra, table_schema, strict_config)

        # Reset validation status
        csv_extra.validation_status = ValidationStatus.VALID

        # Should pass with ignore_extra mode
        ignore_config = PipelineConfig(ignore_extra=True)
        result = validate_csv_schema(csv_extra, table_schema, ignore_config)
        assert result is True, "Ignore extra should pass with extra columns"

        # Test 4: Combined modes - uppercase columns with extra fields
        csv_combined = CSVFile(file_path=extra_csv)
        # Modify to have uppercase columns (simulate)
        csv_combined.column_names = [col.upper() for col in csv_extra.column_names]
        csv_combined.validation_status = ValidationStatus.VALID

        # Should pass with combined case-insensitive and ignore-extra
        combined_config = PipelineConfig(case_insensitive=True, ignore_extra=True)
        result = validate_csv_schema(csv_combined, table_schema, combined_config)
        assert result is True, "Combined modes should work together"

    finally:
        # Cleanup
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(table_name))
            )
            conn.commit()
        pool.close()


# Table auto-creation test
def test_automatic_table_creation(db_config: dict[str, Any], fixtures_dir: Path) -> None:
    """Test automatic table creation when table doesn't exist.

    Validates specification clarification: System SHOULD support optional
    --create-table flag to automatically create missing tables from CSV schema.
    """

    db_cfg = DatabaseConfig(**db_config)

    # Create unique table name that doesn't exist
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    table_name = f"test_auto_created_{timestamp}"

    # Use subset columns CSV for this test
    csv_path = fixtures_dir / "subset_columns.csv"
    csv_file = CSVFile(file_path=csv_path)
    validate_csv_file(csv_file)

    conninfo = make_conninfo(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["dbname"],
        user=db_config["username"],
        password=db_config["password"],
    )
    pool = ConnectionPool(conninfo, min_size=1, max_size=2)

    try:
        # Test 1: Verify table doesn't exist
        with pytest.raises(Exception, match="not found"):
            get_table_schema(db_cfg, table_name, create_if_missing=False)

        # Test 2: Create table automatically from CSV
        schema = get_table_schema(
            db_cfg, table_name, create_if_missing=True, csv_file=csv_file
        )

        # Verify table was created with correct columns
        assert schema.table_name == table_name
        assert len(schema.columns) == 4  # subset_columns.csv has 4 columns
        assert schema.columns[0].name == "customer_id"
        assert schema.columns[1].name == "first_name"
        assert schema.columns[2].name == "last_name"
        assert schema.columns[3].name == "email"

        # All columns should be TEXT and nullable (safe defaults)
        for col in schema.columns:
            assert col.data_type == "text"
            assert col.is_nullable is True

        # Test 3: Verify table exists in database
        with pool.connection() as conn, conn.cursor() as cur:
            # Check table exists
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
                """,
                (table_name,),
            )
            result = cur.fetchone()
            assert result is not None, "Table should exist in database"
            assert result[0] == table_name

            # Check columns match
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
                """,
                (table_name,),
            )
            columns = cur.fetchall()
            assert len(columns) == 4
            assert columns[0][0] == "customer_id"
            assert columns[0][1] == "text"
            assert columns[0][2] == "YES"

        # Test 4: Verify we can validate CSV against the auto-created table
        config = PipelineConfig()
        validation_result = validate_csv_schema(csv_file, schema, config)
        assert validation_result is True, "CSV should validate against auto-created table"

        # Test 5: Verify calling again with existing table returns same schema
        schema2 = get_table_schema(
            db_cfg, table_name, create_if_missing=True, csv_file=csv_file
        )
        assert schema2.table_name == schema.table_name
        assert len(schema2.columns) == len(schema.columns)
        for col1, col2 in zip(schema.columns, schema2.columns, strict=True):
            assert col1.name == col2.name
            assert col1.data_type == col2.data_type

    finally:
        # Cleanup - drop the auto-created table
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(table_name))
            )
            conn.commit()
        pool.close()


def test_json_logging_output(
    db_config: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """
    Test that JSON structured logging is emitted to stderr during load operations.

    Validates:
    - Log entries are valid JSON
    - Required fields present (timestamp, level, message, context)
    - Progress, error, and summary messages are logged
    """
    # Setup JSON logger
    setup_logger("json")

    # Use the existing test fixture
    csv_file_path = Path(__file__).parent / "fixtures" / "valid_1000_rows.csv"

    # Create models
    csv_file = CSVFile(file_path=csv_file_path)
    db_cfg = DatabaseConfig(**db_config)

    # Test with dry-run mode to avoid database setup
    _job = load_csv_to_table(csv_file, db_cfg, "test_customers", dry_run=True)

    # Capture stderr output
    captured = capsys.readouterr()
    stderr_output = captured.err

    # Parse JSON lines from stderr
    log_lines = [line for line in stderr_output.strip().split("\n") if line]

    # Verify we have log output
    assert len(log_lines) >= 2, "Expected at least 2 log entries (start + summary)"

    # Validate each log entry
    for log_line in log_lines:
        try:
            log_data = json.loads(log_line)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in log line: {log_line}. Error: {e}")

        # Check required fields
        assert "timestamp" in log_data, f"Missing timestamp in: {log_data}"
        assert "level" in log_data, f"Missing level in: {log_data}"
        assert "message" in log_data, f"Missing message in: {log_data}"
        assert log_data["level"] in [
            "INFO",
            "ERROR",
        ], f"Invalid log level: {log_data['level']}"

        # Verify timestamp format (ISO 8601 with Z suffix)
        assert log_data["timestamp"].endswith("Z"), "Timestamp should end with Z"

        # If message contains context, validate it
        if "context" in log_data:
            assert isinstance(log_data["context"], dict), "Context should be a dict"

    # Verify specific log messages
    messages = [
        log_data["message"] for log_data in [json.loads(line) for line in log_lines]
    ]
    assert any(
        "Starting CSV load operation" in msg for msg in messages
    ), "Missing start message"
    assert any(
        "Dry-run validation complete" in msg for msg in messages
    ), "Missing summary message"

    # Verify context data in summary
    summary_logs = [
        json.loads(line) for line in log_lines if "Dry-run validation complete" in line
    ]
    assert len(summary_logs) >= 1, "Expected summary log entry"
    summary = summary_logs[0]
    assert "context" in summary, "Summary should have context"
    assert (
        "rows_validated" in summary["context"]
    ), "Summary context should include rows_validated"
    assert summary["context"]["rows_validated"] == 1000, "Should validate 1000 rows"


def test_dry_run_mode_validation_only(
    fixtures_dir: Path, db_config: dict[str, Any], test_table_name: str
) -> None:
    """Test dry-run mode validates without loading data (FR-020, G1).

    Acceptance:
    - File validation runs successfully
    - Row count is reported
    - NO data is written to database
    - Job status is SUCCESS
    """
    # Create test table first
    conninfo = make_conninfo(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["dbname"],
        user=db_config["username"],
        password=db_config["password"],
    )
    pool = ConnectionPool(conninfo, min_size=1, max_size=2)

    try:
        with pool.connection() as conn, conn.cursor() as cur:
            # Create table matching valid_1000_rows.csv schema
            cur.execute(
                sql.SQL(
                    """
                CREATE TABLE {} (
                    customer_id INTEGER PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    created_at TIMESTAMP
                )
            """
                ).format(sql.Identifier(test_table_name))
            )
            conn.commit()

        csv_file_path = fixtures_dir / "valid_1000_rows.csv"
        csv_file = CSVFile(file_path=csv_file_path)
        config = DatabaseConfig(**db_config)

        # Perform dry-run load
        job = load_csv_to_table(
            csv_file=csv_file,
            db_config=config,
            table_name=test_table_name,
            dry_run=True,
        )

        # Verify job succeeded
        assert job.status == JobStatus.SUCCESS
        assert job.records_loaded == 1000  # Row count reported
        assert job.error_message is None

        # Verify NO data was actually loaded to database
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(test_table_name))
            )
            row = cur.fetchone()
            assert row is not None
            count = row[0]
            assert count == 0, "Dry-run should not load any data"

        # Cleanup
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(test_table_name))
            )
            conn.commit()
    finally:
        pool.close()


def test_dry_run_detects_invalid_file(
    tmp_path: Path, db_config: dict[str, Any], test_table_name: str
) -> None:
    """Test dry-run mode detects validation errors without database changes."""
    # Create test table
    conninfo = make_conninfo(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["dbname"],
        user=db_config["username"],
        password=db_config["password"],
    )
    pool = ConnectionPool(conninfo, min_size=1, max_size=2)

    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                CREATE TABLE {} (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """
                ).format(sql.Identifier(test_table_name))
            )
            conn.commit()

        # Create malformed CSV (inconsistent column count)
        csv_path = tmp_path / "malformed.csv"
        csv_path.write_text("id,name\n1,Alice\n2")  # Missing column in row 2

        csv_file = CSVFile(file_path=csv_path)
        config = DatabaseConfig(**db_config)

        job = load_csv_to_table(
            csv_file=csv_file,
            db_config=config,
            table_name=test_table_name,
            dry_run=True,
        )

        # Should detect error during dry-run
        assert job.status == JobStatus.FAILED
        assert job.error_message is not None, "Error message should not be None"
        assert (
            "validation" in job.error_message.lower()
            or "failed" in job.error_message.lower()
        )

        # Cleanup
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(test_table_name))
            )
            conn.commit()
    finally:
        pool.close()
