# Project: Rangtsok App Maintenance, Bug Fixing & Testing

## Architecture
- **Language & Runtime**: Python 3.13 (Windows 64-bit)
- **GUI Framework**: Tkinter + ttkbootstrap 2.2.3 (Themes: cosmo, superhero)
- **Data & Storage**: Embedded SQLite3 database (`paljor_contribution.db`) + `settings.json` configuration
- **Data Analysis & Export**: pandas 3.0.2, openpyxl 3.1.5
- **Documentation**: fpdf2 2.8.7 (`generate_manual.py` -> `User_Manual.pdf`)
- **Packaging**: PyInstaller 6.20.0 (`Rangtsok_app.spec` -> `dist/Rangtsok_app.exe`)
- **Key Modules**:
  - `Rangtsok_app.py`: Main application class `ContributionApp`, entry point, GUI tabs, SQLite queries, settings management
  - `generate_manual.py`: PDF manual generation
  - `settings.json`: Configuration (account heads, currency, places, countries, theme)
  - `paljor_contribution.db`: SQLite tables `transactions` and `gb_database`

## Code Layout
- `Rangtsok_app.py`: Core application code
- `generate_manual.py`: User manual builder
- `settings.json`: Default settings configuration
- `paljor_contribution.db`: Primary database
- `tests/`: Automated test suite
  - `test_account_heads.py`: Account head management, creation, validation, deletion, UI sync, orphan cleanup
  - `test_transactions.py`: Transaction entry, editing, deletion, receipt numbers
  - `test_calculations.py`: Total calculation, multi-head sums, currency formatting
  - `test_reporting.py`: Filtering (by date, head, GB, place), export, summary calculations
  - `test_integrity.py`: Database integrity, GB deduplication, Excel import/export
  - `run_all_tests.py`: Master test runner executing all suites with summary report
- `APP_IMPROVEMENT_RECOMMENDATIONS.md`: Comprehensive improvement report

## Feature Inventory
| # | Feature ID | Feature Name | Description | Milestone | Source |
|---|------------|--------------|-------------|-----------|--------|
| 1 | FEAT-01 | Manage Account Heads UI | Settings tab treeview and input form for adding/deleting account heads | M1 | Survey |
| 2 | FEAT-02 | Account Head Deletion | Deleting unused account heads from settings & database cleanly | M1 | Survey (R1) |
| 3 | FEAT-03 | Dynamic Form Inputs | Dynamically generated input fields on Entry Form tab based on configured account heads | M1 | Survey |
| 4 | FEAT-04 | Report Head Filter Sync | Dropdown filter in Reports tab synchronized with active account heads | M1 | Survey |
| 5 | FEAT-05 | Report Date Filter Fix | Report filter by Date-type head without TypeError crash | M2 | Survey (B1) |
| 6 | FEAT-06 | Treeview Column Auto-Resize | Double-click separator to auto-fit columns in report tree | M2 | Survey (B2) |
| 7 | FEAT-07 | Receipt Auto-Increment | Auto-incrementing receipt numbers preserving zero padding (e.g. 000100 -> 000101) | M2 | Survey (B3) |
| 8 | FEAT-08 | GB Deduplication Longest Name | GB database cleansing retaining longest name as documented | M2 | Survey (B4) |
| 9 | FEAT-09 | Currency Safety | Safe handling of empty or unconfigured currency strings | M2 | Survey (B5) |
| 10 | FEAT-10 | Excel Import Robustness | Support standard ISO dates and NaN-safe ingestion | M2 | Survey (B6) |
| 11 | FEAT-11 | Transaction Entry & Edit | Recording new transactions and editing existing entries | M3 | Survey |
| 12 | FEAT-12 | GB Auto-Fill & Search | Searching and auto-filling member name, place, country from GB number | M3 | Survey |
| 13 | FEAT-13 | Financial Calculations | Real-time calculation of total amount across dynamic heads | M3 | Survey |
| 14 | FEAT-14 | Excel Export & Reporting | Exporting filtered transactions to Excel with sum headers | M3 | Survey |
| 15 | FEAT-15 | Database Backup & Restore | SQLite database backup and restoration workflows | M3 | Survey |
| 16 | FEAT-16 | Automated Test Suite | Python unittest automated test suite covering all key workflows | M3 | Survey (R2) |
| 17 | FEAT-17 | Improvement Recommendations | Written report on architecture, UX, reliability, and functionality | M4 | Survey (R3) |
| 18 | FEAT-18 | E2E & Build Verification | Full test execution, executable packaging, manual build | M5 | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Fix Account Head Deletion (R1) | Fix KeyError 'name', SQL usage query, zero-default vs active usage, orphan key purge, UI sync | none | DONE |
| 2 | M2: Application Bug Fixing | Fix Date filter crash, event binding collision, receipt increment, GB deduplication, currency safety | M1 | DONE |
| 3 | M3: Automated Test Suite (R2) | Build comprehensive 5-suite automated test framework (tests/) and verify 100% pass | M1, M2 | DONE |
| 4 | M4: Improvement Recommendations (R3) | Author detailed APP_IMPROVEMENT_RECOMMENDATIONS.md | none | DONE |
| 5 | M5: E2E Verification & Build | Execute full test suite, verify PyInstaller build, verify manual generation, forensic audit | M1, M2, M3, M4 | DONE |

## Interface Contracts
### `ContributionApp.delete_account_head()`
- Pre-conditions: Selected row in `self.tree_heads`.
- Checks: Active financial usage (`amount > 0` or non-empty date string in `transactions.account_data`).
- If used actively: Show `messagebox.showerror("Deletion Blocked", ...)` and return.
- If unused:
  - Remove from `self.settings["account_heads"]`.
  - Save settings via `save_settings(self.settings)`.
  - Purge inactive/0.0/empty keys from `transactions.account_data`.
  - Refresh settings treeview `self.refresh_settings_heads_list()`.
  - Refresh entry inputs `self.build_dynamic_account_inputs()`.
  - Refresh report filter `self.refresh_report_filters()`.
  - Clear settings entry inputs `self.ent_head_name.delete(0, tk.END)`, etc.
  - Show confirmation / success feedback.
