"""Command-line interface for CSV to Postgres pipeline.

Phase 6 implementation - CLI entry point for pipeline operations.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from psycopg_pool import ConnectionPool

from src.csv_postgres_pipeline import database, loader, models, validator
from src.csv_postgres_pipeline.exceptions import (
    ConfigurationError,
    DatabaseError,
    FileProcessingError,
    ValidationError,
)

# Exit codes
EXIT_SUCCESS: int = 0
EXIT_VALIDATION_ERROR: int = 1
EXIT_CONNECTION_ERROR: int = 2
EXIT_LOAD_ERROR: int = 3
EXIT_UNKNOWN_ERROR: int = 4


def main(args: list[str] | None = None) -> int:
    """Main entry point for CLI.

    Args:
        args: Command-line arguments (for testing). If None, uses sys.argv.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser: argparse.ArgumentParser = create_parser()
    parsed_args: argparse.Namespace = parser.parse_args(args)

    # Configure logging
    log_level: int = logging.DEBUG if parsed_args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    try:
        # Build database configuration from args + environment variables
        # Note: In dry-run mode, database config may not be needed but we
        # still validate it
        try:
            db_config: models.DatabaseConfig = _build_db_config(parsed_args)
        except ValueError as e:
            # In dry-run mode, we might not need database config for validation
            if parsed_args.dry_run:
                # Create a dummy config for dry-run validation
                db_config = models.DatabaseConfig(
                    host="localhost",
                    port=5432,
                    dbname="dummy",
                    username="dummy",
                    password="dummy",
                    connection_timeout=parsed_args.connection_timeout,
                )
            raise ConfigurationError(str(e)) from e

        # Build pipeline configuration
        pipeline_config: models.PipelineConfig = models.PipelineConfig(
            dry_run=parsed_args.dry_run,
            create_table=parsed_args.create_table,
            case_insensitive=parsed_args.case_insensitive,
            allow_subset=parsed_args.allow_subset,
            ignore_extra=parsed_args.ignore_extra,
        )

        # Execute single file mode
        return _handle_single_file_mode(parsed_args, db_config, pipeline_config)

    except ValidationError as e:
        logging.error("Validation failed: %s", e)
        return EXIT_VALIDATION_ERROR
    except (DatabaseError, ConfigurationError) as e:
        logging.error("Database/configuration error: %s", e)
        return EXIT_CONNECTION_ERROR
    except FileProcessingError as e:
        logging.error("File processing error: %s", e)
        return EXIT_LOAD_ERROR
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Top-level catch-all for unexpected errors in CLI main function
        logging.error("Unexpected error: %s", e)
        if parsed_args.verbose:
            logging.exception("Full traceback:")
        return EXIT_UNKNOWN_ERROR


def _build_db_config(args: argparse.Namespace) -> models.DatabaseConfig:
    """Build database configuration from CLI args and environment variables.

    Args:
        args: Parsed CLI arguments

    Returns:
        DatabaseConfig instance

    Raises:
        ValueError: If required database parameters are missing
    """
    host: str = args.host or os.getenv("PGHOST", "localhost")
    port: int = args.port or int(os.getenv("PGPORT", "5432"))
    db_name: str | None = args.database or os.getenv("PGDATABASE")
    username: str | None = args.username or os.getenv("PGUSER")
    password: str | None = args.password or os.getenv("PGPASSWORD")
    connection_timeout: int = args.connection_timeout

    if not db_name:
        raise ValueError("Database name is required (--database or PGDATABASE env var)")
    if not username:
        raise ValueError("Username is required (--username or PGUSER env var)")
    if not password:
        raise ValueError("Password is required (--password or PGPASSWORD env var)")

    return models.DatabaseConfig(
        host=host,
        port=port,
        dbname=db_name,
        username=username,
        password=password,
        pool_max_size=4,  # Default pool size
        connection_timeout=connection_timeout,
    )


