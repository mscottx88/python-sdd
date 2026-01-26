# Constitution v1.4.0 Pylint Compliance Plan

## Amendment Summary

**Version**: 1.3.1 → 1.4.0 (MINOR)
**Date**: 2026-01-21
**Rationale**: Added pylint as mandatory code quality tool with requirement for perfect 10.00/10.00 score

## Initial Pylint Analysis

**Current Score**: 8.87/10.00
**Target Score**: 10.00/10.00
**Gap**: -1.13 points

**Total Violations**: 70 across 7 files (src/ only)

### Violation Breakdown by Category

**Convention (C)**: ~8 violations

- C0301: Line too long (4 instances)
- C0411: Wrong import order (1 instance)
- C0412: Imports not grouped (1 instance)
- C0415: Import outside toplevel (2 instances)

**Refactor (R)**: ~13 violations

- R0903: Too few public methods (1 instance)
- R0911: Too many return statements (2 instances - 7/6 each)
- R0912: Too many branches (1 instance - 13/12)
- R0914: Too many local variables (3 instances - up to 22/15)
- R0915: Too many statements (1 instance - 68/50)
- R1705: Unnecessary else after return (5 instances)

**Warning (W)**: ~46 violations

- W0107: Unnecessary pass statement (5 instances in exceptions.py)
- W0404: Reimport (1 instance)
- W0611: Unused import (2 instances - reporter, Path)
- W0613: Unused argument (1 instance)
- W0621: Redefining name from outer scope (1 instance)
- W0707: Raise missing from (2 instances)
- W0718: Catching too general exception (4 instances)
- W1203: Logging fstring interpolation (30+ instances)
- W1309: F-string without interpolation (1 instance)

**Error (E)**: 0 violations ✅

**Fatal (F)**: 0 violations ✅

### Files Requiring Fixes

1. **cli.py**: ~48 violations (most critical)
   - 30+ logging f-string issues
   - 4 broad exception catches
   - 2 import issues
   - 3 no-else-return
   - 2 too-many-\* issues
   - 1 unused argument

2. **loader.py**: ~8 violations
   - Import order and grouping issues
   - 3 complexity issues (too-many-\*)
   - 1 line too long

3. **database.py**: ~3 violations
   - 1 line too long
   - 1 no-else-return
   - 1 broad exception

4. **exceptions.py**: 5 violations
   - All unnecessary pass statements

5. **executor.py**: ~4 violations
   - 2 broad exceptions
   - 1 unused import
   - 1 too-few-public-methods

6. **models.py**: ~3 violations
   - 2 lines too long
   - 1 too-many-locals

7. **validator.py**: ~2 violations
   - 1 line too long
   - 1 raise-missing-from

## Implementation Plan

### Priority 1: Quick Wins (Low Effort, High Impact)

**Estimated Time**: 20 minutes

1. **Fix unnecessary pass statements** (exceptions.py) - 5 fixes
   - Replace `pass` with docstrings in exception classes

2. **Fix unused imports** - 2 fixes
   - Remove unused `reporter` import from cli.py
   - Remove unused `Path` import from executor.py

3. **Fix f-string without interpolation** - 1 fix
   - Remove f-prefix from non-interpolated string

4. **Fix import order/grouping** (loader.py) - 2 fixes
   - Move psycopg imports to correct position
   - Group psycopg imports together

### Priority 2: Logging Format (Repetitive, Medium Effort)

**Estimated Time**: 30 minutes

5. **Convert 30+ f-string logging to lazy % formatting** (cli.py)
   - Replace: `logging.info(f"text {var}")`
   - With: `logging.info("text %s", var)`

### Priority 3: Exception Handling (Medium Effort)

**Estimated Time**: 15 minutes

6. **Add explicit exception chaining** - 2 fixes
   - Use `raise ... from e` pattern

7. **Narrow exception catches or add justification** - 4 fixes
   - Replace broad `Exception` with specific types where possible
   - Or add `# pylint: disable=broad-exception-caught` with justification

### Priority 4: Code Structure (Medium Effort)

**Estimated Time**: 20 minutes

8. **Remove unnecessary else after return** - 5 fixes
   - De-indent code after early returns

9. **Fix line length issues** - 4 fixes
   - Break long lines at 100 characters

10. **Fix unused argument** - 1 fix
    - Prefix with underscore or use in function

11. **Fix redefined name** - 1 fix
    - Rename parameter to avoid shadowing import

### Priority 5: Complexity Refactoring (High Effort, Optional)

**Estimated Time**: 60 minutes (can be deferred with suppressions)

12. **Refactor load_csv_to_table function** (loader.py)
    - Too many locals (22/15)
    - Too many branches (13/12)
    - Too many statements (68/50)
    - **Option**: Extract helper functions OR add suppressions with justification

13. **Refactor \_handle_batch_mode function** (cli.py)
    - Too many locals (21/15)
    - Too many returns (7/6)
    - **Option**: Extract helper functions OR add suppressions with justification

14. **Refactor \_handle_single_file_mode function** (cli.py)
    - Too many returns (7/6)
    - **Option**: Consolidate returns OR add suppression

15. **Refactor TableSchema.validates_columns** (models.py)
    - Too many locals (16/15)
    - **Option**: Extract validation helpers OR add suppression

16. **Fix BatchResult class** (executor.py)
    - Too few public methods (1/2)
    - **Option**: Add method OR document as dataclass-like structure with suppression

## Recommended Approach

### Phase 1: Non-Invasive Fixes (Target: 9.5/10.00)

- Priorities 1-4 (all quick fixes that don't change logic)
- Estimated time: ~85 minutes
- Expected violations remaining: ~10 (complexity issues)

### Phase 2: Suppression Strategy (Target: 10.00/10.00)

- Add justified pylint suppressions for genuine complexity
- Add `.pylintrc` configuration
- Document rationale in code comments
- Estimated time: ~15 minutes

### Phase 3 (Optional): Refactoring

- Extract functions to reduce complexity
- Only if time permits and adds value
- Can be deferred to future work

## Risk Assessment

**Risk Level**: LOW

- Most fixes are non-functional (formatting, style)
- Exception handling changes require testing
- Complexity suppressions are legitimate for CLI/pipeline code

**Mitigation**:

- Run mypy after each change
- Run full test suite after completion
- Use suppressions rather than forced refactoring

## Success Criteria

✅ Pylint score: 10.00/10.00
✅ mypy --strict: 0 errors
✅ pytest: 154/154 tests passing
✅ No logical changes to functionality

## Implementation Timeline

**Phase 1**: 85 minutes (non-invasive fixes)
**Phase 2**: 15 minutes (suppressions)
**Total Estimated**: ~100 minutes (1.5-2 hours)
