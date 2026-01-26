<!--
  Sync Impact Report - Constitution v1.9.0

  Version Change: 1.8.0 → 1.9.0 (MINOR)

  Rationale: Added Pylance (VS Code Python language server) as mandatory static analysis
  tool alongside mypy, pylint, and ruff. Pylance provides real-time IDE feedback during
  development, catching errors immediately with faster feedback loops. Complements mypy
  by providing better VS Code integration and import resolution checking. Applies equally
  to production and test code per NO DOUBLE STANDARDS policy.

  Modified Principles:
  - Principle V (Code Quality Standards): Added Pylance requirements section with configuration
  - Principle IV (Quality Gates) Phase 2: Added Pylance validation requirement

  Modified Sections:
  - Core Principles > V. Code Quality Standards: Added "Pylance Requirements" and "Pylance Configuration"
  - Core Principles > IV. Quality Gates > Phase 2: Added "Run Pylance analysis" validation step

  Added Sections:
  - Pylance Requirements: Zero errors/warnings policy, type checking mode, integration details
  - Pylance Configuration: VS Code settings for strict analysis with JSON example

  Removed Sections: None

  Templates Requiring Updates:
  ✅ plan-template.md - Should add Pylance validation in quality checks section
  ✅ spec-template.md - No changes needed (content-agnostic)
  ✅ tasks-template.md - Should add Pylance validation tasks
  ✅ commands/*.md - No changes needed (command execution unaffected)

  Follow-up TODOs:
  - Create .vscode/settings.json with Pylance configuration if not present
  - Add Pylance validation to CI/CD pipeline documentation
  - Update plan-template.md to include Pylance checks
  - Update tasks-template.md to include Pylance validation tasks
  - Verify all existing code passes Pylance analysis with zero errors/warnings
  - Document Pylance vs mypy complementary roles in developer workflow

  Notes:
  - Pylance runs continuously in VS Code during development (real-time feedback)
  - mypy runs in CI/CD and pre-commit (batch validation)
  - Both tools REQUIRED per NO DOUBLE STANDARDS policy
  - Pylance catches import issues mypy might miss
  - Zero tolerance for Pylance errors/warnings in production or test code

  Previous Changes (v1.8.0):
  - Added explicit test code quality requirements to eliminate double standards
  - Codified NO DOUBLE STANDARDS policy for test and production code

  Previous Changes (v1.7.0):
  - Added explicit PEP 8 compliance requirement with strict prohibition on inline imports
  - Codified Python community standards through pylint requirements

  Previous Changes (v1.6.0):
  - Added Docker Desktop and database container verification requirement
  - Pre-test infrastructure validation

  Previous Changes (v1.5.0):
  - Added absolute module import path requirement for Python imports
  - All imports within the project must use absolute paths prefixed with `src.`

  Previous Changes (v1.4.0):
  - Added pylint as mandatory code quality tool
  - Required 10.00/10.00 pylint score with zero violations

  Previous Changes (v1.3.1):
  - Strengthened type hints requirement for trivial types
  - Mandated explicit type annotations throughout codebase

  Previous Changes (v1.3.0):
  - Added comprehensive type hints requirement to Technical Standards
  - Mandated type hints in test code

  Previous Changes (v1.2.0):
  - Added LF-only line ending requirement
  - Added file encoding standards

  Previous Changes (v1.1.0):
  - Added Pydantic as mandatory data validation library
  - Added Data Models subsection with Pydantic requirements
-->

# Python-SDD Constitution

## Core Principles

### I. Specification-First Development

Every feature MUST begin with a complete specification before any implementation.
Specifications MUST include:

- User scenarios with acceptance criteria
- Functional requirements (FR-XXX format)
- Edge cases and error handling
- Key entities and their relationships

**Rationale**: Clear specifications prevent scope creep, enable accurate estimation,
and serve as contracts between stakeholders and developers. Without specs,
implementations drift from requirements.

### II. Test-Driven Development (NON-NEGOTIABLE)

All features MUST follow strict TDD workflow:

1. Write tests FIRST based on specification
2. User approves tests
3. Verify tests FAIL
4. Implement until tests PASS
5. Refactor while maintaining green tests

**Red-Green-Refactor cycle is mandatory**. No code without tests. No tests written
after implementation.

**Rationale**: TDD ensures test coverage, validates specifications are testable,
and produces more maintainable code. Tests written after implementation often miss
edge cases and may be biased toward existing code structure.

### III. Independent User Stories

User stories MUST be:

- **Prioritized** (P1, P2, P3, etc.) by business value
- **Independently testable** - each story delivers standalone value
- **Incrementally deliverable** - can be deployed separately
- **Organized by user journey** - not by technical layer

Each user story represents a complete vertical slice that can function as a
minimal viable product increment.

**Rationale**: Independent stories enable parallel development, reduce merge
conflicts, allow early user feedback, and support incremental delivery.
Layered organization (database first, then API, then UI) delays value delivery.

### IV. Quality Gates

All work MUST pass these gates before proceeding:

**Phase 0 (Pre-Planning)**:

- Constitution compliance verified
- Specification complete and approved
- Test cases defined and approved

**Phase 1 (Design)**:

- Technical plan documented (plan.md)
- Data models defined
- API contracts specified
- Constitution re-check passed

**Phase 2 (Implementation)**:

- All linting passes (ruff on src/ AND tests/)
- Type checking passes (mypy on src/ AND tests/)
- Pylint score 10.00/10.00 (on src/ AND tests/)
- All tests pass (pytest)
- Test code quality verified (same standards as production)
- Code review approved (reviews test code equally with production code)

**Test Code Validation (mandatory in Phase 2)**:

- Run `pylint tests/` → MUST score 10.00/10.00
- Run `mypy --strict tests/` → MUST pass with zero errors
- Run `ruff check tests/` → MUST pass with zero violations
- Run Pylance analysis → MUST have zero errors and zero warnings
- Verify all test functions have type hints including `-> None`
- Verify zero inline imports in test files
- Verify all test fixtures have explicit type annotations

**Rationale**: Gates prevent downstream rework. Finding issues early costs
less than finding them late. Gates create natural checkpoints for stakeholder
validation. Test code quality gates ensure tests remain maintainable and reliable.

### V. Code Quality Standards

All Python code MUST adhere to:

- **PEP 8 compliance**: Strict adherence to PEP 8 style guide REQUIRED
- **Linting**: ruff (E, W, F, I, N, UP, B, C4, SIM, S rules) + pylint
- **Type checking**: mypy with strict mode + Pylance (VS Code language server)
- **Testing**: pytest with appropriate coverage
- **Formatting**: ruff format with 90-char line length
- **Commits**: Conventional Commits format
- **Pre-commit hooks**: Automated quality checks enforced

**Pylance Requirements**:

All Python code MUST pass Pylance analysis with zero errors and zero warnings:

- **Type checking**: Pylance type checker mode set to "strict" or "basic" minimum
- **Import resolution**: All imports must resolve correctly with zero "Import could not be resolved" errors
- **Type completeness**: All functions, methods, and variables must have complete type information
- **Unused code detection**: Zero unused imports, variables, or code (Pylance will flag these)
- **Type compatibility**: All type assignments and function calls must be type-compatible
- **VS Code integration**: Pylance runs continuously during development in VS Code
- **Problems panel**: Zero items in VS Code Problems panel for Python files

**Pylance Configuration**:

Configure Pylance in VS Code settings (`.vscode/settings.json` or user settings):

```json
{
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.diagnosticSeverityOverrides": {
    "reportUnusedImport": "error",
    "reportUnusedVariable": "error",
    "reportUndefinedVariable": "error",
    "reportMissingImports": "error",
    "reportMissingTypeStubs": "warning"
  }
}
```

**Rationale**: Pylance provides real-time IDE feedback during development, catching
errors immediately rather than waiting for CI/CD. It complements mypy by providing
faster feedback loops, better VS Code integration, and catches import resolution
issues that mypy might miss. Pylance analysis ensures code is correct before committing.

**PEP 8 Requirements**:

All Python code MUST strictly follow PEP 8 -- Style Guide for Python Code:

- **Import placement**: ALL imports MUST be at the top of the file, immediately after module docstring and before any module-level code
- **Import ordering**: Group imports by: (1) standard library, (2) third-party packages, (3) local application/library imports (separated by blank lines)
- **No inline imports**: Imports inside functions, methods, or classes are STRICTLY PROHIBITED (except in rare cases with explicit constitution amendment)
- **Line length**: Maximum 88-90 characters (ruff/Black compatible)
- **Naming conventions**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Whitespace**: Follow PEP 8 spacing rules for operators, commas, colons
- **Docstrings**: Required for all public modules, functions, classes, and methods

**Inline Import Prohibition Rationale**:

Imports inside functions/methods violate PEP 8 and are prohibited because:

- **Hidden dependencies**: Cannot see what modules file depends on without reading entire file
- **Readability**: Unexpected imports mid-code break reading flow
- **Tool compatibility**: Static analysis, IDEs, and import checkers work poorly with inline imports
- **Performance**: Module import cost paid on every function call (though Python caches, initial cost still incurred)
- **Convention violation**: PEP 8 explicitly requires top-level placement
- **Maintenance burden**: Developers must search entire codebase to find where modules are imported
- **Testing difficulty**: Mocking/patching inline imports is more complex

**Exceptions** (require explicit constitution amendment):

Inline imports MAY be used ONLY when:

- Avoiding circular import deadlocks (rare, indicates design issue)
- Conditional imports for optional dependencies (better solved with try/except at top)
- Performance-critical code where import cost is measured bottleneck (rare)

All exceptions MUST be documented with inline comments explaining justification.

**Rationale**: Consistent code quality reduces cognitive load, prevents bugs,
eases onboarding, and enables safe refactoring. Automated enforcement removes
human inconsistency. Pylint complements ruff by providing semantic analysis,
design pattern checks, and code smell detection that static formatters miss.
PEP 8 compliance ensures the codebase follows Python community standards and
integrates seamlessly with the broader Python ecosystem.

## Development Workflow

All features follow this structured workflow:

1. **Specification** (`/speckit.spec`): Create spec.md with user stories,
   requirements, and acceptance criteria
2. **Planning** (`/speckit.plan`): Generate plan.md with technical approach,
   structure, and constitution verification
3. **Task Breakdown** (`/speckit.tasks`): Generate tasks.md organized by
   user story with clear dependencies
4. **Implementation**: Execute tasks in order, following TDD cycle
5. **Review**: Code review verifies constitution compliance
6. **Merge**: Only after all quality gates pass

**Branch naming**: `###-feature-name` where ### is a sequential number

**Documentation structure**:

```text
specs/###-feature/
├── spec.md        # Specification
├── plan.md        # Implementation plan
├── research.md    # Phase 0 research
├── data-model.md  # Phase 1 data design
├── quickstart.md  # Phase 1 usage guide
├── contracts/     # Phase 1 API contracts
└── tasks.md       # Phase 2 task list
```

## Technical Standards

**Language**: Python 3.13+
**Package Manager**: uv
**Project Structure**: Single project layout (src/, tests/)
**Testing Framework**: pytest
**Type Checker**: mypy + pylint
**Linter/Formatter**: ruff
**Data Validation**: Pydantic v2
**Version Control**: Git with conventional commits
**CI/CD**: GitHub Actions (lint, type-check, test)

**Data Models**:

All data models MUST use Pydantic for validation, serialization, and type safety:

- Use `pydantic.BaseModel` for all configuration and data transfer objects
- Leverage Pydantic's validation decorators for complex business rules
- Use `Field()` for metadata, constraints, and documentation
- Enable strict mode for type coercion control
- Use Pydantic's built-in serialization for JSON/dict conversion

**Rationale**: Pydantic provides runtime validation, automatic type coercion,
comprehensive error messages, and excellent integration with type checkers.
It reduces boilerplate validation code and catches errors early.

**Test Organization**:

- `tests/contract/`: API contract tests
- `tests/integration/`: Cross-component integration tests
- `tests/unit/`: Unit tests for individual functions/classes
- `tests/performance/`: Performance and benchmarking tests

**Test Code Quality Requirements (NON-NEGOTIABLE)**:

Test code MUST meet the EXACT SAME quality standards as production code:

- **NO DOUBLE STANDARDS**: Tests are first-class code, not second-class
- **PEP 8 compliance**: All PEP 8 rules apply equally to tests
- **Type hints**: ALL test functions MUST have explicit type annotations including `-> None`
- **Import placement**: ALL imports at top of file, ZERO inline imports in test functions
- **Pylint score**: Tests MUST achieve 10.00/10.00 pylint score (run: `pylint tests/`)
- **Mypy compliance**: Tests MUST pass `mypy --strict tests/`
- **Ruff compliance**: Tests MUST pass `ruff check tests/`
- **Docstrings**: Test functions MUST have docstrings explaining what they verify

**Test-Specific Standards**:

- Test function names: `test_<what_is_being_tested>` (descriptive, snake_case)
- Test fixtures: Type-annotated with explicit return types
- Assertions: Use pytest assertions, not bare asserts
- Test data: Organize in `tests/*/fixtures/` directories
- Mock objects: Properly typed with explicit Mock[] type hints

**Enforcement**:

- CI/CD MUST run `pylint tests/` and FAIL if score < 10.00/10.00
- Pre-commit hooks MUST check test code quality
- Code review MUST verify test code meets production standards
- Any test code violations are treated as production code violations

**Rationale**: Poor quality test code undermines the entire TDD process. Tests that
are hard to read, maintain, or understand provide false confidence. If tests don't
meet production quality standards, they become technical debt that blocks refactoring.
Test code is executed as frequently as production code and must be equally maintainable.

**Test Environment Requirements**:

Before executing any tests, the following infrastructure verification MUST be performed:

1. **Docker Desktop Status**: Verify Docker Desktop is running and accessible
   - Check that Docker daemon responds to commands
   - Provide clear error message if Docker Desktop is not running
   - Guide users to start Docker Desktop before proceeding

2. **Database Container Verification**: Verify required database container is running
   - Check for active PostgreSQL or pgvector container
   - Verify container health status is "healthy" or "running"
   - Confirm container is accepting connections on expected ports
   - Provide clear error with container name if not found or unhealthy

3. **Pre-Test Validation**: All test suites MUST perform environment checks before running tests
   - Integration tests MUST verify database connectivity
   - Contract tests MUST verify API dependencies are available
   - Unit tests MAY skip infrastructure checks if truly isolated

**Implementation Requirements**:

- Create pytest fixtures or conftest.py setup to validate infrastructure
- Fail fast with actionable error messages when infrastructure is unavailable
- Include infrastructure status in test setup output
- Document required Docker containers in test README.md

**Rationale**: Tests fail cryptically when Docker Desktop is stopped or database
containers are not running. Explicit verification before test execution:

- Prevents confusing error messages from connection failures
- Reduces debugging time for environment issues
- Ensures consistent test environment across development machines
- Provides clear guidance to developers on how to fix infrastructure issues
- Catches configuration problems early before expensive test runs

**Dependency Management**: Declare all dependencies in pyproject.toml with
version constraints. Use optional dependencies for dev tools.

**Module Import Paths**:

All Python imports within the project MUST use absolute module paths prefixed with `src.`:

- **Absolute imports required**: `from src.csv_postgres_pipeline.exceptions import DatabaseError`
- **Never use relative imports**: NOT `from .exceptions import DatabaseError`
- **Never use package-relative imports**: NOT `from csv_postgres_pipeline.exceptions import DatabaseError`
- **Standard library**: Use direct imports: `import os`, `from pathlib import Path`
- **Third-party packages**: Use direct imports: `from psycopg import sql`
- **Within project modules**: ALWAYS prefix with `src.`: `from src.csv_postgres_pipeline.models import CSVFile`

**Module import patterns**:

```python
# ✅ CORRECT: Absolute path with src. prefix
from src.csv_postgres_pipeline.database import create_connection_pool
from src.csv_postgres_pipeline.models import DatabaseConfig, CSVFile
from src.csv_postgres_pipeline.exceptions import ValidationError

