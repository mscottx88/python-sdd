"""Data models for CSV to Postgres pipeline."""

import os
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from uuid import uuid4

from pydantic import (
    BaseModel,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)


class ValidationStatus(Enum):
    """Status of CSV file validation."""

    NOT_VALIDATED = auto()
    VALIDATING = auto()
    VALID = auto()
    INVALID = auto()


class JobStatus(Enum):
    """Status of a load job."""

    PENDING = auto()
    PROCESSING = auto()
    SUCCESS = auto()
    FAILED = auto()


class CSVFile(BaseModel):
    """Represents a CSV file to be loaded."""

    file_path: Path
    delimiter: str = Field(default=",", description="CSV delimiter character")
    encoding: str = Field(default="utf-8", description="File encoding")
    has_header: bool = Field(default=True, description="Whether CSV has header row")
    size_bytes: int = Field(default=0, description="File size in bytes")
    row_count: int | None = Field(default=None, description="Number of data rows")
    column_names: list[str] = Field(
        default_factory=list, description="Column names from header"
    )
    validation_status: ValidationStatus = Field(
        default=ValidationStatus.NOT_VALIDATED, description="Validation status"
    )

    @model_validator(mode="after")
    def validate_file_path(self) -> "CSVFile":
        """Validate file path exists and is a file, then set size."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")
        if not self.file_path.is_file():
            raise ValueError(f"Path is not a file: {self.file_path}")
        # Set size_bytes if not already set
        if self.size_bytes == 0:
            object.__setattr__(self, "size_bytes", self.file_path.stat().st_size)
        return self


class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    host: str = Field(min_length=1, description="Database host")
    dbname: str = Field(min_length=1, description="Database name")
    username: str = Field(min_length=1, description="Database username")
    password: str = Field(description="Database password")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    connection_timeout: int = Field(
        default=30, gt=0, description="Connection timeout in seconds"
    )
    command_timeout: int | None = Field(
        default=None, description="Command timeout in seconds"
    )
    pool_min_size: int = Field(
        default=1, ge=1, description="Minimum connection pool size"
    )
    pool_max_size: int = Field(
        default=10, ge=1, description="Maximum connection pool size"
    )

    @field_validator("pool_max_size")
    @classmethod
    def validate_pool_max_size(cls, v: int, info: ValidationInfo) -> int:
        """Ensure pool_max_size >= pool_min_size."""
        if "pool_min_size" in info.data and v < info.data["pool_min_size"]:
            raise ValueError(
                f"Pool max_size ({v}) must be >= min_size ({info.data['pool_min_size']})"
            )
        return v

    def to_conninfo(self) -> str:
        """Generate psycopg connection string."""
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} "
            f"user={self.username} password={self.password}"
        )

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create DatabaseConfig from environment variables (FR-002 preferred method).

        Reads PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD environment variables.
        Falls back to defaults for host/port if not set.

        Returns:
            DatabaseConfig instance populated from environment

        Raises:
            ValueError: If required variables (PGDATABASE, PGUSER, PGPASSWORD) are missing

        Example:
            >>> import os
            >>> os.environ['PGDATABASE'] = 'mydb'
            >>> os.environ['PGUSER'] = 'user'
            >>> os.environ['PGPASSWORD'] = 'secret'
            >>> config = DatabaseConfig.from_env()
        """
        # Required variables (explicitly typed as Optional[str])
        dbname: str | None = os.getenv("PGDATABASE")
        username: str | None = os.getenv("PGUSER")
        password: str | None = os.getenv("PGPASSWORD")

        if not all([dbname, username, password]):
            missing: list[str] = [
                k
                for k, v in [
                    ("PGDATABASE", dbname),
                    ("PGUSER", username),
                    ("PGPASSWORD", password),
                ]
                if not v
            ]
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        # After validation, we know these are not None
        assert dbname is not None
        assert username is not None
        assert password is not None

        # Optional with defaults (explicitly typed)
        host: str = os.getenv("PGHOST", "localhost")
        port_str: str = os.getenv("PGPORT", "5432")
        port: int = int(port_str)

        return cls(
            host=host,
            port=port,
            dbname=dbname,
            username=username,
            password=password,
        )


class LoadJob(BaseModel):
    """Represents a single CSV loading operation."""

    source_file: CSVFile
    target_table: str = Field(description="Target database table name")
    job_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique job identifier"
    )
    status: JobStatus = Field(default=JobStatus.PENDING, description="Job status")
    start_time: datetime | None = Field(default=None, description="Job start timestamp")
    end_time: datetime | None = Field(default=None, description="Job end timestamp")
    records_loaded: int = Field(default=0, ge=0, description="Number of records loaded")
    error_message: str | None = Field(default=None, description="Error message if failed")
    transaction_id: int | None = Field(
        default=None, description="Database transaction ID"
    )

    def duration_seconds(self) -> float | None:
        """Calculate job duration in seconds.

        Returns:
            Duration in seconds if both start and end times are set, None otherwise.

        Example:
            >>> job = LoadJob(source_file=csv_file, target_table="customers")
            >>> job.start_time = datetime.now()
            >>> # ... process job ...
            >>> job.end_time = datetime.now()
            >>> print(f"Completed in {job.duration_seconds():.2f}s")
        """
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def is_complete(self) -> bool:
        """Check if job has finished (success or failed).

        Returns:
            True if job status is SUCCESS or FAILED, False if still PENDING or PROCESSING.

        Example:
            >>> job = LoadJob(source_file=csv_file, target_table="customers")
            >>> job.status = JobStatus.PROCESSING
            >>> print(job.is_complete())  # False
            >>> job.status = JobStatus.SUCCESS
            >>> print(job.is_complete())  # True
        """
        return self.status in (JobStatus.SUCCESS, JobStatus.FAILED)


