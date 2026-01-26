# Constitution v1.5.0 Import Path Compliance Plan

## Amendment Summary

**Version**: 1.4.0 → 1.5.0 (MINOR)
**Date**: 2026-01-21
**Requirement**: All Python imports within the project MUST use absolute paths prefixed with `src.`

## Compliance Analysis

### Violations Found: 32 total

**Source Code (src/)**: 15 violations

- **cli.py**: 2 violations (relative imports using `from .`)
- **database.py**: 2 violations (package-relative imports)
- **executor.py**: 5 violations (package-relative imports)
- **loader.py**: 4 violations (package-relative imports)
- **validator.py**: 2 violations (package-relative imports)

**Test Code (tests/)**: 17 violations

- **tests/unit/test_database.py**: 3 violations
- **tests/unit/test_executor.py**: 2 violations
- **tests/unit/test_loader.py**: 3 violations
- **tests/unit/test_models.py**: 1 violation
- **tests/unit/test_reporter.py**: 1 violation
- **tests/unit/test_rfc4180.py**: 2 violations
- **tests/unit/test_validator.py**: 3 violations
- **tests/integration/test_batch_processing.py**: 2 violations

### Violation Types

1. **Relative imports** (`from .`): 2 occurrences
   - Pattern: `from . import module`
   - Pattern: `from .exceptions import ...`
   - Fix: Replace with `from src.csv_postgres_pipeline.module import ...`

2. **Package-relative imports** (`from csv_postgres_pipeline`): 30 occurrences
   - Pattern: `from csv_postgres_pipeline.module import ...`
   - Fix: Replace with `from src.csv_postgres_pipeline.module import ...`

## Implementation Plan

### Phase 1: Update Source Code (src/)

**Priority**: HIGH - Core production code must be compliant

#### File: cli.py (2 fixes)

- Line 16: `from . import database, executor, loader, models, validator`
  - Replace with 5 separate imports: `from src.csv_postgres_pipeline import database`, etc.
- Line 17: `from .exceptions import (...)`
  - Replace with: `from src.csv_postgres_pipeline.exceptions import (...)`

#### File: database.py (2 fixes)

- Line 9: `from csv_postgres_pipeline.exceptions import DatabaseError`
  - Replace with: `from src.csv_postgres_pipeline.exceptions import DatabaseError`
- Line 10: `from csv_postgres_pipeline.models import (...)`
  - Replace with: `from src.csv_postgres_pipeline.models import (...)`

#### File: executor.py (5 fixes)

- Line 7: `from csv_postgres_pipeline.models import (...)`
- Line 14: `from csv_postgres_pipeline.loader import load_csv_to_table`
- Line 15: `from csv_postgres_pipeline.validator import validate_csv_file, validate_csv_schema`
- Line 16: `from csv_postgres_pipeline.database import get_table_schema`
- Line 17: `from csv_postgres_pipeline.reporter import log_progress, log_error, log_summary`
- Replace all with `from src.csv_postgres_pipeline...`

#### File: loader.py (4 fixes)

- Line 10: `from csv_postgres_pipeline.models import (...)`
- Line 16: `from csv_postgres_pipeline.database import create_connection_pool`
- Line 17: `from csv_postgres_pipeline.exceptions import FileProcessingError`
- Line 18: `from csv_postgres_pipeline.reporter import (...)`
- Replace all with `from src.csv_postgres_pipeline...`

#### File: validator.py (2 fixes)

- Line 6: `from csv_postgres_pipeline.models import (...)`
- Line 12: `from csv_postgres_pipeline.exceptions import ValidationError`
- Replace all with `from src.csv_postgres_pipeline...`

### Phase 2: Update Test Code (tests/)

**Priority**: HIGH - Tests must use same import patterns as production

All 17 test file violations follow the same pattern:

- Replace: `from csv_postgres_pipeline.*`
- With: `from src.csv_postgres_pipeline.*`

**Files to update**:

1. tests/unit/test_database.py (3 imports)
2. tests/unit/test_executor.py (2 imports)
3. tests/unit/test_loader.py (3 imports)
4. tests/unit/test_models.py (1 import)
5. tests/unit/test_reporter.py (1 import)
6. tests/unit/test_rfc4180.py (2 imports)
7. tests/unit/test_validator.py (3 imports)
8. tests/integration/test_batch_processing.py (2 imports)

### Phase 3: Verification

**Quality Gates**:

1. ✅ All imports updated (0 violations remaining)
2. ✅ mypy --strict passes (no import resolution errors)
3. ✅ pylint passes with 10.00/10.00 score
4. ✅ pytest runs successfully (154/154 tests passing)
5. ✅ No runtime import errors in CLI execution

**Verification Commands**:

```bash
# Check for remaining violations
grep -r "^from \." src/
grep -r "^from csv_postgres_pipeline" src/ tests/

# Run quality checks
python -m mypy src/ tests/ --strict
python -m pylint src/csv_postgres_pipeline/
python -m pytest tests/ -v

# Test CLI functionality
python -m src.csv_postgres_pipeline.cli --help
```

## Risk Assessment

**Risk Level**: LOW-MEDIUM

**Potential Issues**:

1. **Import resolution**: Python path configuration may need adjustment
2. **IDE configuration**: May need to update IDE settings for import recognition
3. **Test discovery**: Pytest may need path configuration updates
4. **Entry points**: CLI entry points in pyproject.toml may need updating

**Mitigation**:

- Test incrementally (source code first, then tests)
- Run full test suite after each major file update
- Verify both unit and integration tests work
- Test CLI execution manually
- Check mypy and pylint after each phase

## Implementation Strategy

### Approach: Batch Updates by Module

Rather than file-by-file, update all imports in logical groups:

1. **Group 1**: Source code files (all 5 files in src/csv_postgres_pipeline/)
2. **Group 2**: Unit test files (all 7 files)
3. **Group 3**: Integration test files (1 file)

**Benefits**:

- Fewer intermediate broken states
- Easier to verify each group works together
- Faster overall completion
- Simpler rollback if issues arise

### Execution Order

1. Update all src/ files simultaneously
2. Run mypy + pylint on src/ to verify
3. Update all test files simultaneously
4. Run full test suite to verify
5. Final verification of all quality gates

## Success Criteria

✅ Constitution v1.5.0 compliance: All imports use `from src.csv_postgres_pipeline.*`
✅ Zero relative imports (`from .`)
✅ Zero package-relative imports (`from csv_postgres_pipeline`)
✅ mypy --strict: 0 errors
✅ pylint: 10.00/10.00 score
✅ pytest: 154/154 tests passing
✅ CLI executes without import errors

## Estimated Time

- Phase 1 (Source code updates): 15 minutes
- Phase 2 (Test code updates): 10 minutes
- Phase 3 (Verification): 10 minutes
- **Total**: ~35 minutes
