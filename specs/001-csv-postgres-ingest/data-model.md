# Data Model: CSV to Postgres Data Pipeline

**Phase**: 1 - Design
**Date**: 2026-01-20
**Purpose**: Define Python data classes for all entities in the system

---

## Overview

The data model defines five core entities that represent the domain objects in the CSV to Postgres pipeline. All classes use Python 3.13 features including dataclasses, type hints, and enums for type safety.

---

## Entity: CSVFile

**Purpose**: Represents a CSV file to be loaded, including metadata and validation state.

**Attributes**:

- `file_path: Path` - Absolute path to CSV file
- `size_bytes: int` - File size in bytes
- `row_count: int | None` - Number of data rows (excluding header), None until counted
- `column_names: List[str]` - Column names from CSV header
- `delimiter: str` - CSV delimiter character (default ',')
- `encoding: str` - File encoding (default 'utf-8')
- `has_header: bool` - Whether CSV has header row (default True)
- `validation_status: ValidationStatus` - Current validation state

**Validation Rules**:

- `file_path` must exist and be readable
- `size_bytes` must be positive
- `delimiter` must be single character
- `encoding` must be valid Python codec
- `column_names` must not be empty if `has_header=True`

**State Transitions**:

```
NOT_VALIDATED → VALIDATING → VALID | INVALID
```

**Python Implementation**:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from enum import Enum, auto

class ValidationStatus(Enum):
    NOT_VALIDATED = auto()
    VALIDATING = auto()
    VALID = auto()
    INVALID = auto()

@dataclass
class CSVFile:
    file_path: Path
    delimiter: str = ','
    encoding: str = 'utf-8'
    has_header: bool = True
    size_bytes: int = field(init=False)
    row_count: int | None = field(default=None, init=False)
    column_names: List[str] = field(default_factory=list, init=False)
    validation_status: ValidationStatus = field(default=ValidationStatus.NOT_VALIDATED, init=False)

    def __post_init__(self):
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")
        if not self.file_path.is_file():
            raise ValueError(f"Path is not a file: {self.file_path}")
        self.size_bytes = self.file_path.stat().st_size
```

---

## Entity: DatabaseConfig

**Purpose**: Contains all information needed to connect to Postgres database.

**Attributes**:

- `host: str` - Database server hostname or IP
- `port: int` - Database server port (default 5432)
- `dbname: str` - Database name (uses psycopg3 standard parameter name)
- `username: str` - Database user
- `password: str` - Database password (sensitive)
- `connection_timeout: int` - Connection timeout in seconds (default 30)
- `command_timeout: int | None` - Query timeout in seconds (None = no limit)
- `pool_min_size: int` - Minimum connections in pool (default 1)
- `pool_max_size: int` - Maximum connections in pool (default 10)

**Validation Rules**:

- `host` must not be empty
- `port` must be 1-65535
- `dbname` must not be empty
- `username` must not be empty
- `connection_timeout` must be positive

**Security Considerations**:

- Password should never be logged
- Support loading from environment variables (preferred method)
- Environment variables: PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD

**Credential Handling Methods**:

1. **Environment Variables** (preferred, implemented in Phase 3b):

   ```python
   # From environment
   config = DatabaseConfig.from_env()
   ```

2. **Direct Parameters** (alternative):

   ```python
   # Explicit parameters
   config = DatabaseConfig(
       host="localhost",
       dbname="mydb",
       username="user",
       password="pass"
   )
   ```

3. **Connection String** (future enhancement):
   ```python
   # From connection string (Phase 4+)
   config = DatabaseConfig.from_connection_string("postgresql://user:pass@localhost:5432/mydb")
   ```

**Python Implementation**:

```python
import os
from typing import Optional

