"""Unit tests for database operations."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.csv_postgres_pipeline.database import (
    create_connection_pool,
    create_table_from_csv,
    get_table_schema,
    validate_connection,
)
from src.csv_postgres_pipeline.exceptions import DatabaseError
from src.csv_postgres_pipeline.models import (
    ColumnInfo,
    CSVFile,
    DatabaseConfig,
    TableSchema,
    ValidationStatus,
)


class TestCreateConnectionPool:
    """Tests for create_connection_pool function."""

    def test_create_connection_pool_with_config(self) -> None:
        """Test connection pool creation with valid config."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
            pool_min_size=2,
            pool_max_size=5,
        )

        with patch("src.csv_postgres_pipeline.database.ConnectionPool") as mock_pool:
            create_connection_pool(config)

            mock_pool.assert_called_once()
            call_kwargs = mock_pool.call_args.kwargs
            assert call_kwargs["min_size"] == 2
            assert call_kwargs["max_size"] == 5
            assert call_kwargs["timeout"] == 30

    def test_connection_pool_uses_conninfo(self) -> None:
        """Test connection pool receives correct connection string."""
        config = DatabaseConfig(
            host="testhost",
            dbname="testdb",
            username="testuser",
            password="testpass",
            port=5433,
        )

        with patch("src.csv_postgres_pipeline.database.ConnectionPool") as mock_pool:
            create_connection_pool(config)

            conninfo = mock_pool.call_args.kwargs["conninfo"]
            assert "host=testhost" in conninfo
            assert "port=5433" in conninfo
            assert "dbname=testdb" in conninfo
            assert "user=testuser" in conninfo


class TestGetTableSchema:
    """Tests for get_table_schema function."""

    def test_get_table_schema_success(self) -> None:
        """Test successful table schema retrieval."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        # Mock database response
        mock_rows = [
            ("id", "integer", "NO", 1, None),
            ("name", "text", "NO", 2, None),
            ("email", "text", "YES", 3, "NULL"),
        ]

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = mock_rows

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.database.create_connection_pool",
            return_value=mock_pool,
        ):
            schema = get_table_schema(config, "test_table")

            assert schema.table_name == "test_table"
            assert len(schema.columns) == 3
            assert schema.columns[0].name == "id"
            assert schema.columns[0].data_type == "integer"
            assert schema.columns[0].is_nullable is False
            assert schema.columns[1].name == "name"
            assert schema.columns[2].is_nullable is True
            mock_pool.close.assert_called_once()

    def test_get_table_schema_table_not_found(self) -> None:
        """Test error handling when table does not exist."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = []  # No rows = table not found

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.database.create_connection_pool",
            return_value=mock_pool,
        ):
            with pytest.raises(DatabaseError, match="not found"):
                get_table_schema(config, "nonexistent_table")

            mock_pool.close.assert_called_once()


class TestValidateConnection:
    """Tests for validate_connection function."""

    def test_validate_connection_success(self) -> None:
        """Test successful connection validation."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = (1,)

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.database.create_connection_pool",
            return_value=mock_pool,
        ):
            is_valid, error = validate_connection(config)

            assert is_valid is True
            assert error is None
            mock_pool.close.assert_called_once()

    def test_validate_connection_failure(self) -> None:
        """Test connection validation handles errors."""
        config = DatabaseConfig(
            host="badhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        with patch(
            "src.csv_postgres_pipeline.database.create_connection_pool",
            side_effect=Exception("Connection refused"),
        ):
            is_valid, error = validate_connection(config)

            assert is_valid is False
            assert error is not None and "Connection refused" in error


class TestConnectionPoolUsage:
    """Tests verifying FR-021 connection pool context manager usage."""

    def test_get_table_schema_uses_pool_context_manager(self) -> None:
        """Verify get_table_schema uses pool.connection() context manager."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = [("id", "integer", "NO", 1, None)]

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.database.create_connection_pool",
            return_value=mock_pool,
        ):
            get_table_schema(config, "test_table")

            # Verify pool.connection() was called (context manager pattern)
            mock_pool.connection.assert_called_once()
            # Verify __enter__ and __exit__ were called (context manager protocol)
            mock_conn.__enter__.assert_called()
            mock_conn.__exit__.assert_called()
            # Verify pool was closed
            mock_pool.close.assert_called_once()

    def test_validate_connection_uses_pool_context_manager(self) -> None:
        """Verify validate_connection uses pool.connection() context manager."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = (1,)

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.database.create_connection_pool",
            return_value=mock_pool,
        ):
            validate_connection(config)

            # Verify connection pool context manager usage
            mock_pool.connection.assert_called_once()
            mock_conn.__enter__.assert_called()
            mock_conn.__exit__.assert_called()
            mock_pool.close.assert_called_once()


class TestCreateTableFromCSV:
    """Tests for create_table_from_csv function."""

    def test_create_table_from_csv_success(self, tmp_path: Path) -> None:
        """Test successful table creation from CSV columns."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        # Create CSV file with columns
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2,col3\nval1,val2,val3\n")
        csv_file = CSVFile(file_path=csv_path)
        csv_file.column_names = ["col1", "col2", "col3"]
        csv_file.validation_status = ValidationStatus.VALID

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.database.create_connection_pool",
            return_value=mock_pool,
        ):
            schema = create_table_from_csv(config, "test_table", csv_file)

            # Verify CREATE TABLE was executed
            mock_cursor.execute.assert_called_once()
            # Just verify it was called, SQL composition objects are complex to inspect

            # Verify commit was called
            mock_conn.commit.assert_called_once()

            # Verify returned schema
            assert schema.table_name == "test_table"
            assert len(schema.columns) == 3
            assert schema.columns[0].name == "col1"
            assert schema.columns[0].data_type == "text"
            assert schema.columns[0].is_nullable is True
            assert schema.columns[1].name == "col2"
            assert schema.columns[2].name == "col3"

    def test_create_table_from_csv_no_columns(self, tmp_path: Path) -> None:
        """Test error when CSV has no column names."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\nval1,val2\n")
        csv_file = CSVFile(file_path=csv_path)
        csv_file.column_names = []  # No columns

        with pytest.raises(DatabaseError, match="no column names available"):
            create_table_from_csv(config, "test_table", csv_file)

    def test_create_table_from_csv_execution_error(self, tmp_path: Path) -> None:
        """Test error handling when CREATE TABLE fails."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\nval1,val2\n")
        csv_file = CSVFile(file_path=csv_path)
        csv_file.column_names = ["col1", "col2"]

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.execute.side_effect = Exception("Table already exists")

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with patch(
            "src.csv_postgres_pipeline.database.create_connection_pool",
            return_value=mock_pool,
        ):
            with pytest.raises(DatabaseError, match="Failed to create table"):
                create_table_from_csv(config, "test_table", csv_file)

            # Verify rollback was called
            mock_conn.rollback.assert_called_once()


