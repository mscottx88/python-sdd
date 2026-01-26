# Implementation Plan: CSV to Postgres Data Pipeline

**Branch**: `001-csv-postgres-ingest` | **Date**: 2026-01-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-csv-postgres-ingest/spec.md`
**Status**: Phase 6 Complete (CLI Implementation) - 146/146 tasks (100% of Phases 1-6 core features), Phase 7 (Polish) pending

## Specification Clarifications (Session 2026-01-20)

The following design decisions were clarified during specification review:

1. **Empty CSV files (0 data rows)**: Complete successfully with 0 records loaded, log warning, maintain transaction consistency
2. **Missing target table**: Default behavior is fail with clear error. Optional `--create-table` flag enables auto-creation with TEXT columns (safe default)
3. **Column name matching**: Default is strict case-sensitive exact match. Configuration flags enable:
   - `--case-insensitive`: Case-insensitive column matching
   - `--allow-subset`: CSV can have fewer columns (use table defaults/nulls)
   - `--ignore-extra`: Ignore unmapped CSV columns
4. **Logging format**: Structured JSON logs to stderr (machine-parseable, supports log aggregation)
5. **Credential handling**: Support multiple methods - environment variables (preferred), connection string, or config file

These clarifications impact:

- Models: Add PipelineConfig fields for matching modes and table creation
- Validator: Implement configurable column matching policies
- Loader: Add empty CSV handling with warning
- Database: Add table creation capability (opt-in)
- Reporter: Implement JSON structured logging to stderr
- CLI: Add configuration flags for new features

## Summary

Build a high-performance data pipeline that loads CSV files into Postgres tables using bulk operations and concurrent processing. The pipeline validates CSV structure with configurable column matching policies, optionally creates missing tables, processes files in parallel using threading, and provides comprehensive error handling with transactional integrity. Core functionality includes single-file ingestion (P1), batch processing (P2), and production-grade error recovery (P3). Structured JSON logging to stderr enables observability and log aggregation.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: psycopg3 (Postgres driver with native COPY support), Python standard library (csv, concurrent.futures, pathlib)
**Storage**: PostgreSQL (version 12+, tables pre-created)
**Testing**: pytest (unit, integration, contract tests), pytest-mock for test isolation
**Target Platform**: Linux/Windows/macOS (cross-platform CLI tool)
**Project Type**: Single project (library + CLI)
**Performance Goals**: Load 100MB/1M rows in <30s, 3-4x speedup with 4 threads, handle 5GB files without memory issues
**Constraints**: <200MB memory per file stream, atomic transactions per file, zero partial loads on failure
**Scale/Scope**: Batch processing up to 100 files concurrently, 4-16 configurable worker threads, support files up to 5GB

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

### ✅ I. Specification-First Development

- [x] Complete specification exists ([spec.md](spec.md))
- [x] User scenarios with acceptance criteria defined (3 prioritized stories)
- [x] Functional requirements enumerated (FR-001 through FR-020)
- [x] Edge cases identified (10 edge cases documented)
- [x] Key entities documented (5 entities)

### ✅ II. Test-Driven Development (NON-NEGOTIABLE)

- [x] Acceptance scenarios testable (Given/When/Then format)
- [x] Test structure planned (contract/integration/unit)
- [x] Tests written FIRST (Phase 3 US1 complete: 75 tests, 100% pass rate)
- [x] Tests fail before implementation (verified during Phase 3)
- [x] Red-Green-Refactor cycle enforced (followed during Phase 3 implementation)

**GATE REQUIREMENT**: All integration and contract tests for MVP (US1) MUST be written and approved before starting Phase 2 implementation tasks. This is a BLOCKING gate per constitution Principle II (NON-NEGOTIABLE).

**STATUS**: ✅ COMPLETED - Phase 3 (US1 MVP) delivered with 68 passing tests (23 model, 6 contract, 6 integration, 17 validator, 7 loader, 8 database, 7 RFC4180). Phase 6 added 10 CLI contract tests (all passing).

### ✅ III. Independent User Stories

- [x] Stories prioritized by value (P1: Single file, P2: Batch, P3: Error handling)
- [x] Each story independently testable (verified in spec)
- [x] Each story incrementally deliverable (P1 is standalone MVP)
- [x] Stories organized by user journey (data engineer workflows, not technical layers)

### ✅ IV. Quality Gates

- [x] Phase 0: Specification complete ✓, Constitution verified ✓
- [x] Phase 1: Plan documented ✓, Data models ✓, Contracts ✓, Re-check constitution ✓
- [x] Phase 2: All linting passes (ruff) ✓, Type checking (mypy) ✓, Tests pass (pytest) ✓
- [x] Phase 3 US1: MVP delivered with 100% test pass rate ✓, All acceptance scenarios validated ✓

### ✅ V. Code Quality Standards

- [x] Will use ruff for linting (E, W, F, I, N, UP, B, C4, SIM, S rules)
- [x] Will use mypy for type checking (strict mode)
- [x] Will use pytest for testing
- [x] Will follow ruff format (90-char line length)
- [x] Will use Conventional Commits
- [x] Pre-commit hooks will be configured

**Gate Status**: ✅ PASSED - Ready to proceed to Phase 0 research

## Project Structure

### Documentation (this feature)

```text
specs/001-csv-postgres-ingest/
├── spec.md              # Feature specification
├── plan.md              # This file - Implementation plan
├── research.md          # Phase 0 - psycopg3 COPY patterns, ThreadPoolExecutor
├── data-model.md        # Phase 1 - Entity definitions and relationships
├── quickstart.md        # Phase 1 - Usage examples and CLI reference
├── contracts/           # Phase 1 - CLI interface specifications
│   └── cli.md           # Command-line interface contract
└── checklists/
    └── requirements.md  # Specification validation checklist
