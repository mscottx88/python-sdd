# PEP 8 Compliance Remediation Plan

**Constitution Version**: v1.7.0
**Date**: January 23, 2026
**Status**: Ready for implementation
**Current Pylint Score**: 9.70/10 (❌ fails constitution requirement of 10.00/10.00)

---

## Executive Summary

The codebase violates **Constitution v1.7.0 Principle V** which mandates:

- PEP 8 compliance REQUIRED at all times
- ALL imports MUST be at top of file
- Inline imports STRICTLY PROHIBITED
- Pylint score MUST be 10.00/10.00

**Current violations**: 15+ instances of `C0415: Import outside toplevel` across test suite

---

## Violation Analysis

### Pylint C0415: Import Outside Toplevel

| File                                         | Line(s) | Import                                       | Severity | Estimated Fix Time |
| -------------------------------------------- | ------- | -------------------------------------------- | -------- | ------------------ |
| tests/conftest.py                            | 31      | `import re`                                  | HIGH     | 2 min              |
| tests/conftest.py                            | 108     | `from psycopg import connect`                | HIGH     | 2 min              |
| tests/conftest.py                            | 109     | `from psycopg.conninfo import make_conninfo` | HIGH     | 2 min              |
| tests/conftest.py                            | 358     | `import logging`                             | HIGH     | 2 min              |
| tests/contract/test_cli_interface.py         | 134     | `import tempfile`                            | MEDIUM   | 1 min              |
| tests/contract/test_cli_interface.py         | 160     | `import os`                                  | MEDIUM   | 1 min              |
| tests/contract/test_cli_interface.py         | 172     | `import logging`                             | MEDIUM   | 1 min              |
| tests/contract/test_cli_interface.py         | 202     | `import logging`                             | MEDIUM   | 1 min              |
| tests/unit/test_reporter.py                  | 230     | `import sys`                                 | MEDIUM   | 1 min              |
| tests/unit/test_loader.py                    | 293     | `import logging`                             | MEDIUM   | 1 min              |
| tests/unit/test_loader.py                    | 324     | `import logging`                             | MEDIUM   | 1 min              |
| tests/performance/test_100mb_load.py         | 123     | `import os`                                  | LOW      | 1 min              |
| tests/performance/test_concurrent_speedup.py | 206     | `import os`                                  | LOW      | 1 min              |
| tests/performance/test_large_file_memory.py  | 156     | `import threading`                           | LOW      | 1 min              |
| tests/integration/test_single_file_load.py   | 602     | `import json`                                | LOW      | 1 min              |

**Total**: 15 violations, **~20 minutes** to fix

### Additional Pylint Issues (tests/conftest.py)

- **W0621**: Redefining name from outer scope (5 occurrences)
- **W0404**: Reimport 'make_conninfo' (1 occurrence)
- **W0718**: Catching too general exception (1 occurrence)

**Impact**: Reducing score to 8.77/10 for conftest.py alone

---

## Remediation Strategy

### Phase 1: Hoist Inline Imports (Priority: CRITICAL)

**Objective**: Move all inline imports to top-level module scope

**Actions**:

1. **tests/conftest.py** (4 violations → top priority)
   - Move `import re` to line ~7 (after stdlib imports)
   - Move `from psycopg import connect` to line ~16 (already has psycopg imports)
   - Remove redundant `make_conninfo` import (already imported at line 18)
   - Move `import logging` to line ~7

2. **tests/contract/test_cli_interface.py** (4 violations)
   - Move `import tempfile` to top
   - Move `import os` to top
   - Move `import logging` to top (consolidate duplicate imports)

3. **tests/unit/test_reporter.py** (1 violation)
   - Move `import sys` to top

4. **tests/unit/test_loader.py** (2 violations)
   - Move `import logging` to top (consolidate duplicates)

5. **tests/performance/\*.py** (3 violations)
   - Move `import os` to top (test_100mb_load.py, test_concurrent_speedup.py)
   - Move `import threading` to top (test_large_file_memory.py)

6. **tests/integration/test_single_file_load.py** (1 violation)
   - Move `import json` to top

