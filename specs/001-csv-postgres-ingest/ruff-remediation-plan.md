# Ruff Linting Issues - Remediation Plan

**Date**: January 23, 2026
**Status**: Ready for implementation
**Total Issues**: 7 (4 security warnings, 2 best practice, 1 code quality)

---

## Summary

| File                                             | Issues | Severity   | Estimated Effort |
| ------------------------------------------------ | ------ | ---------- | ---------------- |
| tests/conftest.py                                | 3      | S603, S607 | 15 minutes       |
| tests/performance/test_concurrent_multi_table.py | 2      | B905       | 5 minutes        |
| tests/performance/test_large_file_memory.py      | 1      | B007       | 2 minutes        |
| tests/verify_acceptance_scenarios.py             | 1      | S603       | 5 minutes        |
| **TOTAL**                                        | **7**  | -          | **~27 minutes**  |

---

## Issue Breakdown

### 1. Security: S607 - Partial Executable Paths (3 occurrences)

**Location**: tests/conftest.py:30, 58
**Rule**: Starting a process with a partial executable path
**Risk**: Low (Docker is a well-known system command)

**Issue Details**:

```python
# Line 30
subprocess.run(["docker", "info"], ...)

# Lines 58-65
subprocess.run([
    "docker",
    "ps",
    "--filter",
    f"name={db_container_name}",
    "--format",
    "{{.Status}}",
], ...)
```

**Remediation**: Add `# noqa: S607` comments with justification

**Rationale**:

- Docker is a system-installed executable
- Path is managed by system PATH variable
- This is infrastructure verification code (constitution v1.6.0 requirement)
- Using full paths would reduce portability across Windows/Linux/macOS

---

### 2. Security: S603 - Subprocess Untrusted Input (2 occurrences)

**Location**: tests/conftest.py:57, tests/verify_acceptance_scenarios.py:126
**Rule**: Check for execution of untrusted input
**Risk**: Medium (needs validation)

**Issue Details**:

**tests/conftest.py:57**:

```python
db_container_name = os.getenv("DB_CONTAINER_NAME", "python-sdd-db-1")
result = subprocess.run([
    "docker",
    "ps",
    "--filter",
    f"name={db_container_name}",  # Environment variable in subprocess
    ...
], ...)
```

**tests/verify_acceptance_scenarios.py:126**:

```python
result = subprocess.run(
    cmd, capture_output=True, text=True, cwd=Path.cwd(), env=env
)
```

**Remediation Options**:

**Option A (Recommended)**: Input validation + noqa

- Validate `db_container_name` matches safe pattern (alphanumeric, hyphens, underscores)
- Add `# noqa: S603` with justification for acceptance scenario verification

**Option B**: Suppress with justification only

- Add `# noqa: S603` comments explaining why input is trusted

---

### 3. Best Practice: B905 - Missing strict= in zip() (2 occurrences)

**Location**: tests/performance/test_concurrent_multi_table.py:95, 147
**Rule**: zip() without explicit strict= parameter
**Risk**: Low (could mask bugs if list lengths differ)

**Issue Details**:

```python
# Line 95
for csv_file, table_name in zip(csv_files, table_names):
    setup_table(db_cfg, table_name)
    load_csv_to_table(csv_file, db_cfg, table_name)

# Line 147
for csv_file, table_name in zip(csv_files, table_names)
```

**Remediation**: Add `strict=True` parameter

**Change**:

```python
# Before
for csv_file, table_name in zip(csv_files, table_names):

# After
for csv_file, table_name in zip(csv_files, table_names, strict=True):
```

**Benefits**:

- Raises ValueError if lists have different lengths
- Catches configuration bugs early
- Aligns with Python 3.10+ best practices

---

### 4. Code Quality: B007 - Unused Loop Variable (1 occurrence)

**Location**: tests/performance/test_large_file_memory.py:47
**Rule**: Loop control variable not used within loop body
**Risk**: None (style issue)

**Issue Details**:

```python
for i in range(10000):
    batch_lines.append(
        f"{row_count},{row_count}_name,email{row_count}@example.com,"
        f"{timestamp}\n"
    )
    row_count += 1
```

**Remediation**: Rename `i` to `_` (Python convention for unused variables)

**Change**:

