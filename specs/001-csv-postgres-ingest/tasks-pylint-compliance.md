# Pylint Compliance Tasks

**Target**: Constitution v1.4.0 compliance (10.00/10.00 pylint score)
**Current**: 8.87/10.00 (70 violations)

## Task Grouping by Priority

### Phase 1: Quick Wins (30 minutes)

#### Task 1.1: Fix unnecessary pass statements in exceptions.py

**File**: [src/csv_postgres_pipeline/exceptions.py](../../../src/csv_postgres_pipeline/exceptions.py)
**Violations**: 5x W0107
**Lines**: 7, 13, 19, 25, 31
**Fix**: Replace `pass` with docstrings

```python
# Before:
class CSVPipelineError(Exception):
    """Base exception for CSV pipeline errors."""
    pass

# After:
class CSVPipelineError(Exception):
    """Base exception for CSV pipeline errors."""
```

#### Task 1.2: Remove unused imports

**Files**:

- [cli.py:15](../../../src/csv_postgres_pipeline/cli.py#L15) - Remove unused `reporter` import
- [executor.py:6](../../../src/csv_postgres_pipeline/executor.py#L6) - Remove unused `Path` import

**Violations**: 2x W0611

#### Task 1.3: Fix import order in loader.py

**File**: [src/csv_postgres_pipeline/loader.py](../../../src/csv_postgres_pipeline/loader.py#L24)
**Violations**: C0411, C0412, W0404
**Lines**: 24 (import issues)
**Fix**: Move `from psycopg import sql` to line 7 (after psycopg imports), remove reimport at line 24

#### Task 1.4: Fix f-string without interpolation

**File**: [cli.py:345](../../../src/csv_postgres_pipeline/cli.py#L345)
**Violation**: W1309
**Fix**: Remove f-prefix from `f"Final summary:"`

#### Task 1.5: Fix line length issues

**Files**:

- [database.py:151](../../../src/csv_postgres_pipeline/database.py#L151) - 101 chars
- [loader.py:240](../../../src/csv_postgres_pipeline/loader.py#L240) - 105 chars
- [models.py:101](../../../src/csv_postgres_pipeline/models.py#L101) - 118 chars
- [models.py:250](../../../src/csv_postgres_pipeline/models.py#L250) - 102 chars
- [validator.py:84](../../../src/csv_postgres_pipeline/validator.py#L84) - 104 chars

**Violations**: 5x C0301
**Fix**: Break lines at 100 characters using proper Python continuation

### Phase 2: Logging Format (30 minutes)

#### Task 2.1: Convert f-string logging in cli.py to lazy %

**File**: [src/csv_postgres_pipeline/cli.py](../../../src/csv_postgres_pipeline/cli.py)
**Violations**: 27x W1203
**Lines**: 89, 92, 95, 98, 160, 164, 167, 178, 181, 191, 212, 224, 229, 257, 261, 267, 270, 284, 286, 290, 295, 299, 345, 346, 347, 348, 349, 350, 353, 358

**Pattern**:

```python
# Before:
logging.info(f"Processing file: {file_path}")

# After:
logging.info("Processing file: %s", file_path)
```

### Phase 3: Code Structure (20 minutes)

#### Task 3.1: Remove unnecessary else after return

**Files**:

- [cli.py:83](../../../src/csv_postgres_pipeline/cli.py#L83) - in `main()`
- [cli.py:289](../../../src/csv_postgres_pipeline/cli.py#L289) - in `_handle_batch_mode()`
- [cli.py:356](../../../src/csv_postgres_pipeline/cli.py#L356) - in `_handle_batch_mode()`
- [database.py:177](../../../src/csv_postgres_pipeline/database.py#L177) - in `get_table_schema()`
- [executor.py:225](../../../src/csv_postgres_pipeline/executor.py#L225) - in `_process_single_file()`

**Violations**: 5x R1705
**Fix**: Remove `else:` and de-indent code block

#### Task 3.2: Fix exception chaining

**Files**:

- [cli.py:70](../../../src/csv_postgres_pipeline/cli.py#L70) - Use `raise ... from e`
- [validator.py:94](../../../src/csv_postgres_pipeline/validator.py#L94) - Use `raise ... from exc`

**Violations**: 2x W0707
**Fix**: Add explicit `from e` clause

#### Task 3.3: Fix redefined name

**File**: [cli.py:118](../../../src/csv_postgres_pipeline/cli.py#L118)
**Violation**: W0621
**Fix**: Rename parameter `database` to `database_name` or `db_name`

#### Task 3.4: Fix unused argument

**File**: [cli.py:144](../../../src/csv_postgres_pipeline/cli.py#L144)
**Violation**: W0613
**Fix**: Either use `pipeline_config` or prefix with underscore: `_pipeline_config`

#### Task 3.5: Move imports to module toplevel

**Files**:

- [cli.py:197](../../../src/csv_postgres_pipeline/cli.py#L197) - Move `import time` to top
- [cli.py:324](../../../src/csv_postgres_pipeline/cli.py#L324) - Move `import time` to top

**Violations**: 2x C0415
**Fix**: Move both `import time` to module top (after other imports)

### Phase 4: Exception Handling (15 minutes)

#### Task 4.1: Handle broad exception catches

**Files**:

- [cli.py:97](../../../src/csv_postgres_pipeline/cli.py#L97) - in `main()`
- [cli.py:217](../../../src/csv_postgres_pipeline/cli.py#L217) - in `_handle_single_file_mode()`
- [database.py:236](../../../src/csv_postgres_pipeline/database.py#L236) - in `validate_connection()`
- [executor.py:144](../../../src/csv_postgres_pipeline/executor.py#L144) - in `process_batch()`
- [executor.py:242](../../../src/csv_postgres_pipeline/executor.py#L242) - in `_process_single_file()`

**Violations**: 5x W0718
**Options**:

1. Narrow to specific exceptions (e.g., `psycopg.Error`, `OSError`)
2. Add inline suppression with justification: `# pylint: disable=broad-exception-caught  # Reason: ...`

### Phase 5: Complexity Issues (Use Suppressions)

#### Task 5.1: Add suppressions for complexity violations

**Rationale**: These functions handle multiple concerns by design (CLI orchestration, data pipeline). Refactoring would reduce readability.

**Files & Suppressions**:

1. **loader.py:27** - `load_csv_to_table()` function
   - R0914: Too many locals (22/15)
   - R0912: Too many branches (13/12)
   - R0915: Too many statements (68/50)

   ```python
   # pylint: disable=too-many-locals,too-many-branches,too-many-statements
   def load_csv_to_table(...):
       """Load CSV file to PostgreSQL table using COPY.

       Complex pipeline function handling validation, type conversion,
       streaming, and error reporting. Suppressed complexity warnings
       as decomposition would reduce clarity.
       """
   ```

2. **cli.py:239** - `_handle_batch_mode()` function
   - R0914: Too many locals (21/15)
   - R0911: Too many returns (7/6)

   ```python
   # pylint: disable=too-many-locals,too-many-return-statements
   def _handle_batch_mode(...):
       """Handle batch directory processing mode.

       CLI orchestration function with multiple exit paths for validation
       and error handling. Complexity reflects business logic requirements.
       """
   ```

3. **cli.py:141** - `_handle_single_file_mode()` function
   - R0911: Too many returns (7/6)

   ```python
   # pylint: disable=too-many-return-statements
   def _handle_single_file_mode(...):
       """Handle single file processing mode.

       Multiple early returns for validation steps improve readability.
       """
   ```

4. **models.py:266** - `TableSchema.validate_csv_columns()` method
   - R0914: Too many locals (16/15)

   ```python
   # pylint: disable=too-many-locals
   def validate_csv_columns(...):
       """Validate CSV columns against table schema.

       Comprehensive validation requires tracking multiple comparison sets.
       """
   ```

5. **executor.py:40** - `BatchExecutor` class
   - R0903: Too few public methods (1/2)

   ```python
   # pylint: disable=too-few-public-methods
   class BatchExecutor:
       """Executes batch CSV processing operations.

       Single-responsibility class focused on batch orchestration.
       Private methods are implementation details.
       """
   ```

## Execution Plan

### Step 1: Phase 1 - Quick Wins

- Run tasks 1.1-1.5
- Verify: `python -m pylint src/csv_postgres_pipeline/`
- Expected: ~40 violations remaining (logging + structure issues)

### Step 2: Phase 2 - Logging Format

- Run task 2.1 (27 logging conversions)
- Verify: `python -m pylint src/csv_postgres_pipeline/`
- Expected: ~13 violations remaining (structure + exceptions + complexity)

### Step 3: Phase 3 - Code Structure

- Run tasks 3.1-3.5
- Verify: `python -m pylint src/csv_postgres_pipeline/`
- Expected: ~8 violations remaining (exceptions + complexity)

### Step 4: Phase 4 - Exception Handling

- Run task 4.1 (decide: narrow vs suppress)
- Verify: `python -m pylint src/csv_postgres_pipeline/`
- Expected: ~8 violations remaining (complexity only)

### Step 5: Phase 5 - Add Suppressions

- Run task 5.1 (add justified suppressions)
- Verify: `python -m pylint src/csv_postgres_pipeline/`
- Expected: 0 violations, 10.00/10.00 score ✅

### Step 6: Regression Testing

- Run: `python -m mypy src/ tests/ --strict`
- Run: `python -m pytest tests/ -v`
- Verify: No regressions, all tests passing

## Success Metrics

- ✅ Pylint score: 10.00/10.00
- ✅ Violations: 0
- ✅ mypy --strict: 0 errors
- ✅ pytest: 154/154 tests passing
- ✅ Constitution v1.4.0 compliance achieved
