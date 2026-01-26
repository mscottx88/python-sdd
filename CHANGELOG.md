# Changelog

All notable changes to the CSV to PostgreSQL Data Pipeline will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-22

### Added

#### Core Features

- **Single File Ingestion (US1)**: Load individual CSV files to PostgreSQL tables using the high-performance COPY FROM STDIN protocol
- **Batch Processing (US2)**: Process multiple CSV files concurrently using ThreadPoolExecutor with configurable worker threads (4-16)
- **Error Handling & Recovery (US3)**: Comprehensive error handling with transaction rollback, detailed error messages, and support for reprocessing corrected files

#### Data Validation

- CSV structure validation (header presence, column count consistency)
- Schema validation with flexible column matching policies:
  - Case-insensitive column matching
  - Allow subset of required columns
  - Ignore extra columns not in target table
  - Configurable column matching modes
- Support for RFC 4180 compliant CSV parsing
- Multiple character encoding support (UTF-8, Latin-1, Windows-1252)

#### Database Integration

- PostgreSQL connection pooling (psycopg3) for concurrent operations
- Automatic table schema introspection and validation
- Transactional integrity with atomic operations (all rows or rollback)
- Support for nullable columns and columns with default values
- Streaming data processing for arbitrarily large files

#### CLI Interface

- Command-line tool `csv-postgres-pipeline` with comprehensive options
- Database connection configuration via environment variables or CLI flags
- Batch processing mode for directories
- Dry-run mode for validation without database writes
- JSON structured logging output for log aggregation
- Verbose mode for detailed progress reporting

#### Performance & Scalability

- Streaming CSV processing with constant memory usage
- COPY FROM STDIN protocol for high-throughput bulk loading (400-900k rows/sec)
- Concurrent file processing with ThreadPoolExecutor
- Memory-efficient handling of multi-GB files (<1 MB memory for 500MB file)
- Support for files up to 5GB+ without memory constraints

#### Developer Experience

- Comprehensive type hints with mypy strict mode compliance
- Pydantic data models for configuration validation
- Structured JSON logging for observability
- Detailed docstrings for all public APIs
- Pre-commit hooks for code quality (ruff, mypy, pytest)

### Testing

- 154 total tests with 82% overall coverage
- Core business logic: 89-100% coverage
- Contract tests for psycopg3 COPY protocol
- Integration tests for all user stories
- Unit tests for all modules
- Performance tests validating throughput and memory usage

### Performance Benchmarks

- **Single file loading**: 447,392 rows/sec (58.61 MB file in 2.08s)
- **Large file handling**: 500MB file loaded with 0.10 MB memory usage
- **Concurrent processing**: Functional concurrent execution with isolated error handling

### Documentation

- Comprehensive README with installation and usage instructions
- API documentation via docstrings
- Acceptance scenarios validated via integration tests
- Configuration examples for all use cases

### Technical Specifications

- **Python**: 3.13+
- **Database**: PostgreSQL 12+ (tested with PostgreSQL via pgvector container)
- **Key Dependencies**:
  - psycopg[binary] >= 3.2.0 (PostgreSQL driver)
  - psycopg-pool >= 3.2.0 (connection pooling)
  - pydantic >= 2.0.0 (data validation)
- **Development Tools**:
  - pytest >= 9.0.0 (testing framework)
  - mypy >= 1.0.0 (type checking)
  - ruff >= 0.8.0 (linting & formatting)

### Known Limitations

- Concurrent speedup is modest (1.1-1.2x with 4 threads) due to:
  - Extremely fast COPY protocol baseline performance
  - I/O contention on single-disk systems
  - Database write serialization to same table
  - However, concurrent processing is functionally correct and provides isolated error handling
- CLI module has 50% test coverage due to complex error paths (core business logic 89-100%)

### Security

- No hardcoded credentials (environment variables or CLI flags)
- Connection string sanitization in error messages
- Transaction isolation for concurrent loads
- Input validation before database operations

[0.1.0]: https://github.com/nearform/csv-postgres-pipeline/releases/tag/v0.1.0
