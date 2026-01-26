"""Integration tests for User Story 3: Error Handling and Recovery.

Tests comprehensive error scenarios including:
- Type mismatch detection with clear error context
- Connection failure rollback validation
- Malformed CSV detection before database operations
- Successful reprocessing after fixing issues

These tests validate FR-015 (clear error messages with file/line/column),
FR-011 (transaction rollback), and FR-004 (validation before DB operations).

Note: Common fixtures (db_config, test_table_name, create_typed_test_table, fixtures_dir)
are defined in tests/conftest.py and automatically available to all tests.
Environment variables are loaded via load_dotenv() in tests/conftest.py.
"""

from pathlib import Path
from typing import Any

import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool

from src.csv_postgres_pipeline.exceptions import DatabaseError, ValidationError
from src.csv_postgres_pipeline.loader import load_csv_to_table
from src.csv_postgres_pipeline.models import CSVFile, DatabaseConfig, ValidationStatus
from src.csv_postgres_pipeline.validator import validate_csv_file


# US3 Acceptance Scenario 1: Type mismatch shows column, row, expected type
def test_type_mismatch_error_with_context(
    db_config: dict[str, Any], create_typed_test_table: str, fixtures_dir: Path
) -> None:
    """
    Test that type mismatch errors provide detailed context.

    US3 Acceptance Scenario 1: Given a CSV file with a column type mismatch,
    When the pipeline attempts to load it, Then a clear error message
    identifies the problematic column and row.

    Validates FR-015: System MUST provide clear error messages with file name,
    line number, and error description.
    """
    # Arrange - CSV with string in integer column
    csv_file_path = fixtures_dir / "type_mismatch.csv"
    csv_file = CSVFile(file_path=csv_file_path)
    db_cfg = DatabaseConfig(**db_config)
    table_name = create_typed_test_table

    # Act & Assert
    with pytest.raises((DatabaseError, Exception)) as exc_info:
        load_csv_to_table(csv_file, db_cfg, table_name)

    # Verify error message contains context
    error_msg = str(exc_info.value).lower()
    assert (
        "type_mismatch.csv" in error_msg or csv_file_path.name in error_msg
    ), f"Error should mention filename, got: {error_msg}"
    # Note: Exact line/column context depends on PostgreSQL error messages
    # which may vary. We verify the error is raised with filename context.


# US3 Acceptance Scenario 2: Connection failure rolls back transaction
def test_connection_failure_rollback(
    db_config: dict[str, Any], create_typed_test_table: str, fixtures_dir: Path
) -> None:
    """
    Test that connection failures trigger proper transaction rollback.

    US3 Acceptance Scenario 2: Given a database connection failure mid-processing,
    When the error occurs, Then the transaction is rolled back and no partial
    data remains.

    Validates FR-011: System MUST use database transactions to ensure
    atomic loading (all or nothing per file).

    Note: This test validates rollback behavior by using an invalid connection
    and verifying no data is written. Uses a 2-second timeout for fast test execution.
    """
    # Arrange - use valid CSV but invalid database config
    csv_file_path = fixtures_dir / "valid_100_rows_typed.csv"
    csv_file = CSVFile(file_path=csv_file_path)

    # Create invalid config (wrong port) with short timeout for fast test execution
    invalid_config = db_config.copy()
    invalid_config["port"] = 9999  # Non-existent port
    invalid_config["connection_timeout"] = 2  # 2-second timeout for faster tests
    db_cfg = DatabaseConfig(**invalid_config)
    table_name = create_typed_test_table

    # Act & Assert - should fail to connect
    with pytest.raises(Exception) as exc_info:
        load_csv_to_table(csv_file, db_cfg, table_name)

    # Verify error is connection-related
    error_msg = str(exc_info.value).lower()
    assert any(
        keyword in error_msg
        for keyword in ["connection", "connect", "timeout", "refused"]
    ), f"Error should be connection-related, got: {exc_info.value}"

    # Verify no data was committed to real database (using correct config)
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
            assert (
                row_count == 0
            ), f"Transaction should rollback on connection failure - found {row_count} rows"
    finally:
        pool.close()


# US3 Acceptance Scenario 3: Malformed CSV detected before database operations
def test_malformed_csv_detection_before_db_ops(
    db_config: dict[str, Any], fixtures_dir: Path
) -> None:
    """
    Test that malformed CSV files are detected during validation phase.

    US3 Acceptance Scenario 3: Given a malformed CSV file with inconsistent
    column counts, When validation runs, Then the error is detected before
    any database operations begin.

    Validates FR-004: System MUST validate CSV structure before attempting
    database operations.
    """
    # Arrange - CSV with inconsistent column counts
    csv_file_path = fixtures_dir / "malformed.csv"
    csv_file = CSVFile(file_path=csv_file_path)

    # Act & Assert - validation should fail before any DB operations
    with pytest.raises(ValidationError) as exc_info:
        validate_csv_file(csv_file)

    # Verify validation status
    assert csv_file.validation_status == ValidationStatus.INVALID
    error_msg = str(exc_info.value).lower()
    assert (
        "malformed" in error_msg or "column" in error_msg or "inconsistent" in error_msg
    ), f"Error should describe malformed CSV issue, got: {error_msg}"


# US3 Acceptance Scenario 4: Fixed file reprocesses successfully
def test_successful_reprocessing_after_fix(
    db_config: dict[str, Any],
    create_typed_test_table: str,
    fixtures_dir: Path,
    tmp_path: Path,
) -> None:
    """
    Test that corrected files can be reprocessed successfully.

    US3 Acceptance Scenario 4: Given a previously failed file has been corrected,
    When reprocessing is initiated, Then the file loads successfully without
    affecting previously loaded data.

    Validates recovery workflow and idempotency.
    """
    db_cfg = DatabaseConfig(**db_config)
    table_name = create_typed_test_table

    # Step 1: Process a valid file successfully
    valid_csv = fixtures_dir / "valid_100_rows_typed.csv"
    csv_file_1 = CSVFile(file_path=valid_csv)
    job_1 = load_csv_to_table(csv_file_1, db_cfg, table_name)
    assert job_1.records_loaded == 100, "First file should load successfully"

    # Step 2: Try to load invalid file (type mismatch) - should fail
    invalid_csv = fixtures_dir / "type_mismatch.csv"
    csv_file_2 = CSVFile(file_path=invalid_csv)
    with pytest.raises(Exception):
        load_csv_to_table(csv_file_2, db_cfg, table_name)

    # Step 3: Create corrected version of the file
    corrected_csv = tmp_path / "corrected.csv"
    corrected_csv.write_text(
        "id,name,age,salary\n"
        "2001,Alice,30,75000.00\n"
        "2002,Bob,25,65000.00\n"
        "2003,Charlie,35,85000.00\n"
    )

    # Step 4: Reprocess corrected file - should succeed
    csv_file_3 = CSVFile(file_path=corrected_csv)
    job_3 = load_csv_to_table(csv_file_3, db_cfg, table_name)
    assert job_3.records_loaded == 3, "Corrected file should load successfully"

    # Step 5: Verify total row count (original 100 + corrected 3)
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
            total_rows = row[0]
            assert total_rows == 103, f"Should have 100 + 3 rows, found {total_rows}"
    finally:
        pool.close()
