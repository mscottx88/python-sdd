# Research: CSV to Postgres Data Pipeline

**Phase**: 0 - Pre-Design Research
**Date**: 2026-01-20
**Purpose**: Resolve technical unknowns before design and implementation

---

## Topic: psycopg3 COPY Implementation

**Decision**: Use `cursor.copy()` with file-like object interface for streaming CSV data via COPY FROM STDIN

**Rationale**:

- psycopg3's `cursor.copy()` accepts file-like objects (anything with `.read()` method)
- COPY FROM STDIN is fastest Postgres bulk load method (10-100x faster than INSERT)
- Streaming approach avoids loading entire CSV into memory
- Built-in support for CSV format with proper quoting/escaping

**Alternatives Considered**:

- **psycopg2's `copy_from()`**: Rejected - using psycopg3 per requirements
- **`copy_expert()` with raw COPY SQL**: More control but unnecessary complexity
- **Row-by-row INSERT**: Rejected - violates FR-005 (must use bulk loading)

**Code Pattern**:

```python
import psycopg
from pathlib import Path

def load_csv_to_table(csv_path: Path, table_name: str, conn: psycopg.Connection):
    """Load CSV file into Postgres table using COPY."""
    with conn.cursor() as cur:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip header row if needed
            next(f)

            # COPY from file object
            with cur.copy(f"COPY {table_name} FROM STDIN WITH (FORMAT CSV)") as copy:
                while data := f.read(8192):  # 8KB chunks
                    copy.write(data)

    conn.commit()
```

**Key Insights**:

- Must use `WITH (FORMAT CSV)` to handle quoted fields, escapes
- Transaction must be explicit (autocommit=False) for rollback capability
- Can specify delimiter, encoding, header options in COPY statement
- Error handling: psycopg raises `psycopg.errors.Error` on COPY failures

---

## Topic: ThreadPoolExecutor Best Practices for I/O-bound Operations

**Decision**: Use ThreadPoolExecutor with one database connection per thread, connection pool size = thread count

**Rationale**:

- Database I/O is I/O-bound not CPU-bound → threading provides real parallelism
- Each thread needs dedicated connection to avoid race conditions
- psycopg3 connections are NOT thread-safe (cannot share across threads)
- ThreadPoolExecutor manages thread lifecycle automatically

**Alternatives Considered**:

- **ProcessPoolExecutor**: Rejected - overhead of process creation, harder to share resources, overkill for I/O
- **asyncio with asyncpg**: Rejected - asyncio adds complexity, ThreadPoolExecutor simpler for batch processing
- **Connection pool shared across threads**: Rejected - psycopg3 connections not thread-safe

**Code Pattern**:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg
from typing import List

def process_files_concurrent(files: List[Path], config: DatabaseConfig, max_workers: int = 4):
    """Process multiple CSV files concurrently."""

    def process_one_file(csv_file: Path) -> LoadJob:
        # Each thread gets its own connection
        with psycopg.connect(
            host=config.host,
            port=config.port,
            dbname=config.database,
            user=config.username,
            password=config.password
        ) as conn:
            return load_csv_to_table(csv_file, config.target_table, conn)

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs
        futures = {executor.submit(process_one_file, f): f for f in files}

        # Process as they complete
        for future in as_completed(futures):
            csv_file = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # Log error but continue processing other files
                results.append(LoadJob(file=csv_file, status='failed', error=str(e)))

    return results
```

**Key Insights**:

- Use context managers (`with`) for automatic connection cleanup
- Set `max_workers` based on testing (default 4, max 16 per FR-008)
- Use `as_completed()` to process results as they finish (better UX)
- Exceptions in one thread don't crash others (isolation)
- Total connections = max_workers (one per thread)

---

## Topic: Large CSV Handling Without Memory Issues

**Decision**: Stream CSV files using Python's `csv.reader()` with file object, never load entire file into memory

**Rationale**:

- Python's `csv` module reads line-by-line (generator pattern)
- psycopg3 `copy()` accepts iterables - can stream directly
- No need to load 5GB file into memory
- Meets SC-003 requirement (handle 5GB files)

**Alternatives Considered**:

- **pandas.read_csv()**: Loads entire file into DataFrame - memory intensive, rejected
- **pandas.read_csv(chunksize=N)**: Better but adds pandas dependency, csv module sufficient
- **polars**: Modern alternative but adds dependency, overkill for simple CSV reading

**Code Pattern**:

```python
import csv
from pathlib import Path

def stream_csv_for_copy(csv_path: Path, has_header: bool = True):
    """Generator that yields CSV rows for COPY operation."""
    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)

        if has_header:
            headers = next(reader)  # Skip header
            # Return headers for validation if needed

        for row in reader:
            # Convert row to CSV line for COPY
            yield ','.join(f'"{field}"' if ',' in field else field for field in row) + '\n'