```

### Source Code (repository root)

```text
src/
├── csv_postgres_pipeline/
│   ├── __init__.py              # Package initialization, version
│   ├── models.py                # Data models (LoadJob, CSVFile, TableSchema, etc.)
│   ├── database.py              # Database connection management, schema validation
│   ├── loader.py                # Core CSV loading logic with psycopg3 COPY
│   ├── validator.py             # CSV structure validation, column matching
│   ├── executor.py              # ThreadPoolExecutor-based concurrent processing
│   ├── reporter.py              # Progress logging and summary statistics
│   ├── cli.py                   # CLI entry point using argparse
│   └── exceptions.py            # Custom exception types
└── __init__.py

tests/
├── contract/
│   ├── test_cli_interface.py    # CLI argument parsing and output format tests
│   └── test_copy_operation.py   # Postgres COPY statement contract tests
├── integration/
│   ├── test_single_file_load.py # User Story 1 integration tests
│   ├── test_batch_processing.py # User Story 2 integration tests
│   ├── test_error_handling.py   # User Story 3 integration tests
│   └── fixtures/                # Test CSV files and database fixtures
│       ├── valid_1000_rows.csv
│       ├── invalid_schema.csv
│       └── malformed.csv
└── unit/
    ├── test_models.py           # Unit tests for data models
    ├── test_validator.py        # CSV validation logic tests
    ├── test_database.py         # Database operations tests (mocked)
    ├── test_loader.py           # Loader logic tests (mocked)
    ├── test_executor.py         # ThreadPoolExecutor wrapper tests
    └── test_reporter.py         # Reporting logic tests
