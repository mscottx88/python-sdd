"""Performance test: Verify 100MB file loads in <30s.

This test creates a 100MB CSV file and measures load time.
Excludes JIT startup by warming up the connection first.
"""

import os
import time
from pathlib import Path

from psycopg_pool import ConnectionPool

from src.csv_postgres_pipeline.database import create_connection_pool
from src.csv_postgres_pipeline.loader import load_csv_to_table
from src.csv_postgres_pipeline.models import CSVFile, DatabaseConfig
from src.csv_postgres_pipeline.validator import validate_csv_file


def create_100mb_csv(file_path: Path) -> None:
    """Create a ~100MB CSV file for performance testing."""
    print(f"Creating 100MB test file at {file_path}...")

    # Calculate rows needed for ~100MB
    # Each row: id (10 chars) + name (50 chars) + email (30 chars) + value (15 chars)
    # = ~110 bytes per row including delimiters and newline
    # 100MB / 110 bytes ≈ 930,000 rows
    target_rows = 930_000

    with open(file_path, "w", encoding="utf-8") as f:
        # Write header
        f.write("id,name,email,value\n")

        # Write data rows
        for i in range(target_rows):
            f.write(f"{i:010d},Test User {i:010d},user{i}@example.com,{i * 1.5:.2f}\n")

    size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"Created test file: {size_mb:.2f} MB with {target_rows:,} rows")


def test_100mb_file_performance(db_config: dict[str, str | int]) -> None:
    """Test that 100MB file loads in under 30 seconds."""
    perf_dir = Path(__file__).parent
    perf_dir.mkdir(exist_ok=True)
    test_file = perf_dir / "perf_100mb.csv"

    # Create test file if it doesn't exist
    if not test_file.exists():
        create_100mb_csv(test_file)

    # Setup database
    db_cfg = DatabaseConfig(**db_config)  # type: ignore[arg-type]
    table_name = "perf_test_100mb"

    # Create table
    pool: ConnectionPool = create_connection_pool(db_cfg)
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            # Drop if exists
            cur.execute(f"DROP TABLE IF EXISTS {table_name}")

            # Create table
            cur.execute(
                f"""
                CREATE TABLE {table_name} (
                    id TEXT,
                    name TEXT,
                    email TEXT,
                    value TEXT
                )
            """
            )
            conn.commit()

            # Warm up connection (exclude JIT startup from timing)
            cur.execute("SELECT 1")
            conn.commit()
    finally:
        pool.close()

    # Prepare CSV file
    csv_file = CSVFile(file_path=test_file)
    validate_csv_file(csv_file)

    # Performance test - measure load time
    print(f"\nLoading {test_file.stat().st_size / (1024 * 1024):.2f} MB file...")
    start_time = time.time()

    job = load_csv_to_table(csv_file, db_cfg, table_name)

    elapsed = time.time() - start_time

    # Verify results
    print("\nPerformance Test Results:")
    print(f"  File size: {test_file.stat().st_size / (1024 * 1024):.2f} MB")
    print(f"  Rows loaded: {job.records_loaded:,}")
    print(f"  Time taken: {elapsed:.2f} seconds")
    print(f"  Throughput: {job.records_loaded / elapsed:.0f} rows/sec")
    print(f"  MB/sec: {(test_file.stat().st_size / (1024 * 1024)) / elapsed:.2f}")

    # Cleanup
    pool = create_connection_pool(db_cfg)
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()
    finally:
        pool.close()

    # Assert performance target
    assert (
        elapsed < 30.0
    ), f"Performance test failed: 100MB file took {elapsed:.2f}s, expected <30s"
    print(f"\n✓ PASS: 100MB file loaded in {elapsed:.2f}s (target: <30s)")


if __name__ == "__main__":
    # Load config from environment
    db_config = {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("PGDATABASE", "postgres"),
        "username": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", "postgres"),
    }

    test_100mb_file_performance(db_config)  # type: ignore[arg-type]