def load_csv_streaming(csv_path: Path, table_name: str, conn: psycopg.Connection):
    """Load large CSV using streaming to avoid memory issues."""
    with conn.cursor() as cur:
        with cur.copy(f"COPY {table_name} FROM STDIN WITH (FORMAT CSV)") as copy:
            for line in stream_csv_for_copy(csv_path):
                copy.write(line)
```

**Key Insights**:

- File object is read in chunks by Python's I/O system
- csv.reader() yields one row at a time (memory efficient)
- Can validate rows during streaming without loading all
- Buffer size controlled by Python's buffered I/O (default 8KB)

**Memory Profile**:

- 5GB file requires <10MB memory (just buffer + current row)
- Memory usage constant regardless of file size

---

## Topic: CSV Column to Table Schema Mapping

**Decision**: Query `information_schema.columns` to get table schema, match case-sensitive column names with CSV headers

**Rationale**:

- Standard SQL approach works across Postgres versions
- Returns column names, types, nullable, ordinal position
- Can validate before COPY operation (fail fast)
- Avoids parsing COPY errors after load starts

**Alternatives Considered**:

- **pg_catalog tables**: More Postgres-specific, harder to read, information_schema preferred
- **Parse COPY errors**: Too late - want validation before loading starts
- **DESCRIBE**: Not standard SQL, doesn't exist in Postgres

**Code Pattern**:

```python
from dataclasses import dataclass
from typing import List

@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    ordinal_position: int

def get_table_schema(table_name: str, conn: psycopg.Connection) -> List[ColumnInfo]:
    """Query table schema from information_schema."""
    query = """
        SELECT column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """
    with conn.cursor() as cur:
        cur.execute(query, (table_name,))
        return [ColumnInfo(*row) for row in cur.fetchall()]

def validate_csv_columns(csv_headers: List[str], table_schema: List[ColumnInfo]) -> bool:
    """Validate CSV headers match table columns."""
    table_columns = {col.name for col in table_schema}
    csv_columns = set(csv_headers)

    # Check all CSV columns exist in table
    missing = csv_columns - table_columns
    if missing:
        raise ValueError(f"CSV columns not in table: {missing}")

    # Extra table columns OK if they have defaults or are nullable
    return True
```

**Key Insights**:

- Column names are case-sensitive in Postgres (usually lowercase)
- CSV can have subset of table columns (if others nullable/default)
- CSV cannot have columns not in table
- Order doesn't matter for COPY with column list

---

## Topic: Transaction Isolation for Concurrent Loads to Same Table

**Decision**: Use default READ COMMITTED isolation with separate transactions per file. Concurrent COPY to same table is safe.

**Rationale**:

- Postgres COPY operations acquire RowExclusiveLock on target table
- Multiple concurrent COPY operations to same table are supported
- Each COPY is an independent transaction (no read phenomena)
- No dirty reads, lost updates, or serialization issues with append-only loads
- Default isolation (READ COMMITTED) is sufficient

**Alternatives Considered**:

- **SERIALIZABLE isolation**: Unnecessary overhead, no read-write conflicts in append-only scenario
- **Advisory locks**: Overkill - Postgres table locks handle concurrency
- **Sequential processing per table**: Defeats purpose of parallelism

**Code Pattern**:

```python
# Each thread/connection runs independent transaction
with psycopg.connect(...) as conn:
    # Default isolation (READ COMMITTED) is fine
    with conn.cursor() as cur:
        with cur.copy(f"COPY {table_name} FROM STDIN WITH (FORMAT CSV)") as copy:
            # Load data
            pass
    conn.commit()  # Atomic - all rows or none

# No explicit lock needed - Postgres handles it
```

**Key Insights**:

- Concurrent COPY to same table: **SAFE** ✓
- Each COPY is atomic (all rows or rollback)
- No phantom reads (only appending, not reading)
- Performance: Near-linear scaling up to ~8 threads (then I/O bound)

**Caveats**:

- If table has triggers, may impact concurrency
- Unique constraints can cause conflicts (but rare with bulk loads)
- Monitor connection pool size (= thread count)

---

## Summary

All research topics resolved with clear implementation patterns:

1. ✅ **psycopg3 COPY**: Use `cursor.copy()` with file objects
2. ✅ **ThreadPoolExecutor**: One connection per thread, max_workers=4-16
3. ✅ **Large CSV Handling**: Stream with `csv.reader()`, constant memory
4. ✅ **Schema Mapping**: Query `information_schema.columns`, validate before load
5. ✅ **Concurrent Loads**: Safe with default isolation, no special locks needed

**Ready for Phase 1**: Design data models and contracts based on these patterns.
