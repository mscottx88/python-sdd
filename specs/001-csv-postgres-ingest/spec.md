# Feature Specification: CSV to Postgres Data Pipeline

**Feature Branch**: `001-csv-postgres-ingest`
**Created**: 2026-01-20
**Status**: Draft
**Input**: User description: "Create a data pipeline that ingests CSV files into a Postgres database with high-performance bulk loading and concurrent processing capabilities"

## Clarifications

### Session 2026-01-20

- Q: When a CSV file contains only a header row (0 data rows), what should the system do? → A: Allow the operation, complete successfully with 0 records loaded and log a warning
- Q: When the target table does not exist in the database, what should the system do? → A: Support auto-create table as an opt-in feature with configuration flag (default: fail with error)
- Q: When CSV column names don't match table column names, what should the matching policy be? → A: Allow all variations with configuration: strict exact match (default), case-insensitive matching, subset matching (CSV missing optional columns), extra column handling (ignore unmapped CSV columns)
- Q: For logging (FR-012: "log processing progress"), what format and destination should be used? → A: Structured JSON logs to stderr (machine-parseable, supports log aggregation)
- Q: For database credentials (FR-002), how should they be provided to the system in CLI mode? → A: Support multiple methods: environment variables (preferred), connection string, or config file

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Single CSV File Ingestion (Priority: P1)

A data engineer needs to load a single CSV file into a Postgres database table. They provide the file path, target table name, and database connection details. The system reads the CSV, validates its structure, and loads all records into the specified table efficiently.

**Why this priority**: This is the core MVP functionality - the ability to load one file into one table. Without this, nothing else matters. It delivers immediate value for simple data loading scenarios.

**Independent Test**: Can be fully tested by providing a sample CSV file, database credentials, and target table name. Success is verified by querying the database and confirming all records were inserted correctly.

**Acceptance Scenarios**:

1. **Given** a valid CSV file with 1000 rows and a target table exists, **When** the pipeline processes the file, **Then** all 1000 rows are inserted into the table
2. **Given** a CSV file with headers matching table columns, **When** the pipeline processes the file, **Then** data is mapped correctly to corresponding columns
3. **Given** a successfully loaded file, **When** the process completes, **Then** the system reports the number of records loaded and processing time

---

### User Story 2 - Error Handling and Recovery (Priority: P2)

When processing fails due to data validation errors, connection issues, or malformed files, the system provides clear error messages indicating what went wrong and where. Failed files can be reprocessed after fixing issues without affecting successfully loaded data.

**Why this priority**: Production systems need robust error handling. This ensures operators can diagnose and fix issues quickly without data loss or corruption. Builds on P1 by adding production-readiness.

**Independent Test**: Can be tested by providing invalid CSV files (missing columns, type mismatches, corrupt data) and verifying appropriate error messages are generated, no partial data is loaded.

**Acceptance Scenarios**:

1. **Given** a CSV file with a column type mismatch, **When** the pipeline attempts to load it, **Then** a clear error message identifies the problematic column and row
2. **Given** a database connection failure mid-processing, **When** the error occurs, **Then** the transaction is rolled back and no partial data remains
3. **Given** a malformed CSV file with inconsistent column counts, **When** validation runs, **Then** the error is detected before any database operations begin
4. **Given** a previously failed file has been corrected, **When** reprocessing is initiated, **Then** the file loads successfully without affecting previously loaded data

---

### Edge Cases