# ❌ INCORRECT: Relative imports
from . import database
from .models import CSVFile
from ..utils import helper

# ❌ INCORRECT: Package-relative imports (missing src. prefix)
from csv_postgres_pipeline.database import create_connection_pool
from csv_postgres_pipeline.models import CSVFile

# ✅ CORRECT: Standard library and third-party
import sys
from pathlib import Path
from psycopg import sql
from pydantic import BaseModel
```

**Rationale**: Absolute imports with explicit `src.` prefix:

- **Eliminate ambiguity**: Clear distinction between project modules and external packages
- **Consistent resolution**: Works identically in all contexts (CLI, tests, IDE, debugging)
- **Refactoring safety**: Moving files doesn't break relative import chains
- **IDE support**: Better autocomplete, navigation, and refactoring tools
- **Explicit dependencies**: Import paths document the module structure clearly
- **Testing clarity**: Test imports mirror production imports exactly
- **Avoid confusion**: No guessing whether `.` means parent or sibling module

**Enforcement**: Configure Python path in development tools and test runners to support
`src.` prefix. Use absolute imports in all new code and refactor existing relative
imports during maintenance.

**Pylint Configuration**:

All code MUST pass pylint with zero errors and warnings. Pylint provides
comprehensive code quality checks beyond what ruff offers:

- **Design checks**: Detect code smells, complexity issues, duplicated code
- **Semantic analysis**: Variable scope issues, unused imports/variables with context
- **Documentation**: Enforce docstring presence and format
- **Naming conventions**: Consistent naming patterns across codebase
- **Best practices**: Detect anti-patterns and suggest improvements

**Pylint Requirements**:

- Run pylint on all Python files: `pylint src/ tests/`
- All code MUST achieve pylint score of 10.00/10.00
- Zero errors, zero warnings, zero refactor suggestions allowed
- Configuration via `.pylintrc` or `pyproject.toml`
- Disable rules only with explicit justification in constitution amendment

**Mandatory Pylint Categories**:

- Convention (C): Violate PEP 8, naming conventions
- Refactor (R): Code smell, design issues requiring refactoring
- Warning (W): Minor programming issues, deprecated features
- Error (E): Probable bugs, undefined variables
- Fatal (F): Prevents pylint from working properly

**Pylint Complement to Ruff**:

- Ruff: Fast syntax/style checking, auto-fixing
- Pylint: Deep semantic analysis, design patterns, code complexity
- Both tools MUST pass - they serve different purposes

**Rationale**: Pylint catches issues that purely syntactic linters miss, including
design problems, overly complex functions, and subtle semantic bugs. Combined
with ruff, it ensures comprehensive code quality from both syntactic and
semantic perspectives.

**Type Hints**:

All Python code MUST include comprehensive, explicit type hints throughout:

- **Function signatures**: ALL parameters and return values MUST have explicit type hints
  - Required even for trivial types: `def greet(name: str) -> str:`
  - Required for None returns: `def log_message(msg: str) -> None:`
  - Required for obvious types: `def count() -> int:` (not `def count():`)
- **Variable assignments**: Explicit type annotations REQUIRED for:
  - Module-level constants: `MAX_RETRIES: int = 3`
  - Class attributes: `name: str`, `count: int`
  - Local variables when type is not immediately obvious from assignment
  - Variables assigned `None`: `result: str | None = None` (NEVER `result = None`)
- **Class attributes**: Type hints REQUIRED on all class and instance variables
  - Instance attributes in `__init__`: `self.name: str = name`
  - Class variables: `default_timeout: int = 30`
- **Test code**: Test functions MUST include explicit type hints
  - Test parameters: `def test_validation(mock_db: MockDatabase) -> None:`
  - Pytest fixtures: `def sample_data() -> dict[str, Any]:`
  - Test helpers: `def create_user(name: str, age: int) -> User:`
- **Trivial types MUST be explicit**: Even when "obvious", annotate:
  - String literals: `message: str = "hello"` (not `message = "hello"`)
  - Integer literals: `count: int = 0` (not `count = 0`)
  - Boolean literals: `is_valid: bool = True` (not `is_valid = True`)
  - Empty collections: `items: list[str] = []` (not `items = []`)
  - Any/None: `result: Any | None = None` (not `result = None`)
- **mypy compliance**: All code MUST pass `mypy --strict` with zero errors

**Type Hint Requirements**:

- Use modern typing syntax: `list[str]`, `dict[str, int]` (not `List`, `Dict`)
- Use `T | None` for nullable types (Python 3.10+ union syntax preferred)
- Use `Any` explicitly when type is truly dynamic (with justification comment)
  - Example: `data: Any = json.loads(response)  # Dynamic JSON structure`