```python
# Before
for i in range(10000):

# After
for _ in range(10000):
```

---

## Implementation Plan

### Phase 1: Critical Security Issues (15 minutes)

**Task 1.1**: Validate subprocess input in conftest.py

- Add validation function for `db_container_name`
- Pattern: `^[a-zA-Z0-9_-]+$`
- Raise clear error if validation fails

**Task 1.2**: Add noqa suppressions with justifications

- conftest.py Docker commands (S607, S603)
- verify_acceptance_scenarios.py (S603)

### Phase 2: Best Practice Improvements (5 minutes)

**Task 2.1**: Add `strict=True` to zip() calls

- test_concurrent_multi_table.py line 95
- test_concurrent_multi_table.py line 147

### Phase 3: Code Quality (2 minutes)

**Task 3.1**: Rename unused loop variable

- test*large_file_memory.py line 47: `i` → `*`

### Phase 4: Verification (5 minutes)

**Task 4.1**: Run linting checks

```bash
uv run ruff check .
```

**Task 4.2**: Run test suite

```bash
uv run pytest tests/ -v
```

**Task 4.3**: Verify pre-commit hooks

```bash
uv run pre-commit run --all-files
```

---

## Code Changes

### File 1: tests/conftest.py

**Line 26** - Add validation function:

```python
def _validate_container_name(name: str) -> None:
    """Validate container name contains only safe characters."""
    import re
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValueError(
            f"Invalid container name '{name}'. "
            "Must contain only alphanumeric characters, hyphens, and underscores."
        )
```

**Line 29-33** - Add noqa for Docker info:

```python
    try:
        result = subprocess.run(
            ["docker", "info"],  # noqa: S607 # Docker is system-installed via PATH
            capture_output=True,
            check=True,
            timeout=5,
        )
```

**Line 55-67** - Validate input and add noqa:

```python
    # Check database container is running
    db_container_name = os.getenv("DB_CONTAINER_NAME", "python-sdd-db-1")
    _validate_container_name(db_container_name)  # Prevent injection attacks

    try:
        result = subprocess.run(  # noqa: S603 # Input validated above
            [
                "docker",  # noqa: S607 # Docker is system-installed via PATH
                "ps",
                "--filter",
                f"name={db_container_name}",
                "--format",
                "{{.Status}}",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
```

### File 2: tests/performance/test_concurrent_multi_table.py

**Line 95**:

```python
for csv_file, table_name in zip(csv_files, table_names, strict=True):
```

**Line 147**:

```python
for csv_file, table_name in zip(csv_files, table_names, strict=True)
```

### File 3: tests/performance/test_large_file_memory.py

**Line 47**:

```python
for _ in range(10000):
```

### File 4: tests/verify_acceptance_scenarios.py

**Line 126**:

```python
    result = subprocess.run(  # noqa: S603 # cmd is constructed internally, not user input
        cmd, capture_output=True, text=True, cwd=Path.cwd(), env=env
    )
```

---

## Expected Outcome

After implementation:

- ✅ 0 ruff errors
- ✅ All tests pass
- ✅ Pre-commit hooks pass
- ✅ Security best practices followed
- ✅ Constitution v1.6.0 compliance maintained

---

## Risk Assessment

| Issue                    | Risk Level | Impact if Not Fixed                                |
| ------------------------ | ---------- | -------------------------------------------------- |
| S607 (Docker path)       | **Low**    | Docker command could fail if PATH misconfigured    |
| S603 (Container name)    | **Medium** | Potential command injection if env var compromised |
| S603 (Acceptance script) | **Low**    | Command constructed internally, no external input  |
| B905 (zip strict)        | **Low**    | Silent bugs if list lengths differ                 |
| B007 (unused var)        | **None**   | Style issue only                                   |

**Recommendation**: Implement all fixes to maintain 100% constitution compliance and security best practices.

---

## Constitution Compliance

This plan maintains compliance with:

- **Principle V**: Code Quality Standards (ruff linting required)
- **Technical Standards**: Security best practices
- **Test Environment**: Infrastructure verification (conftest.py changes support v1.6.0 requirement)

**Note**: The subprocess calls in conftest.py were added specifically to satisfy constitution v1.6.0 test environment verification requirements (lines 242-286). The security suppressions are justified by the controlled nature of the infrastructure verification code.
