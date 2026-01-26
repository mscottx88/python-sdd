# Test Suite: CSV to Postgres Data Pipeline

## Overview

This test suite follows **Test-Driven Development (TDD)** principles per constitution Principle II (NON-NEGOTIABLE).

**TDD Workflow**:

1. ✅ **Write tests FIRST** - Define expected behavior
2. 🔴 **Red phase** - Run tests, verify they FAIL (no implementation yet)
3. ✅ **Green phase** - Implement until tests PASS
4. ♻️ **Refactor** - Improve code while keeping tests green

## Test Organization

```
tests/
├── conftest.py                    # Shared pytest configuration and fixtures
├── contract/                      # Contract tests for external APIs
│   └── test_copy_operation.py    # psycopg3 COPY API contract tests (T008)
├── integration/                   # End-to-end integration tests
│   ├── test_single_file_load.py  # User Story 1 tests (T023-T027c)
│   ├── test_error_handling.py    # User Story 2 tests (T065-T070)
│   └── fixtures/                  # Test data files
│       ├── valid_1000_rows.csv    # Valid CSV with 1000 rows
│       ├── invalid_schema.csv     # CSV with wrong column names
│       └── empty.csv              # CSV with headers only (0 rows)
└── unit/                          # Unit tests for individual modules
    ├── test_models.py             # Data model tests
    ├── test_validator.py          # Validation logic tests
    ├── test_loader.py             # Loading logic tests (mocked DB)
    └── test_database.py           # Database operations tests
```

## User Story 1 Tests (MVP) - ✅ COMPLETE

**Status**: Tests written, awaiting implementation (RED phase)

### Integration Tests (tests/integration/test_single_file_load.py)

- **T023**: `test_single_file_load_success` - Validates Acceptance Scenario 1
  - Given: valid_1000_rows.csv with 1000 rows
  - When: Pipeline processes the file
  - Then: All 1000 rows inserted into database

- **T024**: `test_csv_validation_pass_and_fail` - Validates file validation
  - Valid CSV passes validation
  - Invalid CSV (wrong schema) fails validation

- **T025**: `test_schema_matching_validation` - Validates Acceptance Scenario 2
  - CSV columns matched to table columns correctly
  - Data mapped to corresponding database columns

- **T027c**: `test_empty_csv_file_handling` - Edge case: empty CSV
  - CSV with 0 data rows (headers only)
  - Should complete successfully with 0 rows loaded

- **Additional**: `test_progress_reporting` - Validates Acceptance Scenario 3
  - Reports record count and processing time
  - Tracks start/end timestamps

- **Additional**: `test_transaction_rollback_on_error` - Validates FR-011
  - Transaction rolled back on error
  - No partial data remains in database

### Contract Tests (tests/contract/test_copy_operation.py)

- **T008**: psycopg3 COPY API validation
  - `test_psycopg3_copy_from_stdin_with_text_stream` - Basic COPY from file-like object
  - `test_psycopg3_copy_with_csv_format` - CSV format with quoted fields
  - `test_psycopg3_copy_with_header` - CSV with header row (FR-007)
  - `test_psycopg3_copy_transaction_rollback` - Transaction rollback (FR-011)
  - `test_psycopg3_copy_handles_large_data_streaming` - Streaming 10K rows
  - `test_psycopg3_copy_error_handling` - Error handling with invalid data

### Test Fixtures (tests/integration/fixtures/)

- **T026**: `valid_1000_rows.csv` - ✅ Created (1000 rows, 5 columns)
- **T027**: `invalid_schema.csv` - ✅ Created (wrong column names)
- **T027b**: `empty.csv` - ✅ Created (headers only, 0 data rows)

## Running Tests

### Prerequisites

1. **Test Database Setup**:

   ```bash
   # Create test database and user
   createdb test_csv_pipeline
   psql -d test_csv_pipeline -c "CREATE USER test_user WITH PASSWORD 'test_password';"
   psql -d test_csv_pipeline -c "GRANT ALL PRIVILEGES ON DATABASE test_csv_pipeline TO test_user;"
   ```

2. **Configure Environment** (optional):
   ```bash
   export TEST_DB_HOST=localhost
   export TEST_DB_PORT=5432
   export TEST_DB_NAME=test_csv_pipeline
   export TEST_DB_USER=test_user
   export TEST_DB_PASSWORD=test_password
   ```

### Run All Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/csv_postgres_pipeline --cov-report=html
```

### Run Specific Test Categories

```bash
# Contract tests only (no DB required for most)
pytest tests/contract/ -v

# Integration tests only (requires test DB)
pytest tests/integration/ -v

# Unit tests only (mocked dependencies)
pytest tests/unit/ -v
```

### Run Specific Test Files

```bash
# User Story 1 integration tests
pytest tests/integration/test_single_file_load.py -v

# psycopg3 contract tests
pytest tests/contract/test_copy_operation.py -v
```

### Run Individual Tests

```bash
# Single test function
pytest tests/integration/test_single_file_load.py::test_single_file_load_success -v
```

## Current Status (TDD Cycle)

### ✅ Phase 1: Tests Written (RED phase expected)

- [x] T008 - Contract test for psycopg3 COPY operation
- [x] T023 - Integration test for single file load success
- [x] T024 - Integration test for CSV validation
- [x] T025 - Integration test for schema matching
- [x] T026 - Test fixture: valid_1000_rows.csv
- [x] T027 - Test fixture: invalid_schema.csv
- [x] T027b - Test fixture: empty.csv
- [x] T027c - Integration test for empty CSV handling

### ⏳ Next: T028 - Run Tests (Expected: RED ❌)

```bash
pytest tests/integration/test_single_file_load.py tests/contract/test_copy_operation.py -v
```

**Expected Result**: All tests FAIL because no implementation exists yet.

This confirms:

1. Tests are properly written
2. They verify real functionality (not no-ops)
3. Ready for GREEN phase (implementation)

### ⏳ After RED Phase: Implementation (Phase 2)

Once tests fail as expected:

- T029-T043: Implement validator, loader, models
- GREEN phase: Make tests pass
- Refactor: Improve code quality while keeping tests green

## Test Dependencies

Tests import from the main package:

```python
from src.csv_postgres_pipeline.loader import load_csv_to_table
from src.csv_postgres_pipeline.models import CSVFile, DatabaseConfig, ValidationStatus
from src.csv_postgres_pipeline.validator import validate_csv_file, validate_csv_schema
from src.csv_postgres_pipeline.database import get_table_schema
```

**Note**: All imports use absolute paths with `src.` prefix per constitution v1.5.0.

## Test Quality Standards

Per constitution Principle V:

- **Coverage Target**: >90% for implemented code
- **Type Hints**: All test functions should have type hints
- **Docstrings**: All test functions have descriptive docstrings
- **Assertions**: Clear assertion messages for debugging
- **Fixtures**: Shared setup via pytest fixtures
- **Isolation**: Each test is independent (no shared state)

## Troubleshooting

### ModuleNotFoundError: No module named 'csv_postgres_pipeline'

**Expected during RED phase**. The package doesn't exist yet.

Solution: Proceed to implementation phase (T029+).

### Database connection errors

Check:

1. PostgreSQL is running
2. Test database exists: `test_csv_pipeline`
3. Test user exists with correct permissions
4. Environment variables set correctly (if not using defaults)

### Test failures during GREEN phase

Good! This means:

1. Tests are running (imports work)
2. Implementation has bugs to fix
3. Keep implementing until tests pass

This is the TDD cycle working correctly.
