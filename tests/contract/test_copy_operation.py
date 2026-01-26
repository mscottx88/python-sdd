"""
Contract tests for psycopg3 COPY operation.

T008: Tests the psycopg3 cursor.copy() API contract, not end-to-end file loading.

Purpose: Verify that our understanding of psycopg3 COPY FROM STDIN API is correct
and that the basic COPY operation works with in-memory data streams.

This validates the technical approach documented in research.md for using
psycopg3's native COPY support.

Environment variables are loaded via load_dotenv() in tests/conftest.py.
"""

import io
from datetime import datetime
from os import environ

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool


@pytest.fixture
def db_connection():
    """Create a test database connection pool using PostgreSQL environment variables."""
    pg_host: str = environ.get("PGHOST", "localhost")
    pg_port: str = environ.get("PGPORT", "5432")
    pg_database: str = environ.get("PGDATABASE", "test_csv_pipeline")
    pg_user: str = environ.get("PGUSER", "test_user")
    pg_password: str = environ.get("PGPASSWORD", "test_password")

    conninfo: str = make_conninfo(
        host=pg_host,
        port=pg_port,
        dbname=pg_database,
        user=pg_user,
        password=pg_password,
        connect_timeout=5,  # 5 second timeout
    )
    pool = ConnectionPool(conninfo, min_size=1, max_size=2, timeout=5)
    try:
        with pool.connection() as conn:
            yield conn
    finally:
        pool.close()


