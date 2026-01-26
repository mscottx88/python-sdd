# CLI Contract: CSV to Postgres Pipeline

**Phase**: 1 - Design
**Date**: 2026-01-20
**Purpose**: Define command-line interface specifications and behavior

---

## Command Structure

The pipeline provides a single command with two modes: single-file and batch processing.

### Single File Mode

```bash
csv-postgres-pipeline FILE TABLE [OPTIONS]
```

**Arguments**:

- `FILE` - Path to CSV file
- `TABLE` - Target Postgres table name

**Example**:

```bash
csv-postgres-pipeline data/customers.csv customers \
  --host localhost --database mydb --username admin --password secret
```

### Batch Mode

```bash
csv-postgres-pipeline --batch DIRECTORY [OPTIONS]
```

**Arguments**:

- `DIRECTORY` - Path to directory containing CSV files

**Table Mapping**:

- Default behavior: Use filename as table name (e.g., customers.csv → customers table)
- Optional override: `--table-map FILE` - JSON/YAML file with explicit CSV-to-table mappings

**Example**:

```bash
# Map filename to table (customers.csv → customers table)
csv-postgres-pipeline --batch data/ \
  --host localhost --database mydb --username admin --password secret

# Use explicit mapping file
csv-postgres-pipeline --batch data/ --table-map mapping.json \
  --host localhost --database mydb --username admin --password secret
```

**mapping.json format**:

```json
{
  "customers.csv": "customers",
  "orders.csv": "orders",
  "products.csv": "products"
}
```

---

## Required Options

### Database Connection

All commands require database connection parameters:

```bash
--host TEXT         Database host [required]
--port INTEGER      Database port [default: 5432]
--database TEXT     Database name [required]
--username TEXT     Database username [required]
--password TEXT     Database password [required or via PGPASSWORD env]
```

**Environment Variable Support**:

- `PGHOST` - Database host
- `PGPORT` - Database port
- `PGDATABASE` - Database name
- `PGUSER` - Username
- `PGPASSWORD` - Password (recommended for security)

**Example using environment variables**:

```bash
export PGHOST=localhost
export PGDATABASE=mydb
export PGUSER=admin
export PGPASSWORD=secret

csv-postgres-pipeline data/file.csv table_name
```

---

## Optional Flags

### Performance Options

```bash
--threads INTEGER         Number of concurrent workers [default: 4, range: 1-16]
--chunk-size INTEGER      Rows per transaction [default: all]
```

### CSV Options

```bash
--delimiter TEXT          CSV delimiter [default: ',']
--encoding TEXT           File encoding [default: 'utf-8']
--no-header              CSV has no header row [default: False]
--skip-lines INTEGER     Lines to skip before header [default: 0]
```

### Validation Options

```bash
--dry-run                Validate files without loading [default: False]
--strict                 Fail on any validation warning [default: False]
--skip-validation        Skip pre-load validation [default: False, NOT RECOMMENDED]
```

### Behavior Options

```bash
--fail-fast              Stop batch on first error [default: False]
--continue-on-error      Continue batch despite errors [default: True]
--verbose, -v            Detailed logging [default: False]
--quiet, -q              Minimal output [default: False]
```

---

## Output Format

### Standard Output (Success)

**Single File**:

```
[INFO] Validating customers.csv...
[INFO] Validation passed: 1000 rows, 5 columns
[INFO] Loading customers.csv to 'customers' table...
[INFO] Loaded 1000 rows in 2.3 seconds (434 rows/sec)
[SUCCESS] File loaded successfully
```

**Batch Processing**:

```
[INFO] Found 3 CSV files in data/
[INFO] Starting batch load with 4 workers...
[INFO] [1/3] Loading customers.csv... ✓ 1000 rows (2.3s)
[INFO] [2/3] Loading orders.csv... ✓ 5000 rows (8.1s)
[INFO] [3/3] Loading products.csv... ✓ 500 rows (1.2s)

Summary:
  Total files: 3
  Successful: 3
  Failed: 0
  Total rows: 6500
  Duration: 8.9 seconds
  Throughput: 730 rows/sec
```

