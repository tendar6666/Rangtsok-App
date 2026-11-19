# Rangtsok App — Voluntary Contribution Recording System

An open-source Windows desktop application built with Python (`tkinter`, `ttkbootstrap`, `SQLite`, `pandas`) for recording voluntary contributions, maintaining a Green Book (GB) master database, and generating filterable Excel reports.

---

## Key Features

- **Fast Contribution Entry Form**:
  - Automatic receipt number increment with zero-padding preservation.
  - Live **auto-lookup** of Green Book holders (auto-fills Full Name and optional Aadhaar Number) and automatic database upsert on Save (`Ctrl+S`).
  - Centered **Recent Entries (Last 10)** panel with auto-sized columns and double-click to edit.
  - Configurable Financial Year periods, currencies, countries/places, and dynamic Account Heads.
- **Green Book (GB) Database**:
  - Instant 2-column (`GB Number, Name`) or 3-column (`GB Number, Name, Aadhaar Number`) **paste directly from Excel clipboard**.
  - Live search across GB Number, Name, and Aadhaar Number, plus sorting by **Recently Added**, **Name (A–Z / Z–A)**, or **GB Number**.
  - One-click **Clean Database** deduplication and **Backup Database** utility.
  - Optional **Aadhaar Number** toggle in Settings (hiding it never erases stored values).
- **Reports & Filters**:
  - Clean 2-zone layout separating search/sort controls from **Export Excel**, **Import Excel**, and **Delete Selected**.
  - Filter by Date Range, Country, Place, Currency, Receipt No, GB Number, Name, or Account Head.
  - Sort by **Entry Order (ID)**, **Receipt Number** (natural numeric order), **Transaction Date**, **Total Amount**, or by clicking any column header (`TOTAL` stays pinned at the bottom and is preserved in Excel exports).

---

## Installation & Usage

### Option 1: Standalone Windows Executable (Recommended)
1. Download the latest **`Rangtsok_app.exe`** (and optional **`User_Manual.pdf`**) from the [Releases](https://github.com/tendar6666/Rangtsok-App/releases) page.
2. Double-click `Rangtsok_app.exe` to run. No Python installation is required.
3. Your local database (`paljor_contribution.db`) and `settings.json` are created automatically in the same folder.

> **Windows SmartScreen Notice**: Until code signing is active, Windows may display *"Windows protected your PC — Unknown publisher"* on first launch of an unsigned open-source `.exe`. Click **More info → Run anyway**. All source code and automated build workflows are publicly verifiable in this repository.

### Option 2: Run From Source
```bash
pip install -r requirements.txt
python Rangtsok_app.py
```

### Running the Automated Test Suite
```bash
python tests/run_all_tests.py
```

---

## Privacy Policy

- **100% Offline & Local**: Rangtsok App stores all contribution records, Green Book holder details, and settings strictly in local files (`paljor_contribution.db` and `settings.json`) on the user's own computer.
- **Zero Telemetry / No External Transfers**: This program does **not** transmit any user data, personal information, financial records, or analytics to external servers or third parties.

---

## Code Signing Policy

Free code signing is provided by [SignPath.io](https://signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

- **Team Roles**:
  - **Authors & Approvers**: Repository maintainers (`tendar6666`).
- **Build & Signing Process**:
  - Release binaries (`Rangtsok_app.exe`) are built automatically via GitHub Actions directly from the public source code in this repository (`.github/workflows/build.yml`).
  - Only verified release builds from the `main` branch / release tags are submitted for signing and published to GitHub Releases.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