# pylint: disable=too-many-return-statements
# Multiple early returns for validation steps improve readability
def _handle_single_file_mode(
    args: argparse.Namespace,
    db_config: models.DatabaseConfig,
    _pipeline_config: models.PipelineConfig,
) -> int:
    """Handle single file loading.

    Args:
        args: Parsed CLI arguments
        db_config: Database configuration
        pipeline_config: Pipeline configuration

    Returns:
        Exit code
    """
    source_path: Path = args.source
    table_name: str = args.target_table

    if not source_path.exists():
        logging.error("File not found: %s", source_path)
        return EXIT_VALIDATION_ERROR

    if not source_path.is_file():
        logging.error("Not a file: %s", source_path)
        return EXIT_VALIDATION_ERROR

    logging.info("Validating %s...", source_path.name)

    # Validate file
    csv_file: models.CSVFile = models.CSVFile(
        file_path=source_path,
        delimiter=args.delimiter,
        encoding=args.encoding,
    )
    try:
        validator.validate_csv_file(csv_file)
    except ValidationError as e:
        logging.error("Validation failed: %s", e)
        return EXIT_VALIDATION_ERROR

    logging.info(
        "Validation passed: %s rows, %s columns",
        csv_file.row_count,
        len(csv_file.column_names),
    )

    # Dry run mode - stop here
    if args.dry_run:
        logging.info("[DRY-RUN] Validation successful - no data loaded")
        return EXIT_SUCCESS

    # Load data
    logging.info("Loading %s to '%s' table...", source_path.name, table_name)

    # Create connection pool
    pool: ConnectionPool = database.create_connection_pool(db_config)

    try:
        start_time: float = time.time()

        loader.load_csv_to_table(
            csv_file=csv_file,
            db_config=db_config,
            table_name=table_name,
            dry_run=False,
        )

        duration: float = time.time() - start_time
        row_count: int = csv_file.row_count or 0
        throughput: float = row_count / duration if duration > 0 else 0

        logging.info(
            "Loaded %s rows in %s seconds (%s rows/sec)",
            row_count,
            f"{duration:.1f}",
            f"{throughput:.0f}",
        )
        logging.info("[SUCCESS] File loaded successfully")

    except Exception as e:  # pylint: disable=broad-exception-caught
        # Catch-all for runtime errors during load with connection classification
        error_msg: str = str(e).lower()
        # Check if it's a connection-related error
        if any(
            keyword in error_msg
            for keyword in ["connection", "connect", "timeout", "refused"]
        ):
            logging.error("Connection failed: %s", e)
            if args.verbose:
                logging.exception("Full traceback:")
            return EXIT_CONNECTION_ERROR

        logging.error("Load failed: %s", e)
        if args.verbose:
            logging.exception("Full traceback:")
        return EXIT_LOAD_ERROR
    finally:
        pool.close()

    return EXIT_SUCCESS


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI.

    Returns:
        Configured ArgumentParser instance
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="csv-postgres-pipeline",
        description=(
            "Load CSV files into PostgreSQL tables with validation and bulk operations"
        ),
    )

    # Positional arguments
    parser.add_argument(
        "source",
        type=Path,
        help="CSV file path",
        metavar="SOURCE",
    )

    parser.add_argument(
        "target_table",
        type=str,
        help="Target PostgreSQL table name",
        metavar="TARGET_TABLE",
    )

    # Database connection options
    db_group: argparse._ArgumentGroup = parser.add_argument_group("database connection")
    db_group.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Database host (default: localhost, or PGHOST env var)",
    )
    db_group.add_argument(
        "--port",
        type=int,
        default=5432,
        help="Database port (default: 5432, or PGPORT env var)",
    )
    db_group.add_argument(
        "--database",
        "--dbname",
        type=str,
        required=False,
        help="Database name (required, or PGDATABASE env var)",
    )
    db_group.add_argument(
        "--username",
        "--user",
        type=str,
        required=False,
        help="Database username (required, or PGUSER env var)",
    )
    db_group.add_argument(
        "--password",
        type=str,
        required=False,
        help="Database password (or PGPASSWORD env var, recommended)",
    )
    db_group.add_argument(
        "--connection-timeout",
        type=int,
        default=30,
        help="Connection timeout in seconds (default: 30)",
    )

    # Processing options
    proc_group: argparse._ArgumentGroup = parser.add_argument_group("processing options")
    proc_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate files without loading data (FR-020)",
    )

    # CSV format options
    csv_group: argparse._ArgumentGroup = parser.add_argument_group("CSV format")
    csv_group.add_argument(
        "--delimiter",
        type=str,
        default=",",
        help="CSV delimiter (default: comma) (FR-017)",
    )
    csv_group.add_argument(
        "--encoding",
        type=str,
        default="utf-8",
        help="CSV encoding (default: utf-8) (FR-016)",
    )

    # Phase 3b configuration flags
    config_group: argparse._ArgumentGroup = parser.add_argument_group(
        "column matching configuration (Phase 3b)"
    )
    config_group.add_argument(
        "--create-table",
        action="store_true",
        help="Auto-create missing tables with TEXT columns (opt-in)",
    )
    config_group.add_argument(
        "--case-insensitive",
        action="store_true",
        help="Case-insensitive column name matching",
    )
    config_group.add_argument(
        "--allow-subset",
        action="store_true",
        help="Allow CSV with fewer columns than table (use defaults/nulls)",
    )
    config_group.add_argument(
        "--ignore-extra",
        action="store_true",
        help="Ignore unmapped CSV columns not in table",
    )

    # Output options
    output_group: argparse._ArgumentGroup = parser.add_argument_group("output")
    output_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    output_group.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    return parser


if __name__ == "__main__":
    sys.exit(main())