### Error Output (Failure)

**Validation Error**:

```
[ERROR] Validation failed: customers.csv
  - Column 'email' not found in table 'customers'
  - Expected columns: id, name, email, created_at
  - CSV columns: id, name, mail, created_at
[ERROR] Load aborted - fix errors and retry
```

**Loading Error**:

```
[INFO] Loading customers.csv to 'customers' table...
[ERROR] Load failed at row 42: customers.csv
  - Type mismatch in column 'age'
  - Expected: integer
  - Got: 'N/A'
  - Row data: 1,John Doe,N/A,2024-01-01
[ERROR] Transaction rolled back - no data loaded
```

**Batch Partial Failure**:

```
[INFO] [1/3] Loading customers.csv... ✓ 1000 rows (2.3s)
[ERROR] [2/3] Loading orders.csv... ✗ Failed at row 105
  - Foreign key violation: customer_id 999 does not exist
[INFO] [3/3] Loading products.csv... ✓ 500 rows (1.2s)

Summary:
  Total files: 3
  Successful: 2
  Failed: 1
  Total rows loaded: 1500
  Duration: 5.5 seconds

Failed files:
  - orders.csv: Foreign key violation at row 105
```

### JSON Output Mode

```bash
--format json           Output in JSON format [default: text]
```

**JSON Success Output**:

```json
{
  "status": "success",
  "files_processed": 3,
  "files_succeeded": 3,
  "files_failed": 0,
  "total_rows": 6500,
  "duration_seconds": 8.9,
  "throughput_rows_per_sec": 730,
  "results": [
    {
      "file": "customers.csv",
      "table": "customers",
      "status": "success",
      "rows_loaded": 1000,
      "duration_seconds": 2.3
    }
  ]
}
```

**JSON Error Output**:

```json
{
  "status": "error",
  "error_type": "ValidationError",
  "error_message": "Column 'email' not found in table 'customers'",
  "file": "customers.csv",
  "details": {
    "expected_columns": ["id", "name", "email", "created_at"],
    "csv_columns": ["id", "name", "mail", "created_at"],
    "missing_columns": ["email"],
    "extra_columns": ["mail"]
  }
}
```

---

## Exit Codes

The CLI uses standard exit codes to indicate status:

| Code | Meaning             | Description                                                    |
| ---- | ------------------- | -------------------------------------------------------------- |
| 0    | Success             | All files loaded successfully                                  |
| 1    | Validation Error    | CSV validation failed (schema mismatch, format errors)         |
| 2    | Connection Error    | Database connection failed                                     |
| 3    | Partial Failure     | Some files failed in batch mode (use with --continue-on-error) |
| 4    | Load Error          | Data loading failed (constraint violation, disk full)          |
| 5    | Configuration Error | Invalid command-line arguments or config                       |
| 130  | Interrupted         | User cancelled with Ctrl+C                                     |

**Usage in Scripts**:

```bash
#!/bin/bash
csv-postgres-pipeline data/file.csv table_name
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "Success!"
elif [ $EXIT_CODE -eq 3 ]; then
  echo "Partial success - check logs"
  exit 0  # May want to treat as success
else
  echo "Failed with code $EXIT_CODE"
  exit $EXIT_CODE
fi
```

---

## Progress Reporting

### Interactive Mode (TTY)

When connected to a terminal, show progress bar for large files:

```
Loading customers.csv: [████████████------] 65% (650K/1M rows) 2.5s
```

### Non-Interactive Mode (Pipe/Log)

When piped or logged, use line-based progress:

```
[INFO] Loading customers.csv: 100000 rows (5.2s)
[INFO] Loading customers.csv: 200000 rows (10.3s)
[INFO] Loading customers.csv: 300000 rows (15.1s)
```

Update interval: Every 100K rows or 5 seconds, whichever comes first.

---

## Logging

### Log Levels

```bash
--log-level LEVEL       Set log level [default: INFO]
                        Choices: DEBUG, INFO, WARNING, ERROR
```

