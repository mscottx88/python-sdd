"""Database operations for CSV to Postgres pipeline."""

from typing import Any

from psycopg import sql
from psycopg.sql import Composed
from psycopg_pool import ConnectionPool

from src.csv_postgres_pipeline.exceptions import DatabaseError
from src.csv_postgres_pipeline.models import (
    ColumnInfo,
    CSVFile,
    DatabaseConfig,
    TableSchema,
)


def create_connection_pool(config: DatabaseConfig) -> ConnectionPool:
    """Create a connection pool from database configuration.

    Args:
        config: Database connection configuration

    Returns:
        ConnectionPool instance configured with specified min/max sizes

    Example:
        >>> config = DatabaseConfig(host="localhost", dbname="mydb",
        ...                          username="user", password="pass")
        >>> pool = create_connection_pool(config)
        >>> try:
        ...     with pool.connection() as conn:
        ...         # Use connection
        ...         pass
        ... finally:
        ...     pool.close()
    """
    return ConnectionPool(
        conninfo=config.to_conninfo(),
        min_size=config.pool_min_size,
        max_size=config.pool_max_size,
        timeout=config.connection_timeout,
    )


def create_table_from_csv(
    config: DatabaseConfig, table_name: str, csv_file: CSVFile
) -> TableSchema:
    """Create a new table based on CSV column names.

    All columns are created as TEXT type (safe default) and nullable.
    This is a conservative approach that ensures data compatibility.

    Args:
        config: Database connection configuration
        table_name: Name of the table to create
        csv_file: CSVFile with parsed column names

    Returns:
        TableSchema of the newly created table

    Raises:
        DatabaseError: If table creation fails or CSV has no columns

    Example:
        >>> config = DatabaseConfig(host="localhost", dbname="mydb",
        ...                          username="user", password="pass")
        >>> csv_file = CSVFile(Path("data.csv"))
        >>> validate_csv_file(csv_file)  # Parse column names
        >>> schema = create_table_from_csv(config, "new_table", csv_file)
        >>> print(schema.column_names())
        ['col1', 'col2', 'col3']
    """
    if not csv_file.column_names:
        raise DatabaseError(
            "Cannot create table from CSV: no column names available. "
            "Ensure CSV has been validated first."
        )

    pool: ConnectionPool = create_connection_pool(config)
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            # Build column definitions (all TEXT and nullable for safety)
            column_defs: list[sql.Composable] = [
                sql.SQL("{} TEXT").format(sql.Identifier(col_name))
                for col_name in csv_file.column_names
            ]

            # Build CREATE TABLE statement
            create_stmt: Composed = sql.SQL("CREATE TABLE {} ({})").format(
                sql.Identifier(table_name), sql.SQL(", ").join(column_defs)
            )

            try:
                cur.execute(create_stmt)
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise DatabaseError(f"Failed to create table '{table_name}': {e}") from e

            # Build TableSchema for the created table
            columns: list[ColumnInfo] = [
                ColumnInfo(
                    name=col_name,
                    data_type="text",
                    is_nullable=True,
                    ordinal_position=idx + 1,
                    column_default=None,
                )
                for idx, col_name in enumerate(csv_file.column_names)
            ]

            return TableSchema(table_name=table_name, columns=columns)
    finally:
        pool.close()


def get_table_schema(
    config: DatabaseConfig,
    table_name: str,
    create_if_missing: bool = False,
    csv_file: CSVFile | None = None,
) -> TableSchema:
    """Retrieve table schema from database using information_schema.

    Args:
        config: Database connection configuration
        table_name: Name of the table to introspect
        create_if_missing: If True and table doesn't exist, create it from csv_file
        csv_file: CSVFile with column names (required if create_if_missing=True)

    Returns:
        TableSchema with columns metadata

    Raises:
        DatabaseError: If table does not exist (and create_if_missing=False)
            or connection fails
        ValueError: If create_if_missing=True but csv_file is None

    Example:
        >>> config = DatabaseConfig(host="localhost", dbname="mydb",
        ...                          username="user", password="pass")
        >>> schema = get_table_schema(config, "customers")
        >>> print(schema.column_names())
        ['id', 'name', 'email']

        >>> # With automatic table creation
        >>> csv_file = CSVFile(Path("data.csv"))
        >>> validate_csv_file(csv_file)
        >>> schema = get_table_schema(
        ...     config, "new_table", create_if_missing=True, csv_file=csv_file
        ... )
    """
    pool: ConnectionPool = create_connection_pool(config)
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            # Query information_schema for table columns
            query: sql.SQL = sql.SQL(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    ordinal_position,
                    column_default
                FROM information_schema.columns
                WHERE table_name = %s
                    AND table_schema = 'public'
                ORDER BY ordinal_position
                """
            )

            cur.execute(query, (table_name,))
            rows: list[tuple[Any, ...]] = cur.fetchall()

            if not rows:
                # Table doesn't exist
                if create_if_missing:
                    if csv_file is None:
                        raise ValueError(
                            "csv_file parameter is required when create_if_missing=True"
                        )
                    pool.close()  # Close current pool before creating table
                    return create_table_from_csv(config, table_name, csv_file)
                raise DatabaseError(
                    f"Table '{table_name}' not found in database '{config.dbname}'"
                )

            columns: list[ColumnInfo] = [
                ColumnInfo(
                    name=row[0],
                    data_type=row[1],
                    is_nullable=(row[2] == "YES"),
                    ordinal_position=row[3],
                    column_default=row[4],
                )
                for row in rows
            ]

            return TableSchema(table_name=table_name, columns=columns)
    finally:
        pool.close()


def validate_connection(config: DatabaseConfig) -> tuple[bool, str | None]:
    """Validate database connection can be established.

    Args:
        config: Database connection configuration

    Returns:
        (is_valid, error_message) tuple
        - is_valid: True if connection successful
        - error_message: Error description if connection failed, None otherwise

    Example:
        >>> config = DatabaseConfig(host="localhost", dbname="mydb",
        ...                          username="user", password="pass")
        >>> is_valid, error = validate_connection(config)
        >>> if not is_valid:
        ...     print(f"Connection failed: {error}")
    """
    try:
        pool: ConnectionPool = create_connection_pool(config)
        try:
            with pool.connection() as conn, conn.cursor() as cur:
                # Simple query to verify connection works
                cur.execute("SELECT 1")
                result: tuple[Any, ...] | None = cur.fetchone()
                if result and result[0] == 1:
                    return True, None
                return False, "Unexpected query result"
        finally:
            pool.close()
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Connection validation catch-all to return tuple status
        return False, str(e)
