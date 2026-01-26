"""CSV to Postgres loader using COPY FROM STDIN."""

import csv
from datetime import datetime

from psycopg import sql
from psycopg.sql import Composed
from psycopg_pool import ConnectionPool

from src.csv_postgres_pipeline.database import create_connection_pool
from src.csv_postgres_pipeline.exceptions import FileProcessingError
from src.csv_postgres_pipeline.models import (
    CSVFile,
    DatabaseConfig,
    JobStatus,
    LoadJob,
)
from src.csv_postgres_pipeline.reporter import (
    log_error,
    log_progress,
    log_summary,
    log_warning,
)


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
# Complex pipeline function handling validation, conversion, streaming,
# and error reporting
def load_csv_to_table(
    csv_file: CSVFile,
    db_config: DatabaseConfig,
    table_name: str,
    dry_run: bool = False,
) -> LoadJob:
    """Load CSV file into Postgres table using COPY FROM STDIN.

    Uses streaming approach to handle large files without loading into memory.
    Implements transactional integrity: all rows loaded or none (atomic operation).

    Args:
        csv_file: CSVFile instance with validated data
        db_config: Database connection configuration
        table_name: Target table name in database
        dry_run: If True, validate only without loading data (FR-020)

    Returns:
        LoadJob instance with operation results

    Raises:
        FileProcessingError: If loading fails

    Example:
        >>> csv_file = CSVFile(Path("data.csv"))
        >>> config = DatabaseConfig(host="localhost", dbname="mydb",
        ...                          username="user", password="pass")
        >>> job = load_csv_to_table(csv_file, config, "customers")
        >>> print(f"Loaded {job.records_loaded} records in {job.duration_seconds()}s")
    """
    # Initialize job tracking
    job: LoadJob = LoadJob(source_file=csv_file, target_table=table_name)
    job.start_time = datetime.now()
    job.status = JobStatus.PROCESSING

    log_progress(
        "Starting CSV load operation",
        {
            "file": str(csv_file.file_path),
            "table": table_name,
            "dry_run": dry_run,
        },
    )

    if dry_run:
        # Dry-run mode: validate file can be read and has consistent structure
        try:
            with open(csv_file.file_path, encoding=csv_file.encoding, newline="") as f:
                reader = csv.reader(f, delimiter=csv_file.delimiter)

                # Get expected column count from header
                expected_cols: int = 0
                if csv_file.has_header:
                    header_row: list[str] = next(reader)
                    expected_cols = len(header_row)

                # Validate each row has consistent column count
                row_count: int = 0
                row: list[str]
                for row_num, row in enumerate(
                    reader, start=2 if csv_file.has_header else 1
                ):
                    row_count += 1
                    actual_cols: int = len(row)

                    # Check for malformed rows (inconsistent column count)
                    if csv_file.has_header and actual_cols != expected_cols:
                        error_msg: str = (
                            f"CSV validation failed: Row {row_num} has "
                            f"{actual_cols} columns, expected {expected_cols}"
                        )
                        job.status = JobStatus.FAILED
                        job.error_message = error_msg
                        job.end_time = datetime.now()
                        log_error(
                            "CSV validation failed",
                            {
                                "file": str(csv_file.file_path),
                                "row": row_num,
                                "expected_columns": expected_cols,
                                "actual_columns": actual_cols,
                            },
                        )
                        return job  # Return failed job instead of raising

                job.records_loaded = row_count
                job.status = JobStatus.SUCCESS
                job.end_time = datetime.now()

                # T049: Emit warning for empty CSV (0 data rows)
                if row_count == 0:
                    log_warning(
                        "Empty CSV file - 0 data rows",
                        {
                            "file": str(csv_file.file_path),
                            "rows_validated": row_count,
                        },
                    )

                log_summary(
                    "Dry-run validation complete",
                    {
                        "file": str(csv_file.file_path),
                        "rows_validated": row_count,
                        "duration_seconds": job.duration_seconds(),
                    },
                )
                return job
        except FileProcessingError:
            # Re-raise FileProcessingError as-is (already logged)
            raise
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = f"Dry-run validation failed: {e}"
            job.end_time = datetime.now()
            log_error(
                "Dry-run validation failed",
                {
                    "file": str(csv_file.file_path),
                    "error": str(e),
                },
            )
            raise FileProcessingError(job.error_message) from e

    # Actual load operation
    pool: ConnectionPool = create_connection_pool(db_config)
    try:
        with pool.connection() as conn:
            try:
                with conn.cursor() as cur:
                    # Build COPY command with CSV format and header handling
                    # Handle empty column_names: omit column list from COPY statement
                    copy_sql: Composed
                    if csv_file.column_names:
                        copy_sql = sql.SQL(
                            "COPY {} ({}) FROM STDIN WITH (FORMAT CSV, HEADER {})"
                        ).format(
                            sql.Identifier(table_name),
                            sql.SQL(", ").join(
                                [sql.Identifier(col) for col in csv_file.column_names]
                            ),
                            sql.SQL("TRUE" if csv_file.has_header else "FALSE"),
                        )
                    else:
                        # No column list specified - use all table columns in order
                        copy_sql = sql.SQL(
                            "COPY {} FROM STDIN WITH (FORMAT CSV, HEADER {})"
                        ).format(
                            sql.Identifier(table_name),
                            sql.SQL("TRUE" if csv_file.has_header else "FALSE"),
                        )

                    # Stream CSV file into database using COPY
                    with (
                        open(
                            csv_file.file_path,
                            encoding=csv_file.encoding,
                            newline="",
                        ) as f,
                        cur.copy(copy_sql) as copy,
                    ):
                        # Read and write in chunks to handle large files
                        chunk_size: int = 8192  # 8KB chunks
                        chunk: str
                        while chunk := f.read(chunk_size):
                            copy.write(chunk)

                    # Get row count from COPY operation
                    job.records_loaded = cur.rowcount

                # Commit transaction
                conn.commit()
                job.status = JobStatus.SUCCESS
                job.end_time = datetime.now()

                # T049: Emit warning for empty CSV (0 data rows)
                if job.records_loaded == 0:
                    log_warning(
                        "Empty CSV file - 0 data rows loaded",
                        {
                            "file": str(csv_file.file_path),
                            "table": table_name,
                            "records_loaded": job.records_loaded,
                        },
                    )

                log_summary(
                    "CSV load complete",
                    {
                        "file": str(csv_file.file_path),
                        "table": table_name,
                        "records_loaded": job.records_loaded,
                        "duration_seconds": job.duration_seconds(),
                    },
                )

            except Exception as e:
                # Rollback on any error (FR-011: atomic loading)
                conn.rollback()
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.end_time = datetime.now()
                log_error(
                    "CSV load failed",
                    {
                        "file": str(csv_file.file_path),
                        "table": table_name,
                        "error": str(e),
                    },
                )
                raise FileProcessingError(
                    f"Failed to load CSV file '{csv_file.file_path.name}' "
                    f"into table '{table_name}': {e}"
                ) from e

    finally:
        pool.close(timeout=db_config.connection_timeout)

    return job
