# Quickstart Guide: CSV to Postgres Pipeline

**Version**: 0.1.0
**Date**: 2026-01-20
**Audience**: Data engineers, developers, DevOps

---

## Overview

The CSV to Postgres Pipeline is a high-performance tool for bulk loading CSV files into Postgres tables. It uses Postgres COPY for fast inserts and thread-based parallelism for concurrent processing.

**Key Features**:

- ⚡ Fast bulk loading using Postgres COPY (10-100x faster than row-by-row inserts)
- 🔄 Concurrent processing of multiple files (4-16 configurable workers)
- ✅ Pre-load validation (schema matching, format checking)
- 🔒 Transactional integrity (all rows or none per file)
- 📊 Progress tracking and statistics
- 🛡️ Robust error handling with detailed messages

---

## Installation

### Prerequisites

- Python 3.13 or higher
- PostgreSQL 12 or higher
- Target tables must already exist in database

### Using pip

```bash
pip install csv-postgres-pipeline
```

### Using uv (recommended)

```bash
uv pip install csv-postgres-pipeline
```

### From source

```bash
git clone https://github.com/nearform/python-sdd.git
cd python-sdd
uv pip install -e .
```

### Verify Installation

```bash
csv-postgres-pipeline --version
# Output: csv-postgres-pipeline version 0.1.0
```

---

## Quick Start

### 1. Prepare Your Data

Create a sample CSV file `customers.csv`:

```csv
id,name,email,created_at
1,John Doe,john@example.com,2024-01-01
2,Jane Smith,jane@example.com,2024-01-02
3,Bob Johnson,bob@example.com,2024-01-03
```

### 2. Create Target Table

```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at DATE NOT NULL
);
```

### 3. Load the File

```bash
csv-postgres-pipeline customers.csv customers \
  --host localhost \
  --database mydb \
  --username myuser \
  --password mypassword
```

**Output**:

```
[INFO] Validating customers.csv...
[INFO] Validation passed: 3 rows, 4 columns
[INFO] Loading customers.csv to 'customers' table...
[INFO] Loaded 3 rows in 0.5 seconds (6 rows/sec)
[SUCCESS] File loaded successfully
```

### 4. Verify

```sql
SELECT * FROM customers;
```

---

## Common Usage Patterns

### Single File with Environment Variables

Set database credentials once:

```bash
export PGHOST=localhost
export PGDATABASE=mydb
export PGUSER=myuser
export PGPASSWORD=mypassword

csv-postgres-pipeline data/customers.csv customers
```

### Batch Processing Directory

Load all CSV files in a directory:

```bash
csv-postgres-pipeline --batch data/ \
  --host localhost \
  --database mydb \
  --username myuser \
  --password mypassword
```

The tool uses filename (without extension) as table name:

- `customers.csv` → `customers` table
- `orders.csv` → `orders` table
- `products.csv` → `products` table

### Batch with Custom Table Mapping

Create `mapping.json`:

```json
{
  "customer_data.csv": "customers",
  "order_history.csv": "orders",
  "product_catalog.csv": "products"
}
```

Load with mapping:

```bash
csv-postgres-pipeline --batch data/ --table-map mapping.json \
  --host localhost --database mydb --username myuser --password mypassword
```

### Increase Concurrency

Process files faster with more threads:

```bash
csv-postgres-pipeline --batch data/ --threads 8 \
  --host localhost --database mydb --username myuser --password mypassword
```

**Performance tip**: Optimal thread count depends on:

- Number of CPU cores
- Database connection limit
- Network bandwidth
- Disk I/O capacity

Start with 4 threads, increase to 8-16 if database and network can handle it.

### Dry Run (Validation Only)

Validate files without loading data:

```bash
csv-postgres-pipeline --dry-run customers.csv customers \
  --host localhost --database mydb --username myuser --password mypassword
```

**Output**:

```
[INFO] DRY RUN MODE - No data will be loaded
[INFO] Validating customers.csv...
[INFO] Validation passed: 1000 rows, 5 columns
[INFO] Column mapping verified:
  - id (CSV) → id (INTEGER)
  - name (CSV) → name (TEXT)
  - email (CSV) → email (TEXT)
  - created_at (CSV) → created_at (DATE)
[SUCCESS] Validation complete - file ready to load
```

### Different CSV Format

Handle tab-delimited files:

```bash
csv-postgres-pipeline data.tsv my_table --delimiter '\t' \
  --host localhost --database mydb --username myuser --password mypassword
```

Handle different encoding:

```bash
csv-postgres-pipeline data.csv my_table --encoding 'latin1' \
  --host localhost --database mydb --username myuser --password mypassword
```