class ColumnInfo(BaseModel):
    """Represents a database table column."""

    name: str = Field(description="Column name")
    data_type: str = Field(description="Column data type")
    is_nullable: bool = Field(description="Whether column accepts NULL")
    ordinal_position: int = Field(ge=1, description="Column position in table")
    column_default: str | None = Field(
        default=None, description="Default value expression"
    )

    def accepts_missing_value(self) -> bool:
        """Check if column can be omitted from CSV.

        A column accepts missing values if it's either nullable or has a default value.
        This is used for validating CSV columns when allow_subset mode is enabled.

        Returns:
            True if column is nullable or has a default value, False otherwise.

        Example:
            >>> col = ColumnInfo(name="id", data_type="integer", is_nullable=False,
            ...                  ordinal_position=1, column_default="nextval('id_seq')")
            >>> print(col.accepts_missing_value())  # True (has default)
        """
        return self.is_nullable or self.column_default is not None


class TableSchema(BaseModel):
    """Represents database table structure."""

    table_name: str = Field(description="Table name")
    columns: list[ColumnInfo] = Field(description="List of table columns")
    # Renamed from 'schema' to 'db_schema' to avoid conflict with
    # BaseModel.schema in mypy strict mode
    db_schema: str = Field(default="public", description="Database schema")

    def column_names(self) -> list[str]:
        """Get list of column names in ordinal order.

        Returns:
            List of column names from the table schema.

        Example:
            >>> schema = TableSchema(table_name="users", columns=[...])
            >>> print(schema.column_names())
            ['id', 'name', 'email', 'created_at']
        """
        return [col.name for col in self.columns]

    # pylint: disable=too-many-locals
    # Comprehensive validation requires tracking multiple comparison sets
    def validate_csv_columns(
        self,
        csv_columns: list[str],
        case_insensitive: bool = False,
        allow_subset: bool = False,
        ignore_extra: bool = False,
    ) -> tuple[bool, str | None]:
        """Validate CSV columns against table schema with configurable matching.

        Args:
            csv_columns: Column names from CSV file
            case_insensitive: If True, match column names case-insensitively
            allow_subset: If True, allow CSV to have subset of table columns
            ignore_extra: If True, ignore extra columns in CSV not in table

        Returns:
            (is_valid, error_message)
        """
        table_cols: list[str] = self.column_names()

        # Build mapping for case-insensitive matching
        table_set: set[str]
        csv_set: set[str]

        if case_insensitive:
            # Create lowercase -> original name mapping
            table_lower_map: dict[str, str] = {col.lower(): col for col in table_cols}
            csv_lower_map: dict[str, str] = {col.lower(): col for col in csv_columns}

            # Check for duplicates in case-insensitive mode
            if len(table_lower_map) != len(table_cols):
                duplicates: list[str] = [
                    col
                    for col in table_cols
                    if sum(1 for c in table_cols if c.lower() == col.lower()) > 1
                ]
                return (
                    False,
                    f"Table has duplicate columns (case-insensitive): {set(duplicates)}",
                )

            if len(csv_lower_map) != len(csv_columns):
                csv_duplicates: list[str] = [
                    col
                    for col in csv_columns
                    if sum(1 for c in csv_columns if c.lower() == col.lower()) > 1
                ]
                return (
                    False,
                    f"CSV has duplicate columns (case-insensitive): "
                    f"{set(csv_duplicates)}",
                )

            table_set = set(table_lower_map.keys())
            csv_set = set(csv_lower_map.keys())
        else:
            table_set = set(table_cols)
            csv_set = set(csv_columns)

        # Check for CSV columns not in table
        extra_csv: set[str] = csv_set - table_set
        if extra_csv and not ignore_extra:
            return False, f"CSV has columns not in table: {extra_csv}"

        # Check for required table columns missing from CSV
        missing_csv: set[str] = table_set - csv_set
        if missing_csv:
            # Find which missing columns are required (not nullable)
            required_cols: list[ColumnInfo] = [
                col for col in self.columns if not col.accepts_missing_value()
            ]

            required_missing: list[str]
            if case_insensitive:
                required_missing = [
                    col.name for col in required_cols if col.name.lower() in missing_csv
                ]
            else:
                required_missing = [
                    col.name for col in required_cols if col.name in missing_csv
                ]

            if required_missing:
                return (
                    False,
                    f"CSV missing required columns: {required_missing}",
                )

            # If allow_subset is False, all optional columns must be present too
            if not allow_subset:
                return False, f"CSV missing optional columns: {missing_csv}"

        return True, None


class PipelineConfig(BaseModel):
    """Pipeline-wide configuration."""

    batch_size: int = Field(default=1000, ge=1, description="Batch size for processing")
    enable_progress_bar: bool = Field(
        default=True, description="Enable progress bar display"
    )
    dry_run: bool = Field(default=False, description="Validate without loading data")
    create_table: bool = Field(
        default=False, description="Auto-create missing tables with TEXT columns"
    )
    case_insensitive: bool = Field(
        default=False, description="Case-insensitive column name matching"
    )
    allow_subset: bool = Field(
        default=False,
        description="Allow CSV with fewer columns than table (use defaults/nulls)",
    )
    ignore_extra: bool = Field(default=False, description="Ignore unmapped CSV columns")
    log_format: str = Field(
        default="json",
        description="Logging format: 'json' or 'text'",
        pattern="^(json|text)$",
    )
