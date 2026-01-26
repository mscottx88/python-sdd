# Test Failure Analysis & Fix Plan

## Issue Summary

**Total Failures**: 12 tests across 2 integration test files

- `tests/integration/test_single_file_load.py`: 8 failures
- `tests/integration/test_error_handling.py`: 4 failures

## Root Cause Analysis

### Primary Issue: Pydantic v2 Model Validation Error

**Error Pattern**: `pydantic_core._pydantic_core.ValidationError: 1 validation error for LoadJob source_file`

**Root Cause**: The `LoadJob` model has `source_file: CSVFile` but the Pydantic configuration doesn't properly handle nested model validation. Pydantic v2 is stricter about type checking and requires explicit configuration for complex types.

**Affected Tests**: Most failures show this error pattern.

### Secondary Issues

1. **Assertion Failures in Validation Tests**
   - Test: `test_csv_validation_pass_and_fail`
   - Issue: Assertion logic comparing ValidationStatus values incorrectly

2. **Missing CSV Validation Before Schema Validation**
   - Test: `test_column_matching_configuration`
   - Error: `ValidationError: CSV file must be validated before schema validation`
   - Issue: Test not calling `validate_csv_file()` before schema validation

3. **Error Message Format Issues**
   - Tests: `test_type_mismatch_error_with_context`, `test_connection_failure_rollback`
   - Issue: Error messages don't match expected format due to Pydantic validation failing before actual test logic

## Fix Strategy

### Phase 1: Fix Pydantic Model Configuration (Priority: HIGH)

**Fix**: Update `LoadJob` model configuration to properly handle CSVFile nested model

**Options**:

1. Remove `arbitrary_types_allowed` and ensure proper Pydantic model composition
2. Update model_config to use `from_attributes=True` for compatibility
3. Verify CSVFile is properly configured as a Pydantic model

**Implementation**: Modify `src/csv_postgres_pipeline/models.py`

### Phase 2: Fix Test Assertion Logic (Priority: MEDIUM)

**Fix**: Correct assertion in `test_csv_validation_pass_and_fail`

**Issue**: The assertion `assert csv_file.validation_status == ValidationStatus.VALID` is comparing enum values but the error message suggests they're already equal. Need to investigate the actual test logic.

**Implementation**: Modify `tests/integration/test_single_file_load.py`

### Phase 3: Add Missing Validation Calls (Priority: MEDIUM)

**Fix**: Ensure tests call `validate_csv_file()` before schema validation

**Tests to Update**:

- `test_column_matching_configuration`
- Any other tests that perform schema validation

**Implementation**: Modify test setup to include validation step

### Phase 4: Fix Error Message Assertions (Priority: LOW)

**Fix**: Update error message assertions to account for Pydantic validation errors

**Tests to Update**:

- `test_type_mismatch_error_with_context`
- `test_connection_failure_rollback`
- `test_malformed_csv_detection_before_db_ops`
- `test_successful_reprocessing_after_fix`

## Implementation Tasks

### Task 1: Fix LoadJob Model Configuration

**File**: `src/csv_postgres_pipeline/models.py`
**Changes**:

- Update `LoadJob.model_config` to properly handle nested CSVFile model
- Ensure both CSVFile and LoadJob have compatible configurations
- Test that LoadJob can be instantiated with CSVFile instance

### Task 2: Fix CSVFile Model Configuration

**File**: `src/csv_postgres_pipeline/models.py`
**Changes**:

- Verify CSVFile model_config is correct for Pydantic v2
- Ensure `arbitrary_types_allowed` is needed only for Path type
- Add `from_attributes=True` if needed

### Task 3: Fix test_csv_validation_pass_and_fail

**File**: `tests/integration/test_single_file_load.py`
**Changes**:

- Review and fix assertion logic
- Ensure validation status is properly checked

### Task 4: Add validate_csv_file() calls

**File**: `tests/integration/test_single_file_load.py`
**Changes**:

- Add validation call before schema validation in `test_column_matching_configuration`
- Check other tests for similar issues

### Task 5: Update Error Handling Tests

**File**: `tests/integration/test_error_handling.py`
**Changes**:

- Update error message assertions to handle Pydantic validation errors
- Ensure tests properly validate CSV files before load operations
- Fix error message format expectations

## Expected Outcomes

After fixes:

- ✅ All 12 failing tests should pass
- ✅ No Pydantic validation errors for LoadJob instantiation
- ✅ Proper validation flow in all tests
- ✅ Correct error message assertions

## Verification Steps

1. Run failing tests individually to verify fixes
2. Run full integration test suite
3. Run full test suite to ensure no regressions
4. Verify test coverage remains at acceptable levels