### CSV Without Header

If CSV has no header row:

```bash
csv-postgres-pipeline --no-header data.csv my_table \
  --host localhost --database mydb --username myuser --password mypassword
```

**Note**: Column order in CSV must match table definition exactly.

### Verbose Logging

Get detailed progress information:

```bash
csv-postgres-pipeline -v customers.csv customers \
  --host localhost --database mydb --username myuser --password mypassword
```

**Output**:

```
[DEBUG] Connecting to database localhost:5432/mydb
[DEBUG] Querying schema for table 'customers'
[INFO] Table 'customers' has 4 columns: id, name, email, created_at
[DEBUG] Opening file: customers.csv (encoding: utf-8, delimiter: ,)
[INFO] CSV has 4 columns matching table
[INFO] Validating customers.csv...
[DEBUG] Reading CSV header: ['id', 'name', 'email', 'created_at']
[INFO] Validation passed: 1000 rows, 4 columns
[INFO] Loading customers.csv to 'customers' table...
[DEBUG] Executing COPY command with 4 columns
[INFO] Loaded 1000 rows in 2.3 seconds (434 rows/sec)
[SUCCESS] File loaded successfully
```

### JSON Structured Logging

Output logs in JSON format for integration with log aggregation systems:

```bash
csv-postgres-pipeline customers.csv customers \
  --log-format json \
  --host localhost --database mydb --username myuser --password mypassword
```

**Output** (each line is a JSON object):

```json
{"timestamp": "2026-01-21T10:30:00Z", "level": "INFO", "message": "Starting CSV load operation", "context": {"file": "customers.csv", "table": "customers"}}
{"timestamp": "2026-01-21T10:30:01Z", "level": "INFO", "message": "Validation passed", "context": {"rows": 1000, "columns": 4}}
{"timestamp": "2026-01-21T10:30:03Z", "level": "INFO", "message": "Load complete", "context": {"rows_loaded": 1000, "duration_seconds": 2.3}}
```

**Benefits**:

- Easily parsed by log aggregators (Splunk, ELK, CloudWatch)
- Structured context data for filtering and analysis
- Machine-readable for automated monitoring

---

## Phase 3b Features: Flexible Column Matching

### Auto-Create Missing Tables

Automatically create tables from CSV headers (all columns as TEXT):

```bash
csv-postgres-pipeline new_data.csv new_table --create-table \
  --host localhost --database mydb --username myuser --password mypassword
```

**What happens**:

1. Checks if `new_table` exists
2. If not, creates table with TEXT columns from CSV headers
3. Loads the data

**Example**:

- CSV: `id,name,email`
- Creates: `CREATE TABLE new_table (id TEXT, name TEXT, email TEXT)`
- Then loads data

**⚠️ Note**: This is opt-in (disabled by default). Use `--create-table` flag explicitly. All columns created as TEXT for maximum compatibility - refine types later as needed.

### Case-Insensitive Column Matching

Match CSV columns to table columns regardless of case:

```bash
csv-postgres-pipeline messy_export.csv users --case-insensitive \
  --host localhost --database mydb --username myuser --password mypassword
```

**Example**:

- CSV headers: `ID, Name, EMAIL`
- Table columns: `id, name, email`
- Without flag: ❌ Validation fails
- With `--case-insensitive`: ✅ Matches correctly

**Benefit**: Handle CSV files with inconsistent capitalization.

### Allow Subset of Columns

Load CSV with fewer columns than table (uses defaults/nulls for missing):

```bash
csv-postgres-pipeline partial.csv orders --allow-subset \
  --host localhost --database mydb --username myuser --password mypassword
```

**Example**:

- Table: `id, product_id, quantity, created_at, updated_at`
- CSV: `id, product_id, quantity`
- Without flag: ❌ Validation fails (missing columns)
- With `--allow-subset`: ✅ Loads with NULL/defaults for missing columns

**Requirements**:

- Missing columns must be nullable OR have default values
- Required columns must be in CSV

### Ignore Extra Columns

Ignore CSV columns not present in table:

```bash
csv-postgres-pipeline export.csv customers --ignore-extra \
  --host localhost --database mydb --username myuser --password mypassword
```

**Example**:

- Table: `id, name, email`
- CSV: `id, name, email, temp_field, debug_info`
- Without flag: ❌ Validation fails (extra columns)
- With `--ignore-extra`: ✅ Loads only matching columns, ignores others

**Benefit**: Handle CSV exports with extra metadata or debug columns.

### Combining Flags

All matching flags can be combined for maximum flexibility:

```bash
csv-postgres-pipeline messy_data.csv target_table \
  --case-insensitive \
  --allow-subset \
  --ignore-extra \
  --host localhost --database mydb --username myuser --password mypassword
```

**Use case**: Loading third-party CSV exports with:

- Inconsistent capitalization
- Extra columns you don't need
- Missing optional columns

**Example**:

- Table columns: `id, name, email, phone` (phone nullable)
- CSV headers: `ID, Name, EMAIL, TempData, DebugFlag`
- Matches: `ID→id, Name→name, EMAIL→email` (case-insensitive)
- Ignores: `TempData, DebugFlag` (extra columns)
- Fills NULL: `phone` (allow subset)
- ✅ Loads successfully!

### Non-UTF-8 Encodings

Handle CSV files with different character encodings:

```bash
# Latin-1 encoding (common in European exports)
csv-postgres-pipeline data.csv customers --encoding latin-1 \
  --host localhost --database mydb --username myuser --password mypassword

# Windows-1252 encoding (common in Windows exports)
csv-postgres-pipeline data.csv customers --encoding windows-1252 \
  --host localhost --database mydb --username myuser --password mypassword
```

**Supported encodings**:

- `utf-8` (default)
- `latin-1` (ISO-8859-1)
- `windows-1252` (CP-1252)
- Any encoding supported by Python

**When to use**:

- Files from legacy systems
- International data with special characters
- Windows-generated exports

**Example**: CSV with accented characters:

```csv
name,city
José,São Paulo
François,Montréal
```

Loading with wrong encoding produces garbage; use `--encoding latin-1` for correct results.

### Continue on Error (Batch Mode)

Process all files even if some fail:

```bash
csv-postgres-pipeline --batch data/ --continue-on-error \
  --host localhost --database mydb --username myuser --password mypassword
```

**Output**:

```
[INFO] [1/3] Loading customers.csv... ✓ 1000 rows (2.3s)
[ERROR] [2/3] Loading invalid.csv... ✗ Schema mismatch
[INFO] [3/3] Loading products.csv... ✓ 500 rows (1.2s)

Summary:
  Total files: 3
  Successful: 2
  Failed: 1
  Total rows loaded: 1500
```

Exit code: 3 (partial failure)

---

## User Story Examples

### User Story 1: Single File Loading

**Scenario**: Data engineer needs to load a customer data export.

```bash
# 1. Validate the file first
csv-postgres-pipeline --dry-run customer_export.csv customers \
  --host prod-db.company.com --database sales --username etl_user --password $ETL_PASSWORD

# 2. If validation passes, load the file
csv-postgres-pipeline customer_export.csv customers \
  --host prod-db.company.com --database sales --username etl_user --password $ETL_PASSWORD
```

### User Story 2: Batch Processing

**Scenario**: Data engineer receives daily export of 20 CSV files to load.

```bash
# Load all files concurrently with 8 workers
csv-postgres-pipeline --batch /data/daily_export/ --threads 8 \
  --host prod-db.company.com --database warehouse --username etl_user --password $ETL_PASSWORD

# Monitor progress - tool shows:
# - Files processing concurrently
# - Individual file progress
# - Summary statistics
```

### User Story 3: Error Recovery

**Scenario**: One file in a batch failed - fix and reprocess just that file.

```bash
# 1. Initial batch load - one file fails
csv-postgres-pipeline --batch /data/batch/ --continue-on-error \
  --host localhost --database mydb --username myuser --password mypassword

# Output shows orders.csv failed at row 105
# [ERROR] [2/5] Loading orders.csv... ✗ Type mismatch at row 105

# 2. Fix the problematic row in orders.csv

# 3. Reprocess just the fixed file
csv-postgres-pipeline /data/batch/orders.csv orders \
  --host localhost --database mydb --username myuser --password mypassword

# Success! No need to reload other files
```

---

## Configuration File

### Create config.yaml

```yaml
# Database connection
database:
  host: localhost
  port: 5432
  database: mydb
  username: myuser
  password: ${PGPASSWORD} # Read from environment

# Pipeline settings
pipeline:
  threads: 8
  delimiter: ","
  encoding: "utf-8"
  verbose: true

# Validation settings
validation:
  dry_run: false
  strict: false
```

### Use Configuration File

```bash
csv-postgres-pipeline --config config.yaml customers.csv customers
```

**Benefit**: Reuse configuration across multiple runs, commit to version control (without passwords).

---

## Troubleshooting

### Error: Connection refused

```
[ERROR] Database connection failed: Connection refused
```

**Solution**:

- Verify database is running: `pg_isready -h localhost`
- Check host and port are correct
- Verify firewall allows connections
- Check `pg_hba.conf` allows connections from your IP

### Error: Column not found