- Use Protocol or ABC for interface definitions
- Use TypeAlias for complex or repeated type definitions
- Be explicit over implicit: annotate even when type checker can infer

**Rationale for Explicit Trivial Types**:

"Obvious" is subjective and context-dependent. What's obvious to the author may not
be to reviewers or future maintainers. Explicit annotations:

- Prevent refactoring errors (changing `""` to `None` breaks unannotated code)
- Document intent, not just current implementation
- Enable IDEs to catch errors earlier (e.g., assigning int to str variable)
- Create consistent codebase patterns (no guessing when annotations are needed)
- Support safe code evolution (explicit `str` prevents accidental type changes)

**Exceptions**:

Type hints MAY be omitted only when:

- Technical complications prevent correct typing (document reason)
- Third-party library types are unavailable or broken (use `# type: ignore` with explanation)
- Dynamic metaprogramming makes typing infeasible (rare, requires justification)

These exceptions do NOT apply to "obvious" or "trivial" types - those MUST always
be annotated explicitly.

**Rationale**: Explicit type hints catch bugs at development time, improve IDE
support (autocomplete, refactoring), serve as inline documentation, and enable
confident refactoring. Type inference, even for trivial types, can be ambiguous
and hide bugs during refactoring. Consistent explicit typing across production
and test code ensures comprehensive type safety and eliminates judgment calls
about when annotations are "necessary".

