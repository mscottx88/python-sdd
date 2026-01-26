# Feature Removal: Batch/Concurrent Processing

**Date**: January 23, 2026
**Version**: 0.2.0

## Summary

Removed batch/concurrent processing feature from the CSV to PostgreSQL data pipeline due to marginal performance benefits (1.1-1.2x speedup) that do not justify the added complexity.

## Rationale

Performance testing (T117) revealed:

- Only 10-20% speedup vs sequential processing (target was 3-4x)
- PostgreSQL COPY protocol already extremely fast (400-900k rows/sec)
- I/O bound at database level, parallelism provides minimal benefit
- ~1000 lines of code (production + tests + docs) for marginal gain

## Changes Made

### Production Code Removed

- `src/csv_postgres_pipeline/executor.py` (BatchExecutor, BatchResult) - **DELETED**
- `src/csv_postgres_pipeline/cli.py`:
  - Removed `_handle_batch_mode()` function
  - Removed `--batch` flag
  - Removed `--threads` flag
  - Removed executor module import
- `src/csv_postgres_pipeline/models.py`:
  - Removed `max_workers` field from PipelineConfig

### Tests Removed

- `tests/integration/test_batch_processing.py` - **DELETED**
- `tests/performance/test_concurrent_speedup.py` - **DELETED**
- `tests/unit/test_executor.py` - **DELETED**
- `tests/integration/fixtures/batch/` directory - **DELETED**
- `tests/conftest.py`:
  - Removed `create_batch_test_table` fixture
  - Removed `batch_fixtures_dir` fixture

### Documentation Updated

- `specs/001-csv-postgres-ingest/spec.md`:
  - Removed User Story 2 (Batch Processing Multiple Files)
  - Removed FR-006, FR-008, FR-018 (concurrent processing requirements)
  - Removed SC-002, SC-007, SC-009 (concurrent success criteria)
  - Removed "Concurrent operations on same table" edge case
  - Renumbered User Story 3 → User Story 2
  - Renumbered all FR requirements and SC criteria

- `README.md`:
  - Removed `--batch` and `--threads` documentation
  - Removed batch processing examples

- `tests/README.md`:
  - Updated test organization structure

- `tests/verify_acceptance_scenarios.py`:
  - Removed User Story 2 batch processing scenarios
  - Renumbered US3 → US2

## Core Functionality Retained

The following P1 features remain fully functional:

- Single CSV file ingestion with high performance
- RFC 4180 CSV compliance
- Transactional safety with rollback
- Flexible column matching (case-insensitive, subset, extra columns)
- Automatic table creation
- Comprehensive error handling and validation
- Dry-run mode
- Multiple encodings support

## Migration Guide

Users who were using batch processing can:

1. Use shell scripts to process multiple files sequentially
2. Use parallel command-line tools (GNU parallel, xargs)
3. Implement custom batch processing in their application code

Example sequential processing:

```bash
for file in data/*.csv; do
  csv-postgres-pipeline "$file" target_table
done
```

Example with GNU parallel:

```bash
find data/ -name "*.csv" | parallel csv-postgres-pipeline {} target_table
```

## Impact

- **Reduced complexity**: ~1000 lines of code removed
- **Simpler CLI**: 2 fewer command-line flags
- **Easier maintenance**: No ThreadPoolExecutor, no connection pool thread-safety concerns
- **Clearer focus**: Core value proposition is fast, reliable single-file ingestion
