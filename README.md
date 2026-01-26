[![Continuous Integration](https://github.com/nearform/pyspark-common-utilities/actions/workflows/ci.yml/badge.svg)](https://github.com/nearform/pyspark-common-utilities/actions/workflows/ci.yml)

# Python-SDD (Spec Driven Development in Python)

Instructions from [github](https://github.com/github/spec-kit).

Install [Claude Code](https://code.claude.com/docs/en/setup).

```powershell
irm https://claude.ai/install.ps1 | iex
```

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# Create new project
specify init <PROJECT_NAME>

# Or initialize in existing project
specify init . --ai claude
# or
specify init --here --ai claude

# Check installed tools
specify check
```

# Python Project Template

Standard Python project template for Nearform projects. Includes linting, type checking, testing, and commit message validation.

## CSV to PostgreSQL Data Pipeline

Fast, reliable CSV ingestion into PostgreSQL using `COPY FROM STDIN` for optimal performance.

### Features

- **High Performance**: Uses PostgreSQL's native COPY protocol for streaming data transfer
- **RFC 4180 Compliant**: Handles quoted fields, embedded newlines, escaped quotes, CRLF/LF line endings
- **Flexible Column Matching**: Case-insensitive, subset, and extra column handling modes
- **Automatic Table Creation**: Optional schema inference from CSV headers (all TEXT columns)
- **Transactional Safety**: Atomic operations with automatic rollback on errors
- **Multiple Encodings**: UTF-8 (default), Latin-1, Windows-1252 supported
- **Dry Run Mode**: Validate without executing changes
- **Structured Logging**: JSON output to stderr for integration with log aggregation systems

### Quick Example

```bash
# Set database credentials (preferred method)
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=mydb
export PGUSER=postgres
export PGPASSWORD=secret

# Load CSV into existing table
csv-postgres-pipeline data.csv customers

# Auto-create table if missing
csv-postgres-pipeline data.csv new_table --create-table

# Case-insensitive column matching
csv-postgres-pipeline data.csv users --case-insensitive

# Allow subset of columns (use table defaults/nulls for missing)
csv-postgres-pipeline data.csv orders --allow-subset

# Dry run validation only
csv-postgres-pipeline data.csv products --dry-run
```

### Configuration Flags

#### Column Matching Options

- `--create-table`: Auto-create missing tables with TEXT columns (opt-in, disabled by default)
- `--case-insensitive`: Match columns regardless of case (e.g., "Name" matches "name")
- `--allow-subset`: Allow CSV with fewer columns than table (uses defaults/nulls for missing columns)
- `--ignore-extra`: Ignore CSV columns not present in table (silently skip unmapped columns)

These flags can be combined for maximum flexibility:

```bash
# Case-insensitive + allow subset + ignore extra columns
csv-postgres-pipeline messy_data.csv target_table \
  --case-insensitive --allow-subset --ignore-extra
```

#### Processing Options

- `--dry-run`: Validate CSV and schema without loading data

#### CSV Format Options

- `--delimiter CHAR`: CSV delimiter (default: comma)
- `--encoding ENC`: File encoding (default: utf-8, also supports: latin-1, windows-1252)

#### Database Connection

Environment variables (preferred for security):

- `PGHOST`: Database host (default: localhost)
- `PGPORT`: Database port (default: 5432)
- `PGDATABASE`: Database name (required)
- `PGUSER`: Username (required)
- `PGPASSWORD`: Password (required)

Or use CLI flags:

```bash
csv-postgres-pipeline data.csv customers \
  --host localhost --port 5432 \
  --database mydb --username postgres
```

### Edge Cases Handled

- **Empty CSV files**: Completes successfully with warning (0 records loaded)
- **Quoted fields with commas**: `"Last, First",Address` parsed correctly
- **Embedded newlines**: Multi-line values in quoted fields preserved
- **Mixed line endings**: CRLF and LF within same file handled transparently
- **Encoding mismatches**: Validation error with clear message

### Testing

```bash
# Run all tests
uv run pytest

# Unit tests only
uv run pytest tests/unit/

# Integration tests (requires PostgreSQL)
docker compose up -d  # Start test database
uv run pytest tests/integration/

# Contract tests (psycopg3 COPY API)
uv run pytest tests/contract/

# Test coverage report
uv run pytest --cov=src/csv_postgres_pipeline --cov-report=html
```

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

## Quick Start

```bash
# Install uv (if needed)
curl -LsSf "https://astral.sh/uv/install.sh" | sh

# Install python version
uv python install 3.13

# Create venv
uv venv .venv --python 3.13

# Activate venv
source .venv/Scripts/activate

# Install dependencies
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

## Configuration

Update `pyproject.toml` with your project details.

## Development Commands

```bash
# Run all checks manually
uv run ruff check .              # Lint
uv run ruff format .             # Format
uv run mypy .                    # Type check
uv run pytest                    # Test
```

## Pre-commit Hooks

- **ruff**: Lints (check only, no auto-fix, only on staged files)
- **ruff-format**: Format validation (check only, no auto-format, only on staged files)
- **mypy**: Type checking (only on staged files)
- **pytest**: Full test suite
- **conventional-pre-commit**: Commit message validation

### Commit workflow

```bash
# 1. Commit triggers pre-commit checks
git commit -m "feat: add new feature"

# 2. If checks fail, fix manually
uv run ruff check --fix .
uv run ruff format .

# 3. Review and stage changes
git diff
git add .

# 4. Commit again
git commit -m "feat: add new feature"
```

## Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

[optional body]
```

**Valid types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

## CI/CD

GitHub Actions runs on every push and PR:

- Linting (ruff)
- Type checking (mypy)
- Tests (pytest)
- Auto-merge for Dependabot PRs (after checks pass)

## Versioning and publishing (Optional)

### Manual Release Workflow

The repository includes a manual release workflow that can be triggered from GitHub Actions.
**Note**: The workflow is configured to release from the `master` branch.

1. Go to **Actions** → **Publish to PyPI**
2. Click **Run workflow**
3. Select version bump type (`patch`, `minor`, or `major`)
4. The workflow will:
   - Bump the version in `pyproject.toml`
   - Create a commit and Git tag
   - Build the package
   - Create a GitHub Release
   - Publish to PyPI (if configured)

### PyPI Publication (Optional)

PyPI publication uses **Trusted Publishing** (OIDC) and is **optional**. If not configured, the package will still be released on GitHub but not published to PyPI.

#### Setup PyPI Trusted Publishing

If you want to publish to PyPI, configure Trusted Publishing:

1. **Create a PyPI account** at https://pypi.org (or https://test.pypi.org for testing)

2. **Go to your PyPI account settings** → **Publishing** → **Add a new pending publisher**

3. **Fill in the form**:
   - **PyPI Project Name**: `your-project-name` (must match `name` in `pyproject.toml`)
   - **Owner**: Your GitHub username or organization
   - **Repository name**: `your-repo-name`
   - **Workflow name**: `release.yml` (or whatever you named your workflow file)
   - **Environment name**: Leave empty (or use `release` if you configure one)

4. **Save** - The publisher will be in "pending" state until the first successful publish

5. **Run the workflow** - On first run, PyPI will activate the trusted publisher

[![banner](https://raw.githubusercontent.com/nearform/.github/refs/heads/master/assets/os-banner-green.svg)](https://www.nearform.com/contact/?utm_source=open-source&utm_medium=banner&utm_campaign=os-project-pages)