**File Encoding**:

All source code and documentation files MUST use:

- **Character encoding**: UTF-8 without BOM
- **Line endings**: LF (`\n`) only, never CRLF (`\r\n`)
- **Final newline**: All text files MUST end with a single newline character
- **Scope**: Applies to `.py`, `.md`, `.toml`, `.yaml`, `.yml`, `.json`, `.txt`, `.sh`, `.ini`, `.cfg` and similar source/config files
  5
  **Data File Exception**: CSV and other data files processed by the application
  MUST support both LF and CRLF line endings per RFC 4180 and industry standards.
  The application MUST handle both formats transparently without requiring
  conversion. This exception applies only to input data files, not source code.

**Rationale**: LF line endings are the Unix/Linux standard and Python ecosystem
convention. They ensure cross-platform compatibility, prevent git diff pollution
from line ending conversions, and align with most Python tooling expectations.
Mixed line endings cause merge conflicts and inconsistent behavior across
operating systems. However, data files often originate from diverse sources
(Windows, Mac, Linux) and the application must accept industry-standard formats.

**Enforcement**: Configure `.gitattributes` to normalize source file line endings
on commit, and `.editorconfig` to ensure editors use consistent settings. Python's
`csv` module handles data file line endings automatically via universal newline mode.

## Governance

This constitution supersedes all other development practices and guidelines.

**Amendment Process**:

1. Propose changes with justification and impact analysis
2. Update constitution with version bump (semantic versioning)
3. Update all affected templates and documentation
4. Create Sync Impact Report documenting changes
5. Commit with descriptive message

**Version Bump Rules**:

- **MAJOR**: Backward incompatible changes to principles or workflow
- **MINOR**: New principles, sections, or material additions
- **PATCH**: Clarifications, wording improvements, typo fixes

**Compliance Verification**:

- Constitution Check mandatory in plan.md before implementation
- All PRs must include constitution compliance statement
- Complexity violations require explicit justification
- Template consistency verified with each amendment

**Enforcement**:

- Pre-commit hooks enforce code quality standards
- GitHub Actions enforce testing and quality gates
- Code reviews verify constitution adherence
- Failed gates block merges

**Version**: 1.9.0 | **Ratified**: 2026-01-20 | **Last Amended**: 2026-01-22