```

**Structure Decision**: Single project layout selected. This is a focused CLI tool/library without frontend or mobile components. The structure follows standard Python packaging with clear separation between core logic (models, database, loader, validator, executor) and interface (CLI). Tests are organized by type (contract, integration, unit) per constitution requirements.

## Complexity Tracking

No constitution violations. Plan adheres to all principles:

- Single project structure (simple, appropriate for CLI tool)
- Clear separation of concerns (models, database, loader, validator, executor, CLI)
- Test-first approach planned
- Independent user stories maintained
- Standard Python tooling (psycopg3, ThreadPoolExecutor from stdlib)

---

## Phase 0: Research & Investigation

**Objective**: Resolve technical unknowns and establish implementation patterns before design.

### Research Topics

1. **psycopg3 COPY Implementation**
   - **Question**: What is the optimal pattern for using psycopg3's COPY FROM STDIN with CSV data?
   - **Why**: psycopg3 has different API than psycopg2; need to understand cursor.copy() with file-like objects
   - **Deliverable**: Code pattern for streaming CSV into COPY, transaction handling, error capture

2. **ThreadPoolExecutor Best Practices for I/O-bound Operations**
   - **Question**: How many threads optimal for database I/O? How to handle thread-local database connections?
   - **Why**: Need to balance concurrency benefits vs connection overhead; avoid connection pool exhaustion
   - **Deliverable**: ThreadPoolExecutor configuration pattern, connection-per-thread strategy

3. **Large CSV Handling Without Memory Issues**
   - **Question**: How to stream 5GB CSV files without loading entire file into memory?
   - **Why**: Success criteria requires handling 5GB files; cannot load entire file
   - **Deliverable**: Chunked reading pattern, memory profiling approach

4. **CSV Column to Table Schema Mapping**
   - **Question**: How to efficiently query Postgres table schema and match CSV headers?
   - **Why**: FR-010 requires validation that CSV columns match table schema before loading
   - **Deliverable**: Schema introspection query pattern using information_schema or pg_catalog

5. **Transaction Isolation for Concurrent Loads to Same Table**
   - **Question**: Can multiple threads safely COPY to same table? What isolation level needed?
   - **Why**: Edge case identified - two threads loading to same table simultaneously
   - **Deliverable**: Postgres isolation level recommendations, potential locking issues

### Research Output

Document findings in `research.md` with format:

```markdown
## Topic: [Research Topic]