### Phase 2: Fix Redefined Name Warnings (Priority: HIGH)

**W0621 violations in tests/conftest.py**:

Lines 109, 200, 251, 299 redefine fixtures `db_config` and `test_table_name` from outer scope.

**Root cause**: Fixture parameters shadow other fixture names

**Solution**: Rename fixture parameters or use different names in nested scopes

**Example fix**:

```python
# Before (line 200)
def create_test_table(db_config: dict[str, Any], test_table_name: str) -> Generator[str]:

# After
def create_test_table(db_cfg: dict[str, Any], table_name: str) -> Generator[str]:
```

### Phase 3: Fix Reimport Warning (Priority: MEDIUM)

**W0404**: Line 109 reimports `make_conninfo` (already imported line 18)

**Solution**: Remove inline import, use existing top-level import

### Phase 4: Fix Broad Exception Handling (Priority: LOW)

**W0718**: Line 121 catches too general exception `Exception`

**Solution**: Catch specific exceptions (e.g., `psycopg.OperationalError`, `ConnectionError`)

---

## Implementation Plan

### Step 1: Create Branch

```bash
git checkout -b pep8-compliance-fixes
```

### Step 2: Fix High-Priority File (tests/conftest.py)

**Action 2.1**: Hoist imports to top-level

```python
# Add after existing imports (around line 7-8)
import logging
import re
from psycopg import connect
```

**Action 2.2**: Remove inline imports

- Line 31: Delete `import re`
- Line 108-109: Delete `from psycopg import connect` and redundant `make_conninfo`
- Line 358: Delete `import logging`

**Action 2.3**: Rename shadowed fixture parameters

```python
# Lines 200, 251, 299 - rename parameters to avoid shadowing
@pytest.fixture
def create_test_table(db_cfg: dict[str, Any], table_name: str) -> Generator[str]:
    # Update all references inside function from db_config → db_cfg
```

**Action 2.4**: Fix broad exception handling

```python
# Line 121 - replace Exception with specific types
except (psycopg.OperationalError, ConnectionError, OSError) as e:
```

### Step 3: Fix Remaining Files

**For each file with inline imports**:

1. Identify all inline imports with grep
2. Move to top-level after module docstring
3. Ensure proper import grouping (stdlib, third-party, local)
4. Remove inline import statements
5. Verify no side effects from early import

### Step 4: Verification

**Run pylint**:

```bash
uv run pylint src/ tests/ --score=y
# Expected: Your code has been rated at 10.00/10
```

**Run ruff**:

```bash
uv run ruff check .
# Expected: All checks passed!
```

**Run tests**:

```bash
uv run pytest tests/ -v
# Expected: All tests pass
```

**Run pre-commit hooks**:

```bash
uv run pre-commit run --all-files
# Expected: All hooks pass
```

### Step 5: Documentation

Update CHANGELOG.md:

```markdown
## [Unreleased]

### Fixed

- **PEP 8 Compliance**: Moved all inline imports to top-level (Constitution v1.7.0)
- **Pylint Score**: Restored 10.00/10.00 score (was 9.70/10)
- Fixed C0415 violations (import-outside-toplevel) across 15 files
- Fixed W0621 violations (redefined-outer-name) in conftest.py
- Fixed W0404 violation (reimported) in conftest.py
- Fixed W0718 violation (broad-exception-caught) in conftest.py
```

### Step 6: Commit and PR

```bash
git add .
git commit -m "fix(quality): enforce PEP 8 compliance with top-level imports

BREAKING CHANGE: Constitution v1.7.0 now requires strict PEP 8 compliance

- Hoisted all inline imports to top-level across 15 files
- Fixed pylint C0415 (import-outside-toplevel) violations
- Fixed conftest.py shadowing warnings (W0621)
- Fixed reimport warning (W0404)
- Improved exception handling specificity (W0718)
- Restored pylint score to 10.00/10.00 (was 9.70/10)

Closes constitution-v1.7.0-compliance"

git push origin pep8-compliance-fixes
```

---

## Detailed File Changes