```
[ERROR] Validation failed: customers.csv
  - Column 'email' not found in table 'customers'
```

**Solution**:

- Check CSV header matches table column names (case-sensitive)
- Verify target table exists: `\d customers` in psql
- If CSV columns differ, create a view or alter CSV headers

### Error: Type mismatch

```
[ERROR] Load failed at row 42: customers.csv
  - Type mismatch in column 'age'
  - Expected: integer
  - Got: 'N/A'
```

**Solution**:

- Fix data in CSV (replace 'N/A' with NULL or valid integer)
- Or change table column to TEXT and handle conversion in application
- Use `--strict` mode to catch these during validation

### Error: Foreign key violation

```
[ERROR] Load failed: orders.csv
  - Foreign key violation: customer_id 999 does not exist
```

**Solution**:

- Load files in correct order (parent tables before child tables)
- Verify referenced data exists
- Temporarily disable foreign key constraints (not recommended)

### Performance: Loading is slow

**Symptoms**: Taking >1 minute per 100K rows

**Solutions**:

1. **Increase threads**: `--threads 8` (if database can handle it)
2. **Drop indexes**: Drop indexes before bulk load, recreate after
3. **Disable triggers**: Disable triggers during load if safe
4. **Tune Postgres**:

   ```sql
   -- Increase work_mem for the session
   SET work_mem = '256MB';

   -- Disable auto-vacuum during load
   SET autovacuum = off;
   ```

5. **Check disk I/O**: Ensure disk isn't bottleneck

---

## Best Practices

### 1. Always Validate First

```bash
# Run dry-run before loading production data
csv-postgres-pipeline --dry-run data.csv table --host prod-db ...
```

### 2. Use Environment Variables for Credentials

```bash
# Never put passwords in command history
export PGPASSWORD=secret

# Use in scripts
csv-postgres-pipeline data.csv table --host $PGHOST ...
```

### 3. Monitor Large Loads

```bash
# Use verbose mode for large files
csv-postgres-pipeline -v large_file.csv table ...

# Or watch logs in another terminal
tail -f /var/log/pipeline.log
```

### 4. Test with Small Sample First

```bash
# Test with first 100 rows
head -101 large_file.csv > sample.csv  # +1 for header
csv-postgres-pipeline sample.csv table ...
```

### 5. Batch Load Order

Load parent tables before child tables to avoid foreign key violations:

```bash
# 1. Load parent tables
csv-postgres-pipeline customers.csv customers ...
csv-postgres-pipeline products.csv products ...

# 2. Load child tables
csv-postgres-pipeline orders.csv orders ...
csv-postgres-pipeline order_items.csv order_items ...
```

---

## Advanced Usage

### Scripting

```bash
#!/bin/bash
set -e  # Exit on error

# Load configuration
export PGHOST=localhost
export PGDATABASE=mydb
export PGUSER=etl_user
export PGPASSWORD=$(cat /secrets/db_password)

# Validate all files first
for csv in data/*.csv; do
  table=$(basename "$csv" .csv)
  echo "Validating $csv..."
  csv-postgres-pipeline --dry-run "$csv" "$table" || exit 1
done

# Load all files
echo "Loading files..."
csv-postgres-pipeline --batch data/ --threads 8 --verbose

echo "Load complete!"
```

### Monitoring

```bash
# Output to JSON for monitoring systems
csv-postgres-pipeline --format json data.csv table > result.json

# Parse with jq
cat result.json | jq '.rows_loaded, .duration_seconds'
```

### Integration with Airflow

```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

dag = DAG('csv_load', start_date=datetime(2024, 1, 1), schedule='@daily')

load_task = BashOperator(
    task_id='load_customers',
    bash_command='csv-postgres-pipeline /data/customers.csv customers --config /config/pipeline.yaml',
    dag=dag
)
```

---

## Getting Help

### Command Help

```bash
csv-postgres-pipeline --help
```

### Report Issues

If you encounter bugs or have feature requests, please open an issue at:
https://github.com/nearform/python-sdd/issues

Include:

- Command used
- Error message
- CSV sample (first 10 rows)
- Postgres version
- Python version

---

## Summary

This guide covered:

- ✅ Installation and verification
- ✅ Single file loading
- ✅ Batch processing
- ✅ Common usage patterns
- ✅ Troubleshooting
- ✅ Best practices
- ✅ Advanced usage

**Next Steps**:

1. Install the tool
2. Try the quick start example
3. Load your own data
4. Read the full documentation for advanced features

For implementation details, see:

- [Implementation Plan](plan.md)
- [Data Model](data-model.md)
- [CLI Contract](contracts/cli.md)
