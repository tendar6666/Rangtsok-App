"""Master Test Runner for Rangtsok App.

Discovers and executes all test suites in the `tests/` directory within
isolated Python subprocesses. Subprocess isolation ensures that Tkinter /
ttkbootstrap root windows, themes, and Tk widgets are initialized and destroyed
cleanly per suite without memory leaks or cross-suite window recycling conflicts.

Outputs an executive summary table and returns exit code 0 if all suites pass.
"""

import os
import sys
import time
import subprocess
import re
from pathlib import Path

# Workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = WORKSPACE_ROOT / "tests"


def discover_test_suites():
    """Discover all test_*.py files in tests/ directory, sorted alphabetically."""
    suites = sorted([
        f.name for f in TESTS_DIR.glob("test_*.py")
        if f.is_file() and not f.name.startswith((".", "_"))
    ])
    return suites


def parse_unittest_output(output, returncode):
    """Parse test counts, failures, errors, and status from unittest output."""
    tests_run = 0
    passed = 0
    failed = 0
    errors = 0

    # Match: "Ran X tests in Y.YYs" or "Ran X test in Y.YYs"
    ran_match = re.search(r"Ran (\d+) tests? in", output)
    if ran_match:
        tests_run = int(ran_match.group(1))

    # Check for OK / FAILED
    ok_match = re.search(r"^OK", output, re.MULTILINE)
    fail_match = re.search(r"^FAILED\s*\((.*?)\)", output, re.MULTILINE)

    if ok_match and returncode == 0:
        passed = tests_run
        failed = 0
        errors = 0
        status = "PASSED"
    else:
        if fail_match:
            details = fail_match.group(1)
            f_m = re.search(r"failures=(\d+)", details)
            e_m = re.search(r"errors=(\d+)", details)
            failed = int(f_m.group(1)) if f_m else 0
            errors = int(e_m.group(1)) if e_m else 0
            passed = max(0, tests_run - (failed + errors))
            status = "FAILED"
        elif returncode != 0:
            status = "ERROR"
            errors = max(1, errors)
            passed = max(0, tests_run - errors)
        else:
            passed = tests_run
            status = "PASSED"

    return tests_run, passed, failed, errors, status


def run_suite(suite_filename):
    """Run a single test suite in an isolated subprocess."""
    start_time = time.perf_counter()
    cmd = [sys.executable, "-m", "unittest", f"tests/{suite_filename}"]

    proc = subprocess.run(
        cmd,
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    elapsed = time.perf_counter() - start_time

    combined_output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    tests_run, passed, failed, errors, status = parse_unittest_output(
        combined_output, proc.returncode
    )

    return {
        "suite": suite_filename,
        "tests_run": tests_run,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "duration": elapsed,
        "status": status,
        "returncode": proc.returncode,
        "output": combined_output,
    }


def print_executive_summary(results, total_duration):
    """Print a formatted executive summary table of test results."""
    col_suite = 42
    col_run = 11
    col_pass = 8
    col_fail = 8
    col_err = 8
    col_dur = 12
    col_stat = 10

    def border(char="-", sep="+"):
        return (
            sep + char * (col_suite + 2) +
            sep + char * (col_run + 2) +
            sep + char * (col_pass + 2) +
            sep + char * (col_fail + 2) +
            sep + char * (col_err + 2) +
            sep + char * (col_dur + 2) +
            sep + char * (col_stat + 2) +
            sep
        )

    print("\n" + "=" * 105)
    print("                      RANGTSOK APP - MASTER TEST SUITE EXECUTION REPORT")
    print("=" * 105)
    print(border("-", "+"))
    print(
        f"| {'Test Suite':<{col_suite}} "
        f"| {'Tests Run':>{col_run}} "
        f"| {'Passed':>{col_pass}} "
        f"| {'Failed':>{col_fail}} "
        f"| {'Errors':>{col_err}} "
        f"| {'Duration':>{col_dur}} "
        f"| {'Status':<{col_stat}} |"
    )
    print(border("=", "+"))

    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    all_passed = True

    for r in results:
        total_tests += r["tests_run"]
        total_passed += r["passed"]
        total_failed += r["failed"]
        total_errors += r["errors"]
        if r["status"] != "PASSED":
            all_passed = False

        dur_str = f"{r['duration']:.2f}s"
        print(
            f"| {r['suite']:<{col_suite}} "
            f"| {r['tests_run']:>{col_run}} "
            f"| {r['passed']:>{col_pass}} "
            f"| {r['failed']:>{col_fail}} "
            f"| {r['errors']:>{col_err}} "
            f"| {dur_str:>{col_dur}} "
            f"| {r['status']:<{col_stat}} |"
        )

    print(border("=", "+"))
    grand_label = f"GRAND TOTALS ({len(results)} Suites)"
    total_dur_str = f"{total_duration:.2f}s"
    overall_status = "PASSED" if all_passed else "FAILED"

    print(
        f"| {grand_label:<{col_suite}} "
        f"| {total_tests:>{col_run}} "
        f"| {total_passed:>{col_pass}} "
        f"| {total_failed:>{col_fail}} "
        f"| {total_errors:>{col_err}} "
        f"| {total_dur_str:>{col_dur}} "
        f"| {overall_status:<{col_stat}} |"
    )
    print(border("-", "+"))

    # Print summary highlights
    print("\nSUMMARY METRICS:")
    print(f"  * Total Test Suites Run : {len(results)}")
    print(f"  * Total Test Cases Executed: {total_tests}")
    print(f"  * Total Tests Passed    : {total_passed}")
    print(f"  * Total Tests Failed    : {total_failed}")
    print(f"  * Total Errors          : {total_errors}")
    print(f"  * Total Elapsed Time    : {total_duration:.2f} seconds")
    print(f"  * Overall Suite Result  : {'[SUCCESS] ALL TESTS PASSED' if all_passed else '[FAILURE] SOME TESTS FAILED'}")
    print("=" * 105 + "\n")

    # If any failures, print their details
    if not all_passed:
        print("\n--- FAILURE / ERROR LOGS ---")
        for r in results:
            if r["status"] != "PASSED":
                print(f"\n>>> Suite: {r['suite']} (Return Code {r['returncode']})")
                print(r["output"].strip())
                print("-" * 80)

    return all_passed


def main():
    suites = discover_test_suites()
    if not suites:
        print("ERROR: No test suites found in tests/ directory.")
        sys.exit(1)

    print(f"Discovered {len(suites)} test suites in tests/:")
    for idx, s in enumerate(suites, 1):
        print(f"  {idx}. {s}")
    print("\nExecuting suites sequentially in isolated subprocesses...\n")

    results = []
    overall_start = time.perf_counter()

    for idx, s in enumerate(suites, 1):
        print(f"[{idx}/{len(suites)}] Running {s} ...", end=" ", flush=True)
        res = run_suite(s)
        print(f"{res['status']} ({res['tests_run']} tests, {res['duration']:.2f}s)")
        results.append(res)

    total_duration = time.perf_counter() - overall_start
    all_passed = print_executive_summary(results, total_duration)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