### tests/conftest.py

**Current top-level imports** (lines 7-18):

```python
import os
import subprocess
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool
```

**Add to top-level** (after line 11, before pytest):

```python
import logging
import re
from psycopg import connect
```

**Remove inline imports**:

- Line 31: `import re` → DELETE
- Line 108: `from psycopg import connect` → DELETE
- Line 109: `from psycopg.conninfo import make_conninfo` → DELETE (already imported)
- Line 358: `import logging` → DELETE

**Fix shadowing** (lines 200, 251, 299):

```python
# Change signature
def create_test_table(db_cfg: dict[str, Any], table_name: str) -> Generator[str]:
    """..."""
    # Update function body references
    conninfo = make_conninfo(**db_cfg)  # was db_config
    # ... update all db_config → db_cfg, test_table_name → table_name
```

**Fix exception handling** (line 121):

```python
# Before
except Exception as e:

# After
except (psycopg.OperationalError, ConnectionError, OSError) as e:
```

### tests/contract/test_cli_interface.py

**Add to top-level** (after line 8):

```python
import logging
import os
import tempfile
```

**Remove inline imports**:

- Line 134: `import tempfile` → DELETE
- Line 160: `import os` → DELETE
- Line 172: `import logging` → DELETE
- Line 202: `import logging` → DELETE

### tests/unit/test_reporter.py

**Add to top-level**:

```python
import sys
```

**Remove inline**:

- Line 230: `import sys` → DELETE

### tests/unit/test_loader.py

**Add to top-level**:

```python
import logging
```

**Remove inline**:

- Lines 293, 324: `import logging` → DELETE (both)

### tests/performance/test_100mb_load.py

**Add to top-level**:

```python
import os
```

**Remove inline**:

- Line 123: `import os` → DELETE

### tests/performance/test_concurrent_speedup.py

**Add to top-level**:

```python
import os
```

**Remove inline**:

- Line 206: `import os` → DELETE

### tests/performance/test_large_file_memory.py

**Add to top-level**:

```python
import threading
```

**Remove inline**:

- Line 156: `import threading` → DELETE

### tests/integration/test_single_file_load.py

**Add to top-level**:

```python
import json
```

**Remove inline**:

- Line 602: `import json` → DELETE

---

## Risk Assessment

| Risk                               | Likelihood | Impact                          | Mitigation                                                       |
| ---------------------------------- | ---------- | ------------------------------- | ---------------------------------------------------------------- |
| Import side effects at module load | LOW        | Tests fail at import time       | All imports are stdlib/well-known libraries with no side effects |
| Circular import issues             | VERY LOW   | Import errors                   | Project uses proper layering with src.\* prefix                  |
| Test isolation broken              | LOW        | Tests interfere with each other | Imports don't create shared state                                |
| Performance regression             | NEGLIGIBLE | Slower startup                  | Python caches imports; effect unmeasurable                       |

---

## Success Criteria

- ✅ Pylint score: 10.00/10.00 for all files
- ✅ Zero C0415 violations
- ✅ Zero W0621, W0404, W0718 violations
- ✅ All 154+ tests passing
- ✅ Ruff checks pass
- ✅ Pre-commit hooks pass
- ✅ Constitution v1.7.0 compliance achieved

---

## Timeline

**Total estimated effort**: ~45 minutes

- Phase 1 (Hoist imports): 20 minutes
- Phase 2 (Fix shadowing): 10 minutes
- Phase 3 (Fix other warnings): 5 minutes
- Phase 4 (Verification): 5 minutes
- Phase 5 (Documentation): 5 minutes

**Recommended execution**: Single focused session to maintain context and avoid partial compliance state.

---

## Constitution Compliance Statement

This remediation plan addresses Constitution v1.7.0 requirements:

> **Principle V - Code Quality Standards**:
> "PEP 8 compliance REQUIRED at all times"
> "ALL imports MUST be at the top of the file"
> "Inline imports STRICTLY PROHIBITED"
> "Pylint score MUST be 10.00/10.00"

Upon completion, the codebase will be fully compliant with all constitutional requirements.
