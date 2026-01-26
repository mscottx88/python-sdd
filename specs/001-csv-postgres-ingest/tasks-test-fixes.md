# Test Failure Fix Tasks

## Task 1: Fix Pydantic Model Configuration for LoadJob and CSVFile

**Priority**: HIGH
**Estimated Time**: 15 minutes
**Files**: `src/csv_postgres_pipeline/models.py`

### Changes Required

1. **Update CSVFile model_config**:
   - Remove `arbitrary_types_allowed` or keep it only for Path
   - CSVFile should work as standard Pydantic model

2. **Update LoadJob model_config**:
   - Ensure proper nested model handling
   - Move `model_config` before field definitions if needed
   - Consider removing `arbitrary_types_allowed` since CSVFile is a Pydantic model

### Acceptance Criteria

- [ ] LoadJob can be instantiated with CSVFile instance
- [ ] No Pydantic validation errors when creating LoadJob
- [ ] Test: `python -c "from src.csv_postgres_pipeline.models import LoadJob, CSVFile, JobStatus; from pathlib import Path; csv = CSVFile(file_path=Path('README.md')); job = LoadJob(source_file=csv, target_table='test'); print('Success')"`

---

## Task 2: Fix test_csv_validation_pass_and_fail Assertion

**Priority**: MEDIUM
**Estimated Time**: 10 minutes
**Files**: `tests/integration/test_single_file_load.py`

### Changes Required

1. Review the test assertion logic around line that checks validation status
2. Fix the assertion that's comparing equal enum values but still failing
3. Verify the test logic flow

### Acceptance Criteria

- [ ] Test passes without assertion errors
- [ ] Validation status is properly checked
- [ ] Test: `pytest tests/integration/test_single_file_load.py::test_csv_validation_pass_and_fail -v`

---

## Task 3: Add Missing validate_csv_file() Calls

**Priority**: MEDIUM
**Estimated Time**: 10 minutes
**Files**: `tests/integration/test_single_file_load.py`

### Changes Required

1. **test_column_matching_configuration**:
   - Add `validate_csv_file(csv_file)` call before schema validation
   - Ensure CSV is validated before attempting schema validation

2. **Check other tests**:
   - Review all integration tests for similar missing validation calls

### Acceptance Criteria

- [ ] No "CSV file must be validated before schema validation" errors
- [ ] All tests properly validate CSV files before schema operations
- [ ] Test: `pytest tests/integration/test_single_file_load.py::test_column_matching_configuration -v`

---

## Task 4: Fix Error Handling Tests

**Priority**: MEDIUM
**Estimated Time**: 20 minutes
**Files**: `tests/integration/test_error_handling.py`

### Changes Required

1. **test_type_mismatch_error_with_context**:
   - Ensure CSV validation happens before load
   - Fix error message assertion to handle actual error format

2. **test_connection_failure_rollback**:
   - Fix error message assertion
   - Ensure proper error propagation

3. **test_malformed_csv_detection_before_db_ops**:
   - Verify malformed CSV detection logic
   - May already be working - needs verification

4. **test_successful_reprocessing_after_fix**:
   - Add missing validation calls
   - Fix Pydantic validation error

### Acceptance Criteria

- [ ] All error handling tests pass
- [ ] Error messages match expected format
- [ ] Test: `pytest tests/integration/test_error_handling.py -v`

---

## Task 5: Verify All Fixes and Run Full Test Suite

**Priority**: HIGH
**Estimated Time**: 10 minutes
**Files**: All test files

### Verification Steps

1. Clear Python caches: `rm -rf src/**/__pycache__ tests/**/__pycache__ .pytest_cache`
2. Run failing tests individually
3. Run integration test suites
4. Run full test suite
5. Verify no regressions in passing tests

### Acceptance Criteria

- [ ] All previously failing tests now pass
- [ ] No new test failures introduced
- [ ] Full test suite passes: `pytest tests/ -v`
- [ ] Test coverage remains at acceptable levels

---

## Execution Order

1. Task 1 (Pydantic models) - **Fixes root cause**
2. Task 3 (Missing validations) - **Quick wins**
3. Task 2 (Assertion fix) - **Quick win**
4. Task 4 (Error handling) - **Depends on Task 1**
5. Task 5 (Verification) - **Final check**

## Success Metrics

- ✅ 0 failing tests (currently 12)
- ✅ All integration tests pass
- ✅ No Pydantic validation errors
- ✅ Proper error message handling
