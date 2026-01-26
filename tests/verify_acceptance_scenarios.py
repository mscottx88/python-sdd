"""
Verification script for all acceptance scenarios from spec.md.

This script runs the complete test suite and verifies that all acceptance
scenarios from the specification are covered and passing.

Acceptance Scenarios:

User Story 1 (Single CSV File Ingestion):
- AS1.1: Load 1000 rows into existing table
- AS1.2: Map CSV headers to table columns correctly
- AS1.3: Report records loaded and processing time

User Story 2 (Error Handling & Recovery):
- AS2.1: Clear error message for column type mismatch
- AS2.2: Transaction rollback on database connection failure
- AS2.3: Detect malformed CSV before database operations
- AS2.4: Successfully reprocess corrected file
"""

import subprocess
import sys
from pathlib import Path

# Map acceptance scenarios to test functions
ACCEPTANCE_SCENARIOS = {
    "US1": {
        "name": "Single CSV File Ingestion (Priority: P1)",
        "scenarios": {
            "AS1.1": {
                "desc": "Load 1000 rows into existing table",
                "tests": [
                    "tests/integration/test_single_file_load.py::test_single_file_load_success",
                ],
            },
            "AS1.2": {
                "desc": "Map CSV headers to table columns correctly",
                "tests": [
                    "tests/integration/test_single_file_load.py::test_schema_matching_validation",
                    "tests/integration/test_single_file_load.py::test_column_matching_configuration",
                ],
            },
            "AS1.3": {
                "desc": "Report records loaded and processing time",
                "tests": [
                    "tests/integration/test_single_file_load.py::test_progress_reporting",
                ],
            },
        },
    },
    "US2": {
        "name": "Error Handling & Recovery (Priority: P2)",
        "scenarios": {
            "AS2.1": {
                "desc": "Clear error for column type mismatch",
                "tests": [
                    "tests/integration/test_error_handling.py::test_type_mismatch_error_with_context",
                ],
            },
            "AS2.2": {
                "desc": "Transaction rollback on connection failure",
                "tests": [
                    "tests/integration/test_error_handling.py::test_connection_failure_rollback",
                    "tests/integration/test_single_file_load.py::test_transaction_rollback_on_error",
                ],
            },
            "AS2.3": {
                "desc": "Detect malformed CSV before DB operations",
                "tests": [
                    "tests/integration/test_error_handling.py::test_malformed_csv_detection_before_db_ops",
                    "tests/integration/test_single_file_load.py::test_csv_validation_pass_and_fail",
                ],
            },
            "AS2.4": {
                "desc": "Successfully reprocess corrected file",
                "tests": [
                    "tests/integration/test_error_handling.py::test_successful_reprocessing_after_fix",
                ],
            },
        },
    },
}


def run_pytest_tests(test_paths: list[str]) -> tuple[bool, str]:
    """Run pytest tests and return success status and output."""
    cmd = (
        [
            "C:/Users/michael/nearform/python-sdd/.venv/Scripts/python.exe",
            "-m",
            "pytest",
        ]
        + test_paths
        + ["-v", "--tb=short"]
    )

    env = {"PYTHONPATH": "."}
    result = subprocess.run(  # noqa: S603  # cmd is constructed internally, not user input
        cmd, capture_output=True, text=True, cwd=Path.cwd(), env=env
    )
    return result.returncode == 0, result.stdout + result.stderr


def main() -> int:
    """Run all acceptance scenario tests and report results."""
    print("=" * 80)
    print("ACCEPTANCE SCENARIO VERIFICATION")
    print("=" * 80)
    print()

    all_passed = True
    total_scenarios = 0
    passed_scenarios = 0

    for user_story, data in ACCEPTANCE_SCENARIOS.items():
        print(f"\n{user_story}: {data['name']}")
        print("-" * 80)

        scenarios = data["scenarios"]
        assert isinstance(scenarios, dict), "scenarios must be a dict"
        for scenario_id, scenario_data in scenarios.items():
            total_scenarios += 1
            print(f"\n{scenario_id}: {scenario_data['desc']}")
            print(f"  Tests: {', '.join(Path(t).name for t in scenario_data['tests'])}")

            # Run the tests for this scenario
            success, output = run_pytest_tests(scenario_data["tests"])

            if success:
                print("  ✓ PASS")
                passed_scenarios += 1
            else:
                print("  ✗ FAIL")
                print("\n  Error output:")
                # Print last 20 lines of output
                for line in output.split("\n")[-20:]:
                    print(f"    {line}")
                all_passed = False

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total acceptance scenarios: {total_scenarios}")
    print(f"Passed: {passed_scenarios}")
    print(f"Failed: {total_scenarios - passed_scenarios}")

    if all_passed:
        print("\n✓ ALL ACCEPTANCE SCENARIOS PASS")
        return 0
    else:
        print("\n✗ SOME ACCEPTANCE SCENARIOS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