- **Empty CSV file (0 data rows, only headers)**: System completes successfully with 0 records loaded, logs a warning, and maintains transaction consistency. This is not treated as an error.
- **Extremely large CSV files (>1GB)**: System handles files up to 5GB without memory issues (see SC-002). Uses streaming and COPY FROM STDIN for constant memory usage regardless of file size.
- **Target table doesn't exist**: By default, fail immediately with clear error. With opt-in `--create-table` flag, auto-create table by inferring schema from CSV column types (TEXT for all columns as safe default).
- **CSV column names don't match table columns**: Default behavior is strict case-sensitive exact matching (fails on mismatch). Configurable options: `--case-insensitive` for case-insensitive matching, `--allow-subset` to permit CSV with fewer columns (uses table defaults/nulls), `--ignore-extra` to ignore unmapped CSV columns.
- **Special characters or quotes in CSV data**: Fully supported per RFC 4180 (FR-012). System handles quoted fields, escaped quotes (double-quote), embedded newlines, and special characters correctly.
- **Different CSV delimiters or encoding**: Configurable via FR-014 (encoding, default UTF-8) and FR-015 (delimiter: comma, tab, semicolon, pipe). System validates and applies configuration before processing.
- **Database disk space exhaustion during COPY**: Out of scope for v1.0. PostgreSQL will raise error, transaction rolls back (FR-009), system reports error (FR-013). Recovery requires manual DBA intervention.
- **Connection pool exhaustion**: System uses connection pools (FR-018) with configurable limits. If pool exhausted, operations queue and wait. Timeout settings prevent indefinite hangs. Proper connection cleanup prevents leaks.
- **Network interruption mid-COPY**: Out of scope for v1.0. Database transaction rolls back on connection loss (FR-009), system reports error (FR-013). No automatic retry mechanism - users must manually reprocess failed files.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST accept CSV file path as input
- **FR-002**: System MUST accept database connection parameters (host, port, database, username, password) via multiple methods: environment variables (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD - preferred for security), connection string, or configuration file. Avoid exposing passwords in CLI arguments.
- **FR-003**: System MUST accept target table name(s) for each CSV file
- **FR-004**: System MUST validate CSV structure before attempting database operations
- **FR-005**: System MUST use bulk loading for data ingestion (not row-by-row insertion). Bulk loading means using database-native bulk insert mechanisms as defined in plan.md technical approach
- **FR-006**: System MUST handle CSV files with headers, mapping columns to table columns
- **FR-007**: System MUST validate that target table exists before processing
- **FR-008**: System MUST validate that CSV columns match table schema (default: strict case-sensitive exact match). System SHOULD support configurable matching modes: case-insensitive matching, subset matching (CSV missing optional table columns), and extra column handling (ignore unmapped CSV columns).
- **FR-009**: System MUST use database transactions to ensure atomic loading (all or nothing per file)
- **FR-010**: System MUST log processing progress (files queued, processing, completed, failed) using structured JSON format to stderr for machine-parseability and log aggregation support
- **FR-011**: System MUST report summary statistics (records loaded, files processed, errors, duration)
- **FR-012**: System MUST handle common CSV variations including: quoted fields per RFC 4180, escaped characters (quotes, newlines), and configurable delimiters (comma, tab, semicolon, pipe)
- **FR-013**: System MUST provide clear error messages with file name, line number, and error description
- **FR-014**: System MUST support configurable CSV encoding (default: UTF-8)
- **FR-015**: System MUST support configurable CSV delimiter (default: comma)
- **FR-016**: System MUST close database connections properly after each file processing
- **FR-017**: System MUST support dry-run mode to validate files without loading data
- **FR-018**: System MUST use connection pools for all database connections and MUST use connection pool context managers to ensure proper resource cleanup

### Key Entities

- **CSV File**: Represents a source data file with structured tabular data in CSV format. Attributes include file path, size, row count, column names, delimiter, and encoding.
- **Database Connection**: Represents connection details for the target Postgres database. Attributes include host, port, database name, credentials, and connection pool settings (min/max pool size, timeouts). See data-model.md for complete DatabaseConfig specification.
- **Load Job**: Represents a single file ingestion operation. Attributes include source file, target table, status (pending/processing/success/failed), start time, end time, records loaded, error message.
- **Table Schema**: Represents the target database table structure. Attributes include table name, column names, column types, constraints.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: System successfully loads a 100MB CSV file (1 million rows) in under 30 seconds
- **SC-002**: System handles CSV files up to 5GB without memory issues
- **SC-003**: 100% of valid CSV files with correct schema load successfully
- **SC-004**: 100% of invalid CSV files are rejected with clear error messages before database operations
- **SC-005**: System maintains database integrity - zero occurrences of partial data loads on failures
- **SC-006**: Error messages enable operators to fix issues within 5 minutes for these specific common problems: (1) schema mismatch (column name or count differences), (2) encoding issues (non-UTF-8 files), (3) malformed CSV (inconsistent column counts), (4) connection failures (host unreachable, wrong credentials), (5) permission errors (insufficient database privileges)
- **SC-007**: Database connection count never exceeds pool limits (connection leak prevention)

## Assumptions

- Target Postgres tables already exist by default (table creation available as opt-in feature via configuration flag)
- CSV files are accessible from the file system where the pipeline runs
- Database credentials have INSERT permissions on target tables
- Network connectivity to Postgres database is stable
- CSV files use standard formats (RFC 4180 compliant or close variations)
- Column mapping is based on header names matching table column names (default: case-sensitive exact match, configurable to allow case-insensitive, subset, or extra columns)
- One CSV file maps to one table (multi-table splitting is out of scope)
- Data type conversions are handled by Postgres during COPY (pipeline doesn't transform data)
- Duplicate detection/handling is out of scope (all rows in CSV are loaded)
- Table must have sufficient columns to accept all CSV columns (extra table columns can have defaults)

## Out of Scope

- Incremental loading (detecting and loading only new/changed records)
- Data transformation or cleaning (ETL transforms)
- Modifying existing database table schemas
- Handling compressed CSV files (zip, gzip) - must be uncompressed first
- Loading from remote sources (S3, HTTP) - must be local files
- Real-time streaming or CDC (change data capture)
- Support for databases other than Postgres
- GUI or web interface (CLI/library only)
- Scheduling or orchestration (use external schedulers)
- Data quality rules or validation beyond schema matching
- Automatic retry on network interruption mid-COPY (v1.0 limitation: transactions roll back, manual reprocessing required; consider for v2.0)