class TestGetTableSchemaWithCreation:
    """Tests for get_table_schema with create_if_missing parameter."""

    def test_get_table_schema_create_if_missing_false(self) -> None:
        """Test default behavior - error when table doesn't exist."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        # Mock empty result (table not found)
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with (
            patch(
                "src.csv_postgres_pipeline.database.create_connection_pool",
                return_value=mock_pool,
            ),
            pytest.raises(DatabaseError, match="not found"),
        ):
            get_table_schema(config, "nonexistent_table", create_if_missing=False)

    def test_get_table_schema_create_if_missing_true_without_csv_file(self) -> None:
        """Test error when create_if_missing=True but csv_file not provided."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        # Mock empty result (table not found)
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with (
            patch(
                "src.csv_postgres_pipeline.database.create_connection_pool",
                return_value=mock_pool,
            ),
            pytest.raises(ValueError, match="csv_file parameter is required"),
        ):
            get_table_schema(config, "new_table", create_if_missing=True, csv_file=None)

    def test_get_table_schema_create_if_missing_true_with_csv_file(
        self, tmp_path: Path
    ) -> None:
        """Test automatic table creation when table doesn't exist."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\nval1,val2\n")
        csv_file = CSVFile(file_path=csv_path)
        csv_file.column_names = ["col1", "col2"]
        csv_file.validation_status = ValidationStatus.VALID

        # Mock empty result for first query (table not found)
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with (
            patch(
                "src.csv_postgres_pipeline.database.create_connection_pool",
                return_value=mock_pool,
            ),
            patch(
                "src.csv_postgres_pipeline.database.create_table_from_csv"
            ) as mock_create,
        ):
            # Mock the create_table_from_csv return value
            expected_schema = TableSchema(
                table_name="new_table",
                columns=[
                    ColumnInfo(
                        name="col1",
                        data_type="text",
                        is_nullable=True,
                        ordinal_position=1,
                    ),
                    ColumnInfo(
                        name="col2",
                        data_type="text",
                        is_nullable=True,
                        ordinal_position=2,
                    ),
                ],
            )
            mock_create.return_value = expected_schema

            schema = get_table_schema(
                config, "new_table", create_if_missing=True, csv_file=csv_file
            )

            # Verify create_table_from_csv was called
            mock_create.assert_called_once_with(config, "new_table", csv_file)

            # Verify returned schema
            assert schema.table_name == "new_table"
            assert len(schema.columns) == 2

    def test_get_table_schema_existing_table_ignores_create_flag(self) -> None:
        """Test that existing tables are returned normally even with create_if_missing=True."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        # Mock successful table schema retrieval
        mock_rows = [
            ("id", "integer", "NO", 1, None),
            ("name", "text", "YES", 2, None),
        ]

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = mock_rows

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn

        with (
            patch(
                "src.csv_postgres_pipeline.database.create_connection_pool",
                return_value=mock_pool,
            ),
            patch(
                "src.csv_postgres_pipeline.database.create_table_from_csv"
            ) as mock_create,
        ):
            schema = get_table_schema(config, "existing_table", create_if_missing=True)

            # create_table_from_csv should NOT be called for existing table
            mock_create.assert_not_called()

            # Verify schema was returned from database
            assert schema.table_name == "existing_table"
            assert len(schema.columns) == 2
            assert schema.columns[0].name == "id"
            assert schema.columns[1].name == "name"