@pytest.fixture
def test_table(db_connection):
    """Create a temporary test table for COPY operations."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    table_name = f"copy_test_{timestamp}"

    with db_connection.cursor() as cur:
        cur.execute(
            sql.SQL(
                """
            CREATE TEMPORARY TABLE {} (
                id INTEGER,
                name TEXT,
                value NUMERIC
            )
        """
            ).format(sql.Identifier(table_name))
        )
        db_connection.commit()

    yield table_name


def test_psycopg3_copy_from_stdin_with_text_stream(db_connection, test_table):
    """
    T008 - Test psycopg3 cursor.copy() with text data stream.

    Contract: cursor.copy() should accept CSV data from a file-like object
    and insert it into a table using COPY FROM STDIN.

    This is the core pattern we'll use for CSV loading.
    """
    # Arrange - Create in-memory CSV data
    csv_data = io.StringIO()
    csv_data.write("1\tAlice\t100.50\n")
    csv_data.write("2\tBob\t200.75\n")
    csv_data.write("3\tCharlie\t300.25\n")
    csv_data.seek(0)  # Reset to beginning for reading

    # Act - Use COPY FROM STDIN
    with (
        db_connection.cursor() as cur,
        cur.copy(
            sql.SQL("COPY {} (id, name, value) FROM STDIN").format(
                sql.Identifier(test_table)
            )
        ) as copy,
    ):
        while data := csv_data.read(1024):
            copy.write(data)

    db_connection.commit()

    # Assert - Verify data was inserted
    with db_connection.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(test_table)))
        count = cur.fetchone()[0]
        assert count == 3, f"Expected 3 rows, got {count}"

        cur.execute(
            sql.SQL("SELECT id, name, value FROM {} ORDER BY id").format(
                sql.Identifier(test_table)
            )
        )
        rows = cur.fetchall()

        assert rows[0] == (1, "Alice", 100.50), f"First row mismatch: {rows[0]}"
        assert rows[1] == (2, "Bob", 200.75), f"Second row mismatch: {rows[1]}"
        assert rows[2] == (3, "Charlie", 300.25), f"Third row mismatch: {rows[2]}"


def test_psycopg3_copy_with_csv_format(db_connection, test_table):
    """
    Test psycopg3 COPY with CSV format specification.

    Validates that we can use CSV format with COPY (not just tab-delimited),
    which is required for FR-014 (handle CSV variations).
    """
    # Arrange - CSV data with commas and quoted fields
    csv_data = io.StringIO()
    csv_data.write('4,"David, Jr.",400.00\n')
    csv_data.write('5,"Eve",500.50\n')
    csv_data.seek(0)

    # Act - Use COPY with CSV format
    with (
        db_connection.cursor() as cur,
        cur.copy(
            sql.SQL("COPY {} (id, name, value) FROM STDIN WITH (FORMAT CSV)").format(
                sql.Identifier(test_table)
            )
        ) as copy,
    ):
        while data := csv_data.read(1024):
            copy.write(data)

    db_connection.commit()

    # Assert
    with db_connection.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(test_table)))
        count = cur.fetchone()[0]
        assert count == 2, f"Expected 2 rows, got {count}"

        cur.execute(
            sql.SQL("SELECT name FROM {} WHERE id = %s").format(
                sql.Identifier(test_table)
            ),
            (4,),
        )
        name = cur.fetchone()[0]
        assert (
            name == "David, Jr."
        ), f"Quoted field with comma not parsed correctly: {name}"


def test_psycopg3_copy_with_header(db_connection, test_table):
    """
    Test psycopg3 COPY with CSV HEADER option.

    Validates FR-007: System MUST handle CSV files with headers.
    """
    # Arrange - CSV with header row
    csv_data = io.StringIO()
    csv_data.write("id,name,value\n")  # Header row
    csv_data.write("6,Frank,600.00\n")
    csv_data.write("7,Grace,700.50\n")
    csv_data.seek(0)

    # Act - Use COPY with HEADER option
    with (
        db_connection.cursor() as cur,
        cur.copy(
            sql.SQL(
                "COPY {} (id, name, value) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
            ).format(sql.Identifier(test_table))
        ) as copy,
    ):
        while data := csv_data.read(1024):
            copy.write(data)

    db_connection.commit()

    # Assert - Header row should be skipped
    with db_connection.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(test_table)))
        count = cur.fetchone()[0]
        assert count == 2, f"Expected 2 rows (header skipped), got {count}"

        cur.execute(
            sql.SQL("SELECT id FROM {} ORDER BY id").format(sql.Identifier(test_table))
        )
        ids = [row[0] for row in cur.fetchall()]
        assert ids == [6, 7], f"Expected IDs [6, 7], got {ids}"


def test_psycopg3_copy_transaction_rollback(db_connection, test_table):
    """
    Test that COPY operation respects transactions and can be rolled back.

    Validates FR-011: System MUST use database transactions to ensure
    atomic loading (all or nothing per file).
    """
    # Arrange
    csv_data = io.StringIO()
    csv_data.write("8\tHenry\t800.00\n")
    csv_data.seek(0)

    # Act - Insert data then rollback
    with (
        db_connection.cursor() as cur,
        cur.copy(
            sql.SQL("COPY {} (id, name, value) FROM STDIN").format(
                sql.Identifier(test_table)
            )
        ) as copy,
    ):
        while data := csv_data.read(1024):
            copy.write(data)

    # Don't commit - rollback instead
    db_connection.rollback()

    # Assert - Data should not exist
    with db_connection.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(test_table)))
        count = cur.fetchone()[0]
        assert count == 0, f"Expected 0 rows after rollback, got {count}"


def test_psycopg3_copy_handles_large_data_streaming(db_connection, test_table):
    """
    Test COPY with large data stream to validate streaming approach.

    Validates research.md finding: Use streaming to handle large files
    without loading entire file into memory.
    """
    # Arrange - Generate 10,000 rows
    csv_data = io.StringIO()
    for i in range(10000):
        csv_data.write(f"{i}\tUser_{i}\t{i * 10.5}\n")
    csv_data.seek(0)

    # Act - Stream in chunks (simulating file reading)
    chunk_size = 8192  # 8KB chunks
    with (
        db_connection.cursor() as cur,
        cur.copy(
            sql.SQL("COPY {} (id, name, value) FROM STDIN").format(
                sql.Identifier(test_table)
            )
        ) as copy,
    ):
        while chunk := csv_data.read(chunk_size):
            copy.write(chunk)

    db_connection.commit()

    # Assert
    with db_connection.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(test_table)))
        count = cur.fetchone()[0]
        assert count == 10000, f"Expected 10,000 rows, got {count}"

        # Verify first and last rows
        cur.execute(
            sql.SQL("SELECT id FROM {} WHERE id = %s").format(sql.Identifier(test_table)),
            (0,),
        )
        assert cur.fetchone()[0] == 0, "First row missing"

        cur.execute(
            sql.SQL("SELECT id FROM {} WHERE id = %s").format(sql.Identifier(test_table)),
            (9999,),
        )
        assert cur.fetchone()[0] == 9999, "Last row missing"


def test_psycopg3_copy_error_handling(db_connection, test_table):
    """
    Test COPY error handling with invalid data.

    Validates that errors during COPY prevent partial data insertion
    when transaction is rolled back.
    """
    # Arrange - Invalid data (text in numeric column)
    csv_data = io.StringIO()
    csv_data.write("9\tInvalid\tNOT_A_NUMBER\n")
    csv_data.seek(0)

    # Act & Assert - Should raise exception
    with (
        pytest.raises(Exception),
        db_connection.cursor() as cur,
        cur.copy(
            sql.SQL("COPY {} (id, name, value) FROM STDIN").format(
                sql.Identifier(test_table)
            )
        ) as copy,
    ):
        while data := csv_data.read(1024):
            copy.write(data)

    # Verify transaction is in failed state
    assert (
        db_connection.info.transaction_status != psycopg.pq.TransactionStatus.IDLE
    ), "Transaction should be in error state"

    # Rollback and verify no data inserted
    db_connection.rollback()

    with db_connection.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(test_table)))
        count = cur.fetchone()[0]
        assert count == 0, f"No data should be inserted after error, found {count} rows"