**Decision**: [What approach was chosen]
**Rationale**: [Why this approach]
**Alternatives Considered**: [Other options evaluated]
**Code Pattern**: [Example implementation]
```

---

## Phase 1: Design & Contracts

**Prerequisites**: Phase 0 research complete

### 1. Data Model (data-model.md)

Define Pydantic models for key entities from spec:

- **CSVFile**: file_path, size, row_count, column_names, delimiter, encoding, validation_status
- **DatabaseConfig**: See [data-model.md](data-model.md#entity-databaseconfig) for complete attribute list including connection pool settings
- **LoadJob**: job_id, source_file, target_table, status, start_time, end_time, records_loaded, error_message
- **TableSchema**: table_name, column_names, column_types, constraints
- **PipelineConfig**: concurrency_level, dry_run, csv_delimiter, csv_encoding, max_file_size, create_table (bool), case_insensitive (bool), allow_subset (bool), ignore_extra (bool), log_format (str)

Include:

- Field types and constraints (using Pydantic Field validators)
- Relationships between entities
- Validation rules (using Pydantic validators)
- State transitions for LoadJob (pending → processing → success/failed)

### 2. CLI Contract (contracts/cli.md)

Define command-line interface:

**Command Structure**:

```bash
csv-postgres-pipeline [OPTIONS] SOURCE TARGET_TABLE
csv-postgres-pipeline [OPTIONS] --batch DIRECTORY
```

**Arguments**:

- `SOURCE`: CSV file path or directory (with --batch)
- `TARGET_TABLE`: Postgres table name (or table mapping file for --batch)

**Required Options**:

- `--host`: Database host
- `--port`: Database port (default: 5432)
- `--database`: Database name
- `--username`: Database username
- `--password`: Database password (or env var PGPASSWORD)

**Optional Flags**:

- `--threads`: Concurrency level (default: 4, max: 16)
- `--dry-run`: Validate without loading
- `--delimiter`: CSV delimiter (default: ',')
- `--encoding`: CSV encoding (default: 'utf-8')
- `--create-table`: Auto-create missing tables (TEXT columns)
- `--case-insensitive`: Case-insensitive column matching
- `--allow-subset`: Allow CSV with fewer columns than table
- `--ignore-extra`: Ignore unmapped CSV columns
- `--verbose`: Detailed logging

**Output Format**:

- Structured JSON to stderr: `{"level": "INFO", "timestamp": "2026-01-20T10:30:45Z", "message": "Processing file.csv", "records": 1000}`
- Summary JSON: `{"level": "INFO", "files_loaded": 10, "total_records": 50000, "errors": 0, "duration_seconds": 45.2}`
- Error JSON: `{"level": "ERROR", "file": "file.csv", "line": 42, "error": "Column type mismatch", "expected": "INTEGER", "got": "abc"}`

### 3. Quickstart Guide (quickstart.md)

Create user-facing documentation:

- Installation instructions (pip install)
- Basic usage examples for all three user stories
- Common scenarios (single file, batch processing, error recovery)
- Configuration via environment variables
- Troubleshooting guide for common errors

---

## Phase 2: Implementation Planning

**Note**: This phase handled by `/speckit.tasks` command - NOT generated by this plan.

The tasks command will generate tasks.md organized by user story:

- Setup phase (project structure, dependencies)
- Foundational phase (core infrastructure all stories depend on)
- User Story 1 tasks (single file loading)
- User Story 2 tasks (batch processing with threading)
- User Story 3 tasks (error handling)

Each task includes TDD workflow: Write test → Verify failure → Implement → Verify pass

---

## Post-Phase 1 Constitution Re-Check

_GATE: Verify Phase 1 design adheres to all constitution principles_

### ✅ I. Specification-First Development

- [x] Design based on complete specification
- [x] Data models map to spec entities (5 entities defined)
- [x] Contracts capture all functional requirements (FR-001 through FR-020)

### ✅ II. Test-Driven Development (NON-NEGOTIABLE)

- [x] Test structure defined (contract/integration/unit directories)
- [x] Test files identified for each module
- [x] Contract tests specified for CLI and COPY operations
- [x] Ready for TDD workflow in Phase 2

### ✅ III. Independent User Stories

- [x] Design preserves story independence
- [x] Each story maps to specific modules/tests
- [x] P1 (single file) implementable without P2/P3
- [x] No technical layer dependencies (all vertical slices)

### ✅ IV. Quality Gates

- [x] Phase 0: Research complete ✓ ([research.md](research.md))
- [x] Phase 1: Plan documented ✓ ([plan.md](plan.md))
- [x] Phase 1: Data models defined ✓ ([data-model.md](data-model.md))
- [x] Phase 1: Contracts specified ✓ ([contracts/cli.md](contracts/cli.md))
- [x] Phase 1: Quickstart created ✓ ([quickstart.md](quickstart.md))
- [x] Phase 1: Constitution re-checked ✓ (this section)

### ✅ V. Code Quality Standards

- [x] Python 3.13 with type hints throughout data models
- [x] Standard library preferred (csv, concurrent.futures, pathlib)
- [x] Minimal dependencies (psycopg3, pytest, pytest-mock)
- [x] Quality tools ready (ruff, mypy, pytest)

**Phase 1 Gate Status**: ✅ PASSED - Design complete and constitution-compliant

---

## Current Implementation Status

Phase 3 (US1 MVP) complete! Achievements:

1. ✅ **Phase 0 Research** - Completed ([research.md](research.md))
2. ✅ **Phase 1 Data Model** - Completed ([data-model.md](data-model.md)) - Pydantic models implemented
3. ✅ **Phase 1 Contracts** - Completed ([contracts/cli.md](contracts/cli.md))
4. ✅ **Phase 1 Quickstart** - Completed ([quickstart.md](quickstart.md))
5. ✅ **Update Agent Context** - Completed (GitHub Copilot context updated)
6. ✅ **Constitution Re-Check** - Completed (all gates passed)
7. ✅ **Phase 3 US1** - Single file ingestion MVP complete with 100% test pass rate
   - Core modules: models.py, database.py, loader.py, validator.py, exceptions.py
   - Test coverage: 75 tests total (68 passing + 7 RFC4180)
   - Acceptance scenarios: All 3 US1 scenarios validated
   - RFC 4180 compliance: Quoted fields, escaped quotes, embedded newlines, CRLF tested

## Next Steps

**Immediate**: Update implementation to incorporate specification clarifications:

- T044: Add PipelineConfig fields for column matching modes and table creation
- T045: Implement configurable column matching in validator.py (case-insensitive, subset, extra columns)
- T046: Add table creation capability in database.py (opt-in with TEXT columns)
- T047: Implement JSON structured logging in reporter.py (to stderr)
- T048: Add credential handling via environment variables/connection string/config file
- T049: Update CLI with new configuration flags
- T050: Add tests for new configuration options

**Future Phases**:

- Phase 4: User Story 2 - Batch processing with ThreadPoolExecutor
- Phase 5: User Story 3 - Enhanced error handling and recovery
- Phase 6: CLI implementation
- Phase 7: Production polish (docs, examples, packaging)
