"""
Memory usage test for extremely large CSV files.

This test verifies that the pipeline can handle very large files (1GB+)
without loading the entire file into memory, using streaming processing.

Test scenario:
- Create a 1GB CSV file (or use existing if present)
- Load the file while monitoring memory usage
- Verify peak memory usage stays below 200MB threshold

This validates:
- Streaming CSV reading (not loading entire file)
- COPY FROM STDIN protocol with streaming
- Constant memory usage regardless of file size

Note: Memory monitoring uses tracemalloc (Python stdlib) to avoid external dependencies.
"""

import os
import threading
import time
import tracemalloc
from pathlib import Path

from src.csv_postgres_pipeline.database import create_connection_pool
from src.csv_postgres_pipeline.loader import load_csv_to_table
from src.csv_postgres_pipeline.models import CSVFile, DatabaseConfig
from src.csv_postgres_pipeline.validator import validate_csv_file


def create_large_test_file(file_path: Path, target_size_gb: float) -> None:
    """Create a large CSV file of approximately target_size_gb GB."""
    print(f"Creating {target_size_gb}GB test file at {file_path}...")
    print("This may take several minutes...")

    target_bytes = int(target_size_gb * 1024 * 1024 * 1024)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("id,name,email,amount,created_at\n")

        row_count = 0
        current_size = f.tell()

        while current_size < target_bytes:
            # Write in batches for performance
            batch_lines = []
            for _ in range(10000):
                batch_lines.append(
                    f"{row_count},{row_count}_name,email{row_count}@example.com,"
                    f"{row_count * 1.5},2024-01-01 12:00:00\n"
                )
                row_count += 1

            f.write("".join(batch_lines))
            current_size = f.tell()

            if row_count % 1_000_000 == 0:
                size_mb = current_size / (1024 * 1024)
                progress = (current_size / target_bytes) * 100
                print(
                    f"  Progress: {progress:.1f}% ({size_mb:.0f} MB, {row_count:,} rows)"
                )

    final_size = file_path.stat().st_size / (1024 * 1024 * 1024)
    print(f"Created file: {final_size:.2f} GB with {row_count:,} rows")


def setup_large_file_table(db_cfg: DatabaseConfig, table_name: str) -> None:
    """Create table for large file test."""
    pool = create_connection_pool(db_cfg)
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            cur.execute(
                f"""
                CREATE TABLE {table_name} (
                    id INTEGER,
                    name TEXT,
                    email TEXT,
                    amount NUMERIC,
                    created_at TIMESTAMP
                )
            """
            )
            conn.commit()
    finally:
        pool.close()


def cleanup_large_file_table(db_cfg: DatabaseConfig, table_name: str) -> None:
    """Drop the test table."""
    pool = create_connection_pool(db_cfg)
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()
    finally:
        pool.close()


def get_memory_usage_mb() -> float:
    """Get current memory usage in MB using tracemalloc."""
    current, _peak = tracemalloc.get_traced_memory()
    return current / (1024 * 1024)


def test_5gb_memory_usage(
    db_config: dict[str, str | int], target_size_gb: float = 1.0
) -> None:
    """Test that loading a 1GB file uses less than 200MB of memory."""
    perf_dir = Path(__file__).parent / "large_file_perf"
    perf_dir.mkdir(parents=True, exist_ok=True)

    test_file = perf_dir / f"large_{int(target_size_gb)}gb.csv"

    # Create or verify test file
    if not test_file.exists():
        create_large_test_file(test_file, target_size_gb)
    else:
        file_size_gb = test_file.stat().st_size / (1024 * 1024 * 1024)
        if file_size_gb < (target_size_gb * 0.9):  # Allow 10% tolerance
            print(f"Existing file too small ({file_size_gb:.2f}GB), recreating...")
            test_file.unlink()
            create_large_test_file(test_file, target_size_gb)
        else:
            print(f"Using existing {file_size_gb:.2f}GB test file")

    # Setup database
    db_cfg = DatabaseConfig(**db_config)  # type: ignore[arg-type]
    table_name = "perf_large_memory_test"

    print("\nSetting up database table...")
    setup_large_file_table(db_cfg, table_name)

    # Prepare CSV file
    print("Validating CSV file...")
    csv_file = CSVFile(file_path=test_file)
    validate_csv_file(csv_file)

    # Start memory tracking
    print("\nStarting memory tracking...")
    tracemalloc.start()

    # Measure baseline memory
    baseline_memory = get_memory_usage_mb()
    print(f"Baseline memory usage: {baseline_memory:.2f} MB")

    # Load file while monitoring memory
    print(f"\nLoading {test_file.stat().st_size / (1024**3):.2f}GB file...")
    print("Monitoring memory usage...")

    peak_memory = baseline_memory
    start_time = time.time()

    # Start loading in background thread to monitor memory
    load_complete = False
    load_error = None

    def load_worker():
        nonlocal load_complete, load_error
        try:
            load_csv_to_table(csv_file, db_cfg, table_name)
            load_complete = True
        except Exception as e:  # pylint: disable=broad-except
            # Catch all exceptions to report them in the main thread
            load_error = e
            load_complete = True

    load_thread = threading.Thread(target=load_worker)
    load_thread.start()

    # Monitor memory while loading
    sample_count = 0
    while not load_complete:
        time.sleep(0.5)  # Sample every 500ms
        current_memory = get_memory_usage_mb()
        peak_memory = max(peak_memory, current_memory)
        sample_count += 1

        if sample_count % 10 == 0:  # Print every 5 seconds
            elapsed = time.time() - start_time
            print(
                f"  {elapsed:.1f}s - Current: {current_memory:.2f} MB, Peak: {peak_memory:.2f} MB"
            )

    load_thread.join()

    if load_error:
        raise load_error

    elapsed_time = time.time() - start_time

    # Get peak memory from tracemalloc
    current_memory, peak_memory_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_memory = peak_memory_bytes / (1024 * 1024)
    memory_increase = peak_memory - baseline_memory

    # Cleanup
    print("\nCleaning up...")
    cleanup_large_file_table(db_cfg, table_name)

    # Report results
    file_size_gb = test_file.stat().st_size / (1024 * 1024 * 1024)
    rows_loaded = csv_file.row_count or 0

    print("\n" + "=" * 60)
    print("MEMORY USAGE TEST RESULTS")
    print("=" * 60)
    print(f"File size: {file_size_gb:.2f} GB")
    print(f"Rows loaded: {rows_loaded:,}")
    print(f"Time taken: {elapsed_time:.2f} seconds")
    print(f"Throughput: {rows_loaded / elapsed_time:.0f} rows/sec")
    print(f"Baseline memory: {baseline_memory:.2f} MB")
    print(f"Peak memory: {peak_memory:.2f} MB")
    print(f"Memory increase: {memory_increase:.2f} MB")
    print("Target: <200 MB memory usage")

    # Verify memory usage
    if memory_increase < 200:
        print(f"\n✓ PASS: Memory usage {memory_increase:.2f} MB (target: <200 MB)")
    else:
        print(f"\n✗ FAIL: Memory usage {memory_increase:.2f} MB exceeds 200 MB target")
        raise AssertionError(
            f"Memory usage {memory_increase:.2f} MB exceeds 200 MB threshold"
        )


if __name__ == "__main__":
    db_config: dict[str, str | int] = {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("PGDATABASE", "postgres"),
        "username": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", "postgres"),
    }

    # Note: Creating a 1GB file takes time. For faster testing, use smaller size.
    # For full validation, use target_size_gb=1.0
    test_5gb_memory_usage(
        db_config,
        target_size_gb=0.5,
    )  # Start with 500MB for quick test
