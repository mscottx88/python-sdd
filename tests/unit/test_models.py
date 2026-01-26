"""Unit tests for data models."""

from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.csv_postgres_pipeline.models import (
    ColumnInfo,
    CSVFile,
    DatabaseConfig,
    JobStatus,
    LoadJob,
    PipelineConfig,
    TableSchema,
    ValidationStatus,
)


class TestCSVFile:
    """Tests for CSVFile dataclass."""

    def test_csvfile_initialization_valid_file(self, tmp_path: Path) -> None:
        """Test CSVFile with valid file."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\n")

        csv_file = CSVFile(file_path=test_file)

        assert csv_file.file_path == test_file
        assert csv_file.size_bytes > 0
        assert csv_file.delimiter == ","
        assert csv_file.encoding == "utf-8"
        assert csv_file.has_header is True
        assert csv_file.validation_status == ValidationStatus.NOT_VALIDATED

    def test_csvfile_nonexistent_file(self) -> None:
        """Test CSVFile raises error for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            CSVFile(file_path=Path("/nonexistent/file.csv"))

    def test_csvfile_directory_path(self, tmp_path: Path) -> None:
        """Test CSVFile raises error for directory path."""
        with pytest.raises(ValueError, match="Path is not a file"):
            CSVFile(file_path=tmp_path)

    def test_csvfile_custom_delimiter(self, tmp_path: Path) -> None:
        """Test CSVFile with custom delimiter."""
        test_file = tmp_path / "test.tsv"
        test_file.write_text("col1\tcol2\n")

        csv_file = CSVFile(file_path=test_file, delimiter="\t")

        assert csv_file.delimiter == "\t"


class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass."""

    def test_databaseconfig_valid(self) -> None:
        """Test DatabaseConfig with valid parameters."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
        )

        assert config.host == "localhost"
        assert config.dbname == "testdb"
        assert config.username == "user"
        assert config.password == "pass"
        assert config.port == 5432
        assert config.connection_timeout == 30
        assert config.pool_min_size == 1
        assert config.pool_max_size == 10

    def test_databaseconfig_invalid_port(self) -> None:
        """Test DatabaseConfig raises error for invalid port."""
        with pytest.raises(ValidationError, match="less than or equal to 65535"):
            DatabaseConfig(
                host="localhost",
                dbname="testdb",
                username="user",
                password="pass",
                port=70000,
            )

    def test_databaseconfig_empty_host(self) -> None:
        """Test DatabaseConfig raises error for empty host."""
        with pytest.raises(
            ValidationError, match="String should have at least 1 character"
        ):
            DatabaseConfig(
                host="",
                dbname="testdb",
                username="user",
                password="pass",
            )

    def test_databaseconfig_pool_validation(self) -> None:
        """Test DatabaseConfig validates pool sizes."""
        with pytest.raises(ValidationError, match="Pool max_size.*must be >= min_size"):
            DatabaseConfig(
                host="localhost",
                dbname="testdb",
                username="user",
                password="pass",
                pool_min_size=10,
                pool_max_size=5,
            )

    def test_to_conninfo(self) -> None:
        """Test connection string generation."""
        config = DatabaseConfig(
            host="localhost",
            dbname="testdb",
            username="user",
            password="pass",
            port=5433,
        )

        conninfo = config.to_conninfo()

        assert "host=localhost" in conninfo
        assert "port=5433" in conninfo
        assert "dbname=testdb" in conninfo
        assert "user=user" in conninfo
        assert "password=pass" in conninfo


class TestLoadJob:
    """Tests for LoadJob dataclass."""

    def test_loadjob_initialization(self, tmp_path: Path) -> None:
        """Test LoadJob initialization."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\n")
        csv_file = CSVFile(file_path=test_file)

        job = LoadJob(source_file=csv_file, target_table="test_table")

        assert job.source_file == csv_file
        assert job.target_table == "test_table"
        assert job.status == JobStatus.PENDING
        assert job.records_loaded == 0
        assert UUID(job.job_id)  # Verify valid UUID

    def test_duration_seconds(self, tmp_path: Path) -> None:
        """Test job duration calculation."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\n")
        csv_file = CSVFile(file_path=test_file)

        job = LoadJob(source_file=csv_file, target_table="test_table")
        job.start_time = datetime(2026, 1, 20, 10, 0, 0)
        job.end_time = datetime(2026, 1, 20, 10, 0, 30)

        assert job.duration_seconds() == 30.0

    def test_duration_seconds_none(self, tmp_path: Path) -> None:
        """Test duration is None when times not set."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\n")
        csv_file = CSVFile(file_path=test_file)

        job = LoadJob(source_file=csv_file, target_table="test_table")

        assert job.duration_seconds() is None

    def test_is_complete(self, tmp_path: Path) -> None:
        """Test job completion check."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\n")
        csv_file = CSVFile(file_path=test_file)

        job = LoadJob(source_file=csv_file, target_table="test_table")
        assert job.is_complete() is False

        job.status = JobStatus.SUCCESS
        assert job.is_complete() is True

        job.status = JobStatus.FAILED
        assert job.is_complete() is True


class TestColumnInfo:
    """Tests for ColumnInfo dataclass."""

    def test_accepts_missing_value_nullable(self) -> None:
        """Test nullable column accepts missing value."""
        col = ColumnInfo(
            name="test_col",
            data_type="text",
            is_nullable=True,
            ordinal_position=1,
        )

        assert col.accepts_missing_value() is True

    def test_accepts_missing_value_has_default(self) -> None:
        """Test column with default accepts missing value."""
        col = ColumnInfo(
            name="test_col",
            data_type="integer",
            is_nullable=False,
            ordinal_position=1,
            column_default="0",
        )

        assert col.accepts_missing_value() is True

    def test_accepts_missing_value_required(self) -> None:
        """Test required column does not accept missing value."""
        col = ColumnInfo(
            name="test_col",
            data_type="text",
            is_nullable=False,
            ordinal_position=1,
        )

        assert col.accepts_missing_value() is False


