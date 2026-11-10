# E2E Test Infra: Rangtsok App

## Test Philosophy
- Automated, repeatable, zero external package dependencies (built upon Python's standard `unittest`).
- Dual verification:
  1. Headless integration tests with ttkbootstrap/Tkinter (`root.withdraw()`) to verify UI events, dynamic widgets, bindings, and end-to-end user flows.
  2. Data and SQLite model tests to verify database integrity, schema migrations, and JSON serialization.

## Feature Inventory & Test Mapping
| # | Feature | Test Suite | File |
|---|---------|------------|------|
| 1 | Manage Account Heads (Add, Delete, Validation, UI sync, Orphan cleanup) | Suite 1 | `tests/test_account_heads.py` |
| 2 | Transactions (Add, Edit, Delete, Receipt numbering, Currency) | Suite 2 | `tests/test_transactions.py` |
| 3 | Calculations (Totals, Defaults, Dynamic sums, Multi-head math) | Suite 3 | `tests/test_calculations.py` |
| 4 | Reporting & Filters (Date filter, Head filter, Multi-criteria, Export) | Suite 4 | `tests/test_reporting.py` |
| 5 | Database Integrity & GB Management (GB deduplication, backup/restore, Excel import) | Suite 5 | `tests/test_integrity.py` |

## Test Runner
- Master Test Runner: `tests/run_all_tests.py`
- Invocation: `python tests/run_all_tests.py` or `python -m unittest discover -s tests -p "test_*.py"`
- Output: Formatted pass/fail counts, total duration, zero exit code on success.

## Coverage Goals
- 100% of inventoried features covered.
- All R1 criteria verified (deletion succeeds cleanly, UI updates immediately, no orphan records).
- All identified bug fixes (B1-B6) explicitly regression-tested.
