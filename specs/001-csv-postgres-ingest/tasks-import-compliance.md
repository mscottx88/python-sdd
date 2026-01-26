# Import Path Compliance Tasks

**Target**: Constitution v1.5.0 compliance - Absolute import paths with `src.` prefix
**Current**: 32 violations (15 in src/, 17 in tests/)

## Phase 1: Update Source Code (src/)

### Task 1.1: Update cli.py imports

**File**: src/csv_postgres_pipeline/cli.py
**Violations**: 2 (lines 16-17)

**Changes**:

1. Line 16: Replace `from . import database, executor, loader, models, validator`
   - With separate imports:
     ```python
     from src.csv_postgres_pipeline import database
     from src.csv_postgres_pipeline import executor
     from src.csv_postgres_pipeline import loader
     from src.csv_postgres_pipeline import models
     from src.csv_postgres_pipeline import validator
     ```

2. Line 17: Replace `from .exceptions import (...)`
   - With: `from src.csv_postgres_pipeline.exceptions import (...)`

### Task 1.2: Update database.py imports

**File**: src/csv_postgres_pipeline/database.py
**Violations**: 2 (lines 9-10)

**Changes**:

1. Line 9: `from csv_postgres_pipeline.exceptions` → `from src.csv_postgres_pipeline.exceptions`
2. Line 10: `from csv_postgres_pipeline.models` → `from src.csv_postgres_pipeline.models`

### Task 1.3: Update executor.py imports

**File**: src/csv_postgres_pipeline/executor.py
**Violations**: 5 (lines 7, 14-17)

**Changes**:

1. Line 7: `from csv_postgres_pipeline.models` → `from src.csv_postgres_pipeline.models`
2. Line 14: `from csv_postgres_pipeline.loader` → `from src.csv_postgres_pipeline.loader`
3. Line 15: `from csv_postgres_pipeline.validator` → `from src.csv_postgres_pipeline.validator`
4. Line 16: `from csv_postgres_pipeline.database` → `from src.csv_postgres_pipeline.database`
5. Line 17: `from csv_postgres_pipeline.reporter` → `from src.csv_postgres_pipeline.reporter`

### Task 1.4: Update loader.py imports

**File**: src/csv_postgres_pipeline/loader.py
**Violations**: 4 (lines 10, 16-18)

**Changes**:

1. Line 10: `from csv_postgres_pipeline.models` → `from src.csv_postgres_pipeline.models`
2. Line 16: `from csv_postgres_pipeline.database` → `from src.csv_postgres_pipeline.database`
3. Line 17: `from csv_postgres_pipeline.exceptions` → `from src.csv_postgres_pipeline.exceptions`
4. Line 18: `from csv_postgres_pipeline.reporter` → `from src.csv_postgres_pipeline.reporter`

### Task 1.5: Update validator.py imports

**File**: src/csv_postgres_pipeline/validator.py
**Violations**: 2 (lines 6, 12)

**Changes**:

1. Line 6: `from csv_postgres_pipeline.models` → `from src.csv_postgres_pipeline.models`
2. Line 12: `from csv_postgres_pipeline.exceptions` → `from src.csv_postgres_pipeline.exceptions`

### Task 1.6: Verify source code after Phase 1

**Commands**:

```bash
# Check for remaining violations in src/
grep -r "^from \." src/csv_postgres_pipeline/
grep -r "^from csv_postgres_pipeline" src/csv_postgres_pipeline/

# Run mypy on source
python -m mypy src/ --strict

# Run pylint on source
python -m pylint src/csv_postgres_pipeline/
```

**Expected**: 0 violations in src/, mypy passes, pylint 10.00/10.00

---

## Phase 2: Update Test Code (tests/)

### Task 2.1: Update unit test imports

**Files**: tests/unit/\*.py (7 files)
**Violations**: 15 total

**Pattern**: Replace all `from csv_postgres_pipeline.*` with `from src.csv_postgres_pipeline.*`

**Files to update**:

1. **test_database.py** (3 imports):
   - Line 8: `from csv_postgres_pipeline.database`
   - Line 14: `from csv_postgres_pipeline.models`
   - Line 21: `from csv_postgres_pipeline.exceptions`

2. **test_executor.py** (2 imports):
   - Line 7: `from csv_postgres_pipeline.executor`
   - Line 8: `from csv_postgres_pipeline.models`

3. **test_loader.py** (3 imports):
   - Line 8: `from csv_postgres_pipeline.loader`
   - Line 9: `from csv_postgres_pipeline.models`
   - Line 16: `from csv_postgres_pipeline.exceptions`

4. **test_models.py** (1 import):
   - Line 9: `from csv_postgres_pipeline.models`

5. **test_reporter.py** (1 import):
   - Line 9: `from csv_postgres_pipeline.reporter`

6. **test_rfc4180.py** (2 imports):
   - Line 15: `from csv_postgres_pipeline.validator`
   - Line 16: `from csv_postgres_pipeline.models`

7. **test_validator.py** (3 imports):
   - Line 6: `from csv_postgres_pipeline.validator`
   - Line 7: `from csv_postgres_pipeline.models`
   - Line 14: `from csv_postgres_pipeline.exceptions`

### Task 2.2: Update integration test imports

**Files**: tests/integration/\*.py (1 file)
**Violations**: 2 total

**File: test_batch_processing.py**:

- Line 37: `from csv_postgres_pipeline.models`
- Line 38: `from csv_postgres_pipeline.executor`

### Task 2.3: Verify test code after Phase 2

**Commands**:

```bash
# Check for remaining violations in tests/
grep -r "^from csv_postgres_pipeline" tests/

# Run mypy on tests
python -m mypy tests/ --strict

# Run full test suite
python -m pytest tests/ -v
```

**Expected**: 0 violations in tests/, mypy passes, 154/154 tests passing

---

## Phase 3: Final Verification

### Task 3.1: Comprehensive compliance check

**Commands**:

```bash
# Scan entire codebase for violations
grep -r "^from \." src/ tests/
grep -r "^from csv_postgres_pipeline" src/ tests/

# Run all quality checks
python -m mypy src/ tests/ --strict
python -m pylint src/csv_postgres_pipeline/
python -m pytest tests/ -v --tb=short

# Test CLI execution
python -m src.csv_postgres_pipeline.cli --help
```

**Success Criteria**:

- ✅ 0 grep matches (all violations fixed)
- ✅ mypy: 0 errors in 25 source files
- ✅ pylint: 10.00/10.00 score
- ✅ pytest: 154/154 tests passing
- ✅ CLI executes without import errors

### Task 3.2: Update compliance plan with results

**Action**: Update constitution-v1.5.0-compliance-plan.md with:

- Verification results
- Any issues encountered and resolutions
- Final compliance status

---

## Execution Summary

**Total Files to Update**: 13 files

- Source: 5 files (cli.py, database.py, executor.py, loader.py, validator.py)
- Tests: 8 files (7 unit tests + 1 integration test)

**Total Import Changes**: 32 replacements

- Relative imports (`from .`): 2
- Package-relative imports (`from csv_postgres_pipeline`): 30

**Estimated Duration**: 35 minutes

- Phase 1: 15 minutes
- Phase 2: 10 minutes
- Phase 3: 10 minutes