class TestTableSchema:
    """Tests for TableSchema dataclass."""

    def test_column_names(self) -> None:
        """Test getting column names from schema."""
        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="integer", is_nullable=False, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        assert schema.column_names() == ["col1", "col2"]

    def test_validate_csv_columns_exact_match(self) -> None:
        """Test validation with exact column match."""
        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="integer", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        is_valid, error = schema.validate_csv_columns(["col1", "col2"])

        assert is_valid is True
        assert error is None

    def test_validate_csv_columns_extra_in_csv(self) -> None:
        """Test validation fails with extra CSV columns."""
        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        is_valid, error = schema.validate_csv_columns(["col1", "col2"])

        assert is_valid is False
        assert error is not None and "not in table" in error

    def test_validate_csv_columns_missing_required(self) -> None:
        """Test validation fails with missing required columns."""
        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=False, ordinal_position=1
            ),  # Required
            ColumnInfo(
                name="col2", data_type="integer", is_nullable=True, ordinal_position=2
            ),  # Optional
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        is_valid, error = schema.validate_csv_columns(["col2"])

        assert is_valid is False
        assert error is not None and "missing required columns" in error


class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_pipelineconfig_defaults(self) -> None:
        """Test PipelineConfig default values."""
        config = PipelineConfig()

        assert config.batch_size == 1000
        assert config.enable_progress_bar is True
        assert config.dry_run is False
        assert config.create_table is False
        assert config.case_insensitive is False
        assert config.allow_subset is False
        assert config.ignore_extra is False
        assert config.log_format == "json"

    def test_pipelineconfig_invalid_batch_size(self) -> None:
        """Test PipelineConfig raises error for invalid batch_size."""
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            PipelineConfig(batch_size=0)

    def test_pipelineconfig_configuration_flags(self) -> None:
        """Test PipelineConfig with configuration flags enabled."""
        config = PipelineConfig(
            create_table=True,
            case_insensitive=True,
            allow_subset=True,
            ignore_extra=True,
            log_format="text",
        )

        assert config.create_table is True
        assert config.case_insensitive is True
        assert config.allow_subset is True
        assert config.ignore_extra is True
        assert config.log_format == "text"

    def test_pipelineconfig_invalid_log_format(self) -> None:
        """Test PipelineConfig raises error for invalid log format."""
        with pytest.raises(ValidationError, match="String should match pattern"):
            PipelineConfig(log_format="xml")

    def test_pipelineconfig_column_matching_combinations(self) -> None:
        """Test PipelineConfig with various column matching combinations."""
        # Strict mode (all flags off)
        strict = PipelineConfig()
        assert not strict.case_insensitive
        assert not strict.allow_subset
        assert not strict.ignore_extra

        # Case-insensitive only
        case_insensitive = PipelineConfig(case_insensitive=True)
        assert case_insensitive.case_insensitive
        assert not case_insensitive.allow_subset

        # Subset with case-insensitive
        subset_case = PipelineConfig(case_insensitive=True, allow_subset=True)
        assert subset_case.case_insensitive
        assert subset_case.allow_subset

        # All matching modes enabled
        permissive = PipelineConfig(
            case_insensitive=True, allow_subset=True, ignore_extra=True
        )
        assert permissive.case_insensitive
        assert permissive.allow_subset
        assert permissive.ignore_extra


class TestDatabaseConfigFromEnv:
    """Tests for DatabaseConfig.from_env() method (FR-002)."""

    def test_database_config_from_env_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DatabaseConfig.from_env() with all variables set."""
        # Clear all PG* env vars first
        for key in ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]:
            monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("PGHOST", "testhost")
        monkeypatch.setenv("PGPORT", "5433")
        monkeypatch.setenv("PGDATABASE", "testdb")
        monkeypatch.setenv("PGUSER", "testuser")
        monkeypatch.setenv("PGPASSWORD", "testpass")

        config = DatabaseConfig.from_env()

        assert config.host == "testhost"
        assert config.port == 5433
        assert config.dbname == "testdb"
        assert config.username == "testuser"
        assert config.password == "testpass"

    def test_database_config_from_env_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DatabaseConfig.from_env() uses defaults for host/port."""
        # Clear all PG* env vars first
        for key in ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]:
            monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("PGDATABASE", "testdb")
        monkeypatch.setenv("PGUSER", "testuser")
        monkeypatch.setenv("PGPASSWORD", "testpass")
        # Don't set PGHOST or PGPORT

        config = DatabaseConfig.from_env()

        assert config.host == "localhost"
        assert config.port == 5432

    def test_database_config_from_env_missing_required(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DatabaseConfig.from_env() raises on missing required vars."""
        # Clear all PG* env vars first
        for key in ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]:
            monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("PGHOST", "testhost")
        # Missing PGDATABASE, PGUSER, PGPASSWORD

        with pytest.raises(ValueError, match="Missing required environment variables"):
            DatabaseConfig.from_env()

    def test_database_config_from_env_missing_partial(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DatabaseConfig.from_env() identifies all missing vars."""
        # Clear all PG* env vars first
        for key in ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]:
            monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("PGDATABASE", "testdb")
        # Missing PGUSER and PGPASSWORD

        with pytest.raises(
            ValueError,
            match="Missing required environment variables.*PGUSER.*PGPASSWORD",
        ):
            DatabaseConfig.from_env()