@dataclass
class DatabaseConfig:
    host: str
    dbname: str
    username: str
    password: str
    port: int = 5432
    connection_timeout: int = 30
    command_timeout: int | None = None
    pool_min_size: int = 1
    pool_max_size: int = 10

    def __post_init__(self):
        if not self.host:
            raise ValueError("Database host is required")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}")
        if not self.dbname:
            raise ValueError("Database name is required")
        if not self.username:
            raise ValueError("Username is required")
        if self.connection_timeout <= 0:
            raise ValueError("Connection timeout must be positive")
        if self.pool_min_size < 1:
            raise ValueError("Pool min_size must be at least 1")
        if self.pool_max_size < self.pool_min_size:
            raise ValueError("Pool max_size must be >= min_size")

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create DatabaseConfig from environment variables.

        Uses standard PostgreSQL environment variables:
        - PGHOST (default: localhost)
        - PGPORT (default: 5432)
        - PGDATABASE (required)
        - PGUSER (required)
        - PGPASSWORD (required)

        Raises:
            ValueError: If required environment variables are missing
        """
        host = os.getenv("PGHOST", "localhost")
        port_str = os.getenv("PGPORT", "5432")
        dbname = os.getenv("PGDATABASE")
        username = os.getenv("PGUSER")
        password = os.getenv("PGPASSWORD")

        if not dbname:
            raise ValueError("PGDATABASE environment variable is required")
        if not username:
            raise ValueError("PGUSER environment variable is required")
        if not password:
            raise ValueError("PGPASSWORD environment variable is required")

        port = int(port_str)

        return cls(
            host=host,
            port=port,
            dbname=dbname,
            username=username,
            password=password
        )

    def to_conninfo(self) -> str:
        """Generate psycopg connection string."""
        return f"host={self.host} port={self.port} dbname={self.dbname} user={self.username} password={self.password}"
```

**Connection Pool Usage**:

```python
from psycopg_pool import ConnectionPool

# Create pool from config
config = DatabaseConfig(host="localhost", dbname="mydb", username="user", password="pass")
pool = ConnectionPool(config.to_conninfo(), min_size=config.pool_min_size, max_size=config.pool_max_size)

# Use pool with context managers (recommended pattern)
try:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM table")
        results = cur.fetchall()
finally:
    pool.close()
```

---

## Entity: LoadJob

**Purpose**: Represents a single CSV file loading operation with status tracking.

**Attributes**:

- `job_id: str` - Unique identifier (UUID)
- `source_file: CSVFile` - CSV file being loaded
- `target_table: str` - Postgres table name
- `status: JobStatus` - Current job state
- `start_time: datetime | None` - When job started
- `end_time: datetime | None` - When job completed/failed
- `records_loaded: int` - Number of rows successfully loaded
- `error_message: str | None` - Error details if failed
- `transaction_id: int | None` - Postgres transaction ID if available

**Validation Rules**:

- `job_id` must be unique across jobs
- `target_table` must be valid SQL identifier
- `records_loaded` must be non-negative
- `end_time` must be after `start_time` if both set

**State Transitions**:

```

PENDING → PROCESSING → SUCCESS
↓
FAILED

```

**Python Implementation**:

```python
from datetime import datetime
from uuid import uuid4

class JobStatus(Enum):
    PENDING = auto()
    PROCESSING = auto()
    SUCCESS = auto()
    FAILED = auto()

@dataclass
class LoadJob:
    source_file: CSVFile
    target_table: str
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING
    start_time: datetime | None = None
    end_time: datetime | None = None
    records_loaded: int = 0
    error_message: str | None = None
    transaction_id: int | None = None

    def duration_seconds(self) -> float | None:
        """Calculate job duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def is_complete(self) -> bool:
        """Check if job has finished (success or failed)."""
        return self.status in (JobStatus.SUCCESS, JobStatus.FAILED)
```

---

## Entity: TableSchema

**Purpose**: Represents Postgres table structure for validation against CSV.

**Attributes**:

- `table_name: str` - Table name in database
- `columns: List[ColumnInfo]` - List of column metadata
- `schema: str` - Database schema (default 'public')

**ColumnInfo Sub-entity**:

- `name: str` - Column name (case-sensitive)
- `data_type: str` - Postgres data type (e.g., 'integer', 'text')
- `is_nullable: bool` - Whether NULL values allowed
- `ordinal_position: int` - Column position in table (1-based)
- `column_default: str | None` - Default value expression

**Validation Rules**:

- `table_name` must be valid SQL identifier
- `columns` must not be empty
- `ordinal_position` must be unique and sequential

**Python Implementation**:

```python
@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    ordinal_position: int
    column_default: str | None = None

    def accepts_missing_value(self) -> bool:
        """Check if column can be omitted from CSV (nullable or has default)."""
        return self.is_nullable or self.column_default is not None

@dataclass
class TableSchema:
    table_name: str
    columns: List[ColumnInfo]
    schema: str = 'public'

    def column_names(self) -> List[str]:
        """Get list of column names."""
        return [col.name for col in self.columns]

    def validate_csv_columns(self, csv_columns: List[str]) -> tuple[bool, str | None]:
        """Validate CSV columns against table schema.

        Returns:
            (is_valid, error_message)
        """
        table_cols = set(self.column_names())
        csv_cols = set(csv_columns)

        # Check for CSV columns not in table
        extra_csv = csv_cols - table_cols
        if extra_csv:
            return False, f"CSV has columns not in table: {extra_csv}"

        # Check for required table columns missing from CSV
        missing_csv = table_cols - csv_cols
        required_missing = [
            col.name for col in self.columns
            if col.name in missing_csv and not col.accepts_missing_value()
        ]
        if required_missing:
            return False, f"CSV missing required columns: {required_missing}"

        return True, None

    def column_mapping(self, csv_columns: List[str]) -> List[str]:
        """Generate column list for COPY statement.

        Returns list of column names in order matching CSV columns.
        """
        return csv_columns  # CSV order determines COPY order