**DEBUG**: All operations including SQL queries

```
[DEBUG] Executing: SELECT column_name FROM information_schema.columns...
[DEBUG] Opening file: data/customers.csv (encoding: utf-8)
[DEBUG] Thread-1: Processing customers.csv
```

**INFO**: Standard progress updates (default)

```
[INFO] Validating customers.csv...
[INFO] Loading customers.csv...
```

**WARNING**: Non-fatal issues

```
[WARNING] CSV has 10 columns but table has 12 - using defaults for missing columns
```

**ERROR**: Fatal errors only

```
[ERROR] Load failed: customers.csv
```

### Log File

```bash
--log-file PATH         Write logs to file [default: stderr]
```

**Example**:

```bash
csv-postgres-pipeline data/file.csv table \
  --log-file /var/log/pipeline.log \
  --log-level DEBUG
```

---

## Configuration File Support

Load options from a configuration file:

```bash
--config FILE           Load options from YAML/JSON file
```

**config.yaml**:

```yaml
database:
  host: localhost
  port: 5432
  database: mydb
  username: admin
  password: secret

pipeline:
  threads: 8
  delimiter: ","
  encoding: "utf-8"
  dry_run: false
  verbose: true

validation:
  strict: false
  skip_validation: false
```

**Usage**:

```bash
csv-postgres-pipeline --config config.yaml data/file.csv table_name
```

Command-line options override config file values.

---

## Help and Version

### Help Text

```bash
csv-postgres-pipeline --help
```

Output:

```
CSV to Postgres Pipeline - Bulk load CSV files into Postgres tables

Usage: csv-postgres-pipeline [OPTIONS] FILE TABLE
       csv-postgres-pipeline --batch [OPTIONS] DIRECTORY

Options:
  Connection:
    --host TEXT         Database host [required]
    --database TEXT     Database name [required]
    --username TEXT     Database username [required]
    --password TEXT     Database password [required]

  Performance:
    --threads INTEGER   Concurrent workers [default: 4, range: 1-16]

  CSV Format:
    --delimiter TEXT    CSV delimiter [default: ',']
    --encoding TEXT     File encoding [default: 'utf-8']
    --no-header        CSV has no header row

  Validation:
    --dry-run          Validate without loading

  General:
    --verbose, -v      Detailed logging
    --help            Show this message
    --version         Show version

Examples:
  # Load single file
  csv-postgres-pipeline data/customers.csv customers --host localhost ...

  # Batch load directory
  csv-postgres-pipeline --batch data/ --host localhost ...

  # Validate without loading
  csv-postgres-pipeline --dry-run data/file.csv table --host localhost ...
```

### Version

```bash
csv-postgres-pipeline --version
```

Output:

```
csv-postgres-pipeline version 0.1.0
Python 3.13.0
psycopg 3.x.x
```

---

## Contract Tests

The following tests verify CLI contract compliance:

1. **Argument Parsing**
   - Valid arguments accepted
   - Invalid arguments rejected with clear errors
   - Required arguments enforced

2. **Exit Codes**
   - Correct exit code for each failure type
   - Exit code 0 on success

3. **Output Format**
   - Text format matches specification
   - JSON format is valid JSON
   - Progress updates at correct intervals

4. **Error Messages**
   - Clear, actionable error messages
   - Includes file name, line number, column name
   - Suggests fixes when possible

5. **Environment Variables**
   - Correctly read from PG\* environment variables
   - Command-line options override env vars

All contract tests go in `tests/contract/test_cli_interface.py` and must pass before implementation.

---

## Summary

The CLI contract defines:

- ✅ Single-file and batch processing modes
- ✅ Required and optional arguments
- ✅ Output formats (text and JSON)
- ✅ Exit codes (0-5, 130)
- ✅ Progress reporting (interactive and non-interactive)
- ✅ Logging levels and file output
- ✅ Configuration file support
- ✅ Help and version commands

Ready for implementation in `src/csv_postgres_pipeline/cli.py`.