```

---

## Entity: PipelineConfig

**Purpose**: Global configuration for pipeline execution and column matching behavior.

**Attributes**:

Core execution settings:

- `max_workers: int` - Number of concurrent worker threads (default 4)
- `batch_size: int` - Rows per transaction chunk (default 1000)
- `show_progress: bool` - Display progress bar (default True)

Column matching configuration (Phase 3b):

- `create_table: bool` - Auto-create missing tables with TEXT columns (default False, opt-in)
- `case_insensitive: bool` - Case-insensitive column name matching (default False)
- `allow_subset: bool` - Allow CSV with fewer columns than table (default False)
- `ignore_extra: bool` - Ignore unmapped CSV columns not in table (default False)

Logging configuration:

- `log_format: str` - Output format: "json" or "text" (default "json")

**Validation Rules**:

- `max_workers` must be 1-16 (per FR-008)
- `batch_size` must be positive
- `log_format` must be "json" or "text"

**Python Implementation**:

```python
from pydantic import BaseModel, Field

class PipelineConfig(BaseModel):
    """Pipeline execution configuration."""

    # Core execution settings
    max_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum number of concurrent workers"
    )
    batch_size: int = Field(
        default=1000,
        gt=0,
        description="Number of rows per transaction chunk"
    )
    show_progress: bool = Field(
        default=True,
        description="Enable progress bar display"
    )

    # Column matching configuration (Phase 3b)
    create_table: bool = Field(
        default=False,
        description="Auto-create missing tables with TEXT columns (opt-in)"
    )
    case_insensitive: bool = Field(
        default=False,
        description="Case-insensitive column name matching"
    )
    allow_subset: bool = Field(
        default=False,
        description="Allow CSV with fewer columns than table (use defaults/nulls)"
    )
    ignore_extra: bool = Field(
        default=False,
        description="Ignore unmapped CSV columns not in table"
    )

    # Logging configuration
    log_format: str = Field(
        default="json",
        description="Log format: json or text",
        pattern="^(json|text)$"
    )
```

**Usage Examples**:

```python
# Default configuration (strict matching)
config = PipelineConfig()

# Flexible matching for messy data
config = PipelineConfig(
    case_insensitive=True,
    allow_subset=True,
    ignore_extra=True
)

# Auto-create tables from CSV
config = PipelineConfig(
    create_table=True
)

# JSON logging for production
config = PipelineConfig(
    log_format="json"
)
```

**Column Matching Behavior**:

| Flag                    | Effect                              | Use Case                          |
| ----------------------- | ----------------------------------- | --------------------------------- |
| `create_table=True`     | Creates table if missing (all TEXT) | New tables from CSV               |
| `case_insensitive=True` | "Name" matches "name"               | Inconsistent capitalization       |
| `allow_subset=True`     | CSV can have fewer columns          | Optional columns missing          |
| `ignore_extra=True`     | CSV can have extra columns          | Third-party exports with metadata |

**Combining Flags**:

Flags can be combined for maximum flexibility:

- All False: Strict matching (exact column names, all columns required)
- All True: Maximum flexibility (handles most CSV variations)

---

## Relationships

```
PipelineConfig ──┐
                 ├──> LoadJob ──> CSVFile
DatabaseConfig ──┘       ↓
                         ↓
                   TableSchema
```

**Description**:

- **LoadJob** references one **CSVFile** (the source)
- **LoadJob** references one **TableSchema** (the target)
- **PipelineConfig** applies to all **LoadJobs** in a batch
- **DatabaseConfig** is used to create connections for each **LoadJob**

---

## Type Aliases

**Common types used throughout the codebase**:

```python
from typing import TypeAlias
from pathlib import Path

FilePath: TypeAlias = Path | str
ConnectionString: TypeAlias = str
TableName: TypeAlias = str
JobResult: TypeAlias = tuple[LoadJob, bool]  # (job, success)
```

---

## Summary

Five entities define the complete data model:

1. **CSVFile** - Source file with validation state
2. **DatabaseConfig** - Connection parameters
3. **LoadJob** - Operation tracking with status
4. **TableSchema** - Target table structure
5. **PipelineConfig** - Execution settings

All entities use dataclasses with validation, type hints, and enums for type safety. Ready for implementation in `src/csv_postgres_pipeline/models.py`.
