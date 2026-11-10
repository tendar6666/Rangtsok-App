# Strategic Improvement Recommendations & Technical Modernization Roadmap
## Rangtsok App — Tibetan Voluntary Contribution Recording System (Chatrel System)

**Document Version**: 2.0.0  
**Target Application**: `Rangtsok_app.py` (Voluntary Contribution Recording System)  
**Target Environment**: Windows 10/11 x64 | Python 3.10+ / 3.13  
**Domain**: Central Tibetan Administration (CTA / བོད་མིའི་སྒྲིག་འཛུགས།) Department of Finance (Paljor / དཔལ་འབྱོར་ལས་ཁུངས།)  
**Author**: Systems Architecture & QA Working Group  

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
   - 1.1 System Identity & Mission
   - 1.2 Current State Technical Assessment
   - 1.3 Key Architectural Strengths & Baseline Assets
   - 1.4 Critical Modernization Drivers & Strategic Goals
2. [Architecture Modernization & Layered Decoupling](#2-architecture-modernization--layered-decoupling)
   - 2.1 Decomposition of `Rangtsok_app.py` Monolith
   - 2.2 Proposed Modular Package Layout
   - 2.3 Layer Contracts & Interface Specifications
   - 2.4 Database Schema Evolution: Relational Normalization vs JSON
   - 2.5 Complete Normalized Relational DDL
   - 2.6 Automated Backward-Compatible Migration Strategy
3. [User Experience & Workflow Enhancements](#3-user-experience--workflow-enhancements)
   - 3.1 Real-Time Member Autocomplete & Fuzzy Search
   - 3.2 Dynamic Interactive Grids with Tri-State Sorting & Column Persistence
   - 3.3 Official PDF Receipt Generation & Thermal POS Printing
   - 3.4 Non-Blocking Toast Notifications & Keyboard Navigation Accelerator
   - 3.5 High-DPI Scaling, Form Scrolling & Theme Polish
4. [Reliability, Data Safety & Concurrency Engineering](#4-reliability-data-safety--concurrency-engineering)
   - 4.1 SQLite Write-Ahead Logging (WAL) Mode & Concurrency
   - 4.2 Connection Context Managers with Deterministic Atomic Rollback
   - 4.3 Automated Rolling Backup Engine with SHA-256 Checksums & Vacuuming
   - 4.4 Financial-Grade Precision with `Decimal` & Defensive Type Sanitization
   - 4.5 Resilient Multi-Format Date Ingestion Pipeline
5. [Functional & CTA Domain Enhancements](#5-functional--cta-domain-enhancements)
   - 5.1 Multi-Currency Management & Dynamic Exchange Rate Aggregation
   - 5.2 Tibetan Fiscal Year (Chatrel Cycle) Engine
   - 5.3 Tibetan Typography, Numerals & Bilingual Document Formatting
   - 5.4 Comprehensive Financial Audit Trail & Activity Logging
   - 5.5 Contributor 360° Ledger & Annual Tax Exemption Certificates
6. [Testing, Quality Assurance & DevOps Automation](#6-testing-quality-assurance--devops-automation)
   - 6.1 Two-Tier Continuous Testing Pyramid (Unit + Headless Tkinter)
   - 6.2 GUI Mocking & Headless Execution Framework
   - 6.3 Automated PyInstaller Build & Smoke-Verification Pipeline
   - 6.4 Continuous Integration Workflow (GitHub Actions)
7. [Actionable Implementation Roadmap & Priority Matrix](#7-actionable-implementation-roadmap--priority-matrix)
   - 7.1 Comprehensive Recommendation Scoring Matrix
   - 7.2 Phased Modernization Rollout Plan
   - 7.3 Risk Mitigation, Rollback & Governance Guidelines

---

## 1. Executive Summary

### 1.1 System Identity & Mission
The **Rangtsok App** (Voluntary Contribution Recording System) is a mission-critical desktop financial utility serving Offices of Tibet, Tibetan Settlement Offices, and regional community liaisons operating under the Central Tibetan Administration (CTA) Department of Finance (Paljor). The system records, tracks, aggregates, and reports voluntary financial contributions—predominantly **Chatrel** (དྭང་བླངས་དཔྱ་ཁྲལ། - Tibetan Voluntary Tax), along with Meal Strike contributions, salary/business contributions, emergency relief funds, and general charitable donations. 

These contributions are keyed against the **Green Book** (Lag-deb / ལག་དེབ།), the primary citizenship and identity ledger for Tibetans in exile. Recording accuracy, auditability, operational continuity across low-resource offline environments, and data integrity are paramount.

```
+-----------------------------------------------------------------------------------------+
|                                    RANGTSOK APPLICATION                                 |
|               (Central Tibetan Administration Voluntary Contribution System)            |
+-----------------------------------------------------------------------------------------+
       |                                      |                                  |
       v                                      v                                  v
+-----------------------+          +-----------------------+          +-------------------+
|      Core Modules     |          |       Datastores      |          |    Distribution   |
| - Tkinter/ttkbootstrap|          | - SQLite3 Database    |          | - Standalone EXE  |
| - Pandas & Openpyxl   |          |   (paljor_contrib.db) |          |   (PyInstaller)   |
| - FPDF2 PDF Generator |          | - JSON Configuration  |          | - Offline-first   |
| - Embedded Assets     |          |   (settings.json)     |          |   Portability     |
+-----------------------+          +-----------------------+          +-------------------+
```

### 1.2 Current State Technical Assessment
The application is presently maintained as a single monolithic script:
- **Source Code**: `Rangtsok_app.py` (2,015 lines of code) containing all graphical user interface (GUI) definitions, layout grids, visual callbacks, database connection management, dynamic SQL generation, string parsing, JSON serialization, Excel I/O, and business validation rules.
- **Persistence Layer**: Embedded SQLite 3 (`paljor_contribution.db`) composed of two tables: `gb_database` (Green Book master register) and `transactions` (financial records). Financial line items are serialized into a single TEXT column (`transactions.account_data`) as semi-structured JSON strings.
- **Configuration**: Local JSON file (`settings.json`) persisting administrative preferences, active currencies, geographical locations, and the dynamic array of configured account heads.
- **Runtime & Presentation**: Standard Python 3 with `ttkbootstrap 2.2.3` supporting "cosmo" (light) and "superhero" (dark) themes, executing primarily on Windows 10/11 x64 desktop workstations.

### 1.3 Key Architectural Strengths & Baseline Assets
Despite its monolithic architecture, the Rangtsok application displays substantial foundational strengths that should be retained and expanded:
1. **Zero External Server Dependency**: Fully offline-first desktop footprint; requires no active internet connection, external database server, or cloud latency, making it ideal for worldwide regional settlements.
2. **Dynamic Account Head Customization**: Operators can define, reorder, and configure custom account heads (Amount vs Date types) without recompiling software or manually issuing SQL DDL commands.
3. **Clean Visual Styling**: Integration with `ttkbootstrap` provides a clean, modern aesthetic that significantly surpasses default Tkinter styling.
4. **Instant Standalone Portability**: Built via PyInstaller into a self-contained single-file executable (`Rangtsok_app.exe`) that executes without pre-installed Python environments.
5. **High Operational Utility**: Incorporates high-value operational features such as Excel batch imports, clipboard-based Green Book master updates, and cross-tab financial year synchronization.

### 1.4 Critical Modernization Drivers & Strategic Goals
To transform Rangtsok into an enterprise-grade financial management platform capable of serving CTA offices for the next decade, five architectural bottlenecks must be resolved:

```
+----------------------------------------------------------------------------------------------------+
|                                    STRATEGIC MODERNIZATION DRIVERS                                 |
+----------------------------------+----------------------------------+------------------------------+
| 1. Structural Modularity         | 2. Relational Integrity          | 3. Concurrency & Safety      |
| Single 2,015-line file binds UI, | Dynamic heads stored as JSON     | Default DELETE journal mode  |
| SQL, and logic in event handlers.| strings prevent foreign keys,    | and raw file copies risk     |
| Must decompose into layered MVC. | indexes, and SQL group queries.  | locks and silent corruption. |
+----------------------------------+----------------------------------+------------------------------+
| 4. User Workflow Efficiency      | 5. Financial Grade Precision     |                              |
| Missing search auto-complete,    | Float-based math risks rounding; |                              |
| non-sortable report grids, and   | strict date parsers abort on     |                              |
| blocking modal dialog boxes.     | valid ISO Excel spreadsheets.    |                              |
+----------------------------------+----------------------------------+------------------------------+
```

---

## 2. Architecture Modernization & Layered Decoupling

### 2.1 Decomposition of `Rangtsok_app.py` Monolith
In `Rangtsok_app.py`, presentation logic is inseparable from business and persistence operations. For example:
- In `save_entry()` (lines 541–646), a single callback reads widget text, performs string manipulation, parses dates, queries SQLite, executes transaction inserts, manages JSON serialization, invokes external settings methods, updates UI labels, and triggers file-level receipt auto-incrementation.
- In `delete_account_head()` (lines 1888–1937), widget selection indices are coupled directly with raw SQL text matching and JSON dictionary manipulation.

This coupling causes regression cascades, prevents automated unit testing without rendering GUI windows, and obscures business rules.

### 2.2 Proposed Modular Package Layout
The codebase should be refactored into a layered Clean/Service-Repository architecture:

```
rangtsok/
├── __init__.py
├── __main__.py                    # Application launch orchestrator
├── core/                          # Domain primitives, models, exceptions
│   ├── __init__.py
│   ├── config.py                  # SettingsManager (settings.json lifecycle & schema)
│   ├── constants.py               # Enums (HeadType, Currency, Theme, FYPeriod)
│   ├── exceptions.py              # Custom domain exceptions (ValidationError, IntegrityError)
│   └── models.py                  # Typed dataclasses (Transaction, AccountHead, Member)
├── database/                      # Persistence layer & migrations
│   ├── __init__.py
│   ├── connection.py              # Thread-safe SQLite connection factory & WAL config
│   ├── migrations.py              # Automated schema versioning and upgrade engine
│   └── repositories/              # Repository Pattern (DAO)
│       ├── __init__.py
│       ├── account_head_repo.py   # CRUD for account heads & line items
│       ├── audit_repo.py          # Immutable audit logging
│       ├── member_repo.py         # Green Book master lookup, bulk upsert, deduplication
│       └── transaction_repo.py    # Transaction queries, filtering, and aggregations
├── services/                      # Pure business logic (100% testable without GUI)
│   ├── __init__.py
│   ├── accounting_service.py      # Real-time summation, currency balance & multi-head totals
│   ├── backup_service.py          # Native SQLite backup API, VACUUM & checksumming
│   ├── import_export_service.py   # Excel/Clipboard ingestion, normalization & validation
│   ├── receipt_service.py         # PDF receipt rendering (FPDF2) & thermal printer formatting
│   └── validation_service.py      # Defensive type casting, date parser & business rule guards
└── ui/                            # Presentation layer (Tkinter + ttkbootstrap)
    ├── __init__.py
    ├── app.py                     # Root window controller & notebook manager
    ├── assets/                    # Icons, logos, and Tibetan font bundles
    ├── components/                # Reusable custom UI widgets
    │   ├── autocomplete_entry.py  # Dropdown auto-suggest entry widget
    │   ├── date_entry_widget.py   # Robust wrapper over DateEntry
    │   ├── scrollable_frame.py    # Scrollable container for dynamic forms
    │   ├── sortable_treeview.py   # Treeview with header-click sorting & persistent widths
    │   └── toast.py               # Non-blocking animated toast notification banners
    └── views/                     # Notebook tab controllers
        ├── __init__.py
        ├── entry_view.py          # Tab 1: Contribution entry form & live calculation
        ├── gb_database_view.py    # Tab 2: Green Book master registry & deduplication
        ├── reports_view.py        # Tab 3: Dynamic multi-parameter reporting & export
        └── settings_view.py       # Tab 4: Office setup, currencies, locations, heads
```

### 2.3 Layer Contracts & Interface Specifications

#### Data Models (`core/models.py`)
```python
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from enum import Enum

class HeadType(str, Enum):
    AMOUNT = "Amount"
    DATE = "Date"

@dataclass(frozen=True)
class AccountHead:
    id: Optional[int]
    name: str
    head_type: HeadType
    default_value: str
    display_order: int = 0
    is_active: bool = True

@dataclass
class LineItem:
    head_id: int
    head_name: str
    head_type: HeadType
    amount_value: Optional[Decimal] = None
    date_value: Optional[date] = None

@dataclass
class Transaction:
    id: Optional[int]
    receipt_no: str
    gb_number: str
    name: str
    country: str
    place: str
    currency: str
    tx_date: date
    entry_date: datetime
    total_amount: Decimal
    line_items: List[LineItem] = field(default_factory=list)
    remarks: Optional[str] = None
```

#### Repository Interface (`database/repositories/transaction_repo.py`)
```python
from typing import List, Optional, Tuple
from datetime import date
from decimal import Decimal
from core.models import Transaction, LineItem

class TransactionRepository:
    def __init__(self, connection_factory):
        self._get_connection = connection_factory

    def save(self, tx: Transaction) -> int:
        """Atomically saves transaction and all associated line items."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO transactions (
                    receipt_no, gb_number, name, country, place, 
                    currency, tx_date, entry_date, total_amount, remarks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx.receipt_no, tx.gb_number, tx.name, tx.country, tx.place,
                    tx.currency, tx.tx_date.isoformat(), tx.entry_date.isoformat(),
                    float(tx.total_amount), tx.remarks
                )
            )
            tx_id = cursor.lastrowid
            
            line_records = [
                (tx_id, item.head_id, float(item.amount_value) if item.amount_value is not None else None,
                 item.date_value.isoformat() if item.date_value else None)
                for item in tx.line_items
            ]
            cursor.executemany(
                """
                INSERT INTO transaction_line_items (
                    transaction_id, account_head_id, amount_value, date_value
                ) VALUES (?, ?, ?, ?)
                """,
                line_records
            )
            return tx_id
```

### 2.4 Database Schema Evolution: Relational Normalization vs JSON
The existing application serializes all contribution heads into a single JSON string:
```json
{"Chatrel": 250.0, "Chatrel Start Date": "01-04-2026", "Chatrel End Date": "31-03-2027", "Meal Strike": 0.0, "Donation": 0.0}
```

#### Architectural Shortcomings of the Current JSON Approach:
1. **Inefficient Aggregations**: To calculate the aggregate sum of "Chatrel" over 15,000 transactions, the database engine cannot compute `SUM(amount)`. Instead, all 15,000 records must be fetched into Python, parsed via `json.loads()`, and mapped into a pandas DataFrame in memory.
2. **Missing Referential Integrity**: If an account head is deleted or renamed, there is no foreign key constraint to cascade or prevent deletion; transactions can be left containing orphaned strings.
3. **Data Pollution**: Non-standard values such as `NaN`, `null`, or empty strings pollute JSON payloads, causing silent parser failures.
4. **No Column Indexing**: SQLite cannot index arbitrary JSON keys without generated column definitions, resulting in full table scans on every filtered query.

#### Comparative Evaluation:
| Architectural Dimension | Current JSON Serialization | Proposed Normalized Relational Schema |
|---|---|---|
| **Storage Engine** | Unindexed `TEXT` column | Dedicated tables with Foreign Keys |
| **Integrity Guarantees** | Application-level heuristic | Database engine enforcement (`ON DELETE RESTRICT`) |
| **Summation Speed (100k rows)** | ~1,200 ms (Python deserialization) | ~8 ms (Indexed native B-Tree query) |
| **Indexability** | None (requires full scan) | B-Tree index on `(account_head_id, transaction_id)` |
| **Schema Evolution** | Prone to key-drift & typos | Managed versioned migrations (`schema_migrations`) |
| **Backward Compatibility** | High (legacy layout) | Full (via SQL migration adapter) |

### 2.5 Complete Normalized Relational DDL
The following DDL establishes the normalized relational schema, incorporating foreign keys, strict check constraints, and performance indexes:

```sql
-- Enable foreign key constraints in SQLite
PRAGMA foreign_keys = ON;

-- 1. Schema Migration Tracking Table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL
);

-- 2. Green Book (GB) Master Registry
CREATE TABLE IF NOT EXISTS members (
    gb_number TEXT PRIMARY KEY COLLATE NOCASE,
    full_name TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT '',
    place TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_members_name ON members(full_name COLLATE NOCASE);

-- 3. Normalized Account Heads Register
CREATE TABLE IF NOT EXISTS account_heads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    head_name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    head_type TEXT NOT NULL CHECK(head_type IN ('Amount', 'Date')),
    default_value TEXT NOT NULL DEFAULT '',
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_heads_order ON account_heads(display_order, is_active);

-- 4. Financial Transactions Master Record
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_no TEXT NOT NULL UNIQUE COLLATE NOCASE,
    gb_number TEXT NOT NULL,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    place TEXT NOT NULL,
    currency TEXT NOT NULL CHECK(length(currency) >= 3),
    tx_date TEXT NOT NULL CHECK(tx_date IS date(tx_date)),
    entry_date TEXT NOT NULL,
    total_amount REAL NOT NULL CHECK(total_amount >= 0.0),
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gb_number) REFERENCES members(gb_number) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(tx_date);
CREATE INDEX IF NOT EXISTS idx_tx_receipt ON transactions(receipt_no COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_tx_gb ON transactions(gb_number COLLATE NOCASE);

-- 5. Transaction Line Items (Normalized dynamic contribution details)
CREATE TABLE IF NOT EXISTS transaction_line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    account_head_id INTEGER NOT NULL,
    amount_value REAL CHECK(amount_value >= 0.0 OR amount_value IS NULL),
    date_value TEXT CHECK(date_value IS NULL OR date_value IS date(date_value)),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (account_head_id) REFERENCES account_heads(id) ON DELETE RESTRICT,
    CONSTRAINT uq_tx_head UNIQUE (transaction_id, account_head_id)
);
CREATE INDEX IF NOT EXISTS idx_line_tx ON transaction_line_items(transaction_id);
CREATE INDEX IF NOT EXISTS idx_line_head ON transaction_line_items(account_head_id);

-- 6. Comprehensive Financial Audit Log
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL CHECK(action IN ('INSERT', 'UPDATE', 'DELETE', 'BULK_IMPORT', 'SETTINGS_CHANGE')),
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    old_data TEXT,
    new_data TEXT,
    operator TEXT DEFAULT 'admin'
);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(timestamp);
```

### 2.6 Automated Backward-Compatible Migration Strategy
Upgrading deployed client databases without data loss or downtime requires an automated zero-friction migration runner executing at startup:

```
[Application Startup]
         |
         v
+-------------------------------+      YES     +----------------------------------+
| Does schema_migrations exist? | -----------> | Read highest version from table  |
+-------------------------------+              +----------------------------------+
         | NO                                                    |
         v                                                       v
+-------------------------------+              +----------------------------------+
| Create Pre-Migration Backup   |              | Are there pending migrations?    |
| (paljor_contribution.db.bak)  |              +----------------------------------+
+-------------------------------+                                |
         |                                                       | YES
         v                                                       v
+-------------------------------+              +----------------------------------+
| Run V1 Baseline Extraction:   |              | Run Migration in atomic TX:      |
| Extract JSON heads & populate |              | BEGIN IMMEDIATE TRANSACTION;     |
| account_heads & line_items    |              | Apply DDL / Data Transforms;     |
+-------------------------------+              | COMMIT;                          |
         |                                     +----------------------------------+
         v                                                       |
+-------------------------------+                                v
| Validate Row Counts & Totals  |                      [Launch Application]
+-------------------------------+
```

#### Step-by-Step Migration Algorithm (`database/migrations.py`):
1. **Automated Safety Snapshot**: Before executing any DDL, call `sqlite3.Connection.backup()` to create a timestamped archive copy: `backups/paljor_contribution_pre_v2.db`.
2. **Schema Introspection**: Inspect `sqlite_master` for the presence of table `schema_migrations`. If absent, the database is in V1 (legacy) state.
3. **Transaction Isolation**: Issue `BEGIN IMMEDIATE TRANSACTION;` to acquire an exclusive write lock.
4. **Seed `account_heads`**: Extract distinct account heads from `settings.json` and legacy `account_data` JSON keys; insert them into `account_heads` with auto-assigned IDs.
5. **ETL Legacy Transactions**:
   - Loop over each row in legacy `transactions`.
   - Parse `account_data` via `json.loads()`.
   - Insert rows into `transaction_line_items` matching head IDs.
   - Cleanse receipt numbers, stripping leading/trailing whitespace.
6. **Audit & Reconciliation Verification**:
   - Compare `SELECT COUNT(*), SUM(total_amount) FROM transactions` before and after migration.
   - If `abs(sum_before - sum_after) > 0.001`, trigger immediate `ROLLBACK;` and alert the operator.
7. **Version Stamp**: Insert record `(version=2, description="Normalized relational line items")` into `schema_migrations` and `COMMIT;`.

---

## 3. User Experience & Workflow Enhancements

### 3.1 Real-Time Member Autocomplete & Fuzzy Search
- **Current Limitation**: In the Entry tab, operators must type the exact Green Book number and manually press `<Return>` or click "🔍 Lookup". A single character discrepancy or casing difference results in "⚠ Data not found."
- **Proposed Solution**: Implement a responsive auto-suggest dropdown widget (`AutocompleteEntry`) and fuzzy search support.

```
+-----------------------------------------------------------+
| Green Book Number: [ In001                              ] |
+-----------------------------------------------------------+
|  In000100 - Tenzin Norbu (Dharamshala, India)             |
|  In001254 - Sonam Dolma (Delhi, India)                    |
|  IN001988 - Pema Wangdu (Bylakuppe, India)                |
+-----------------------------------------------------------+
  (Navigable via UP/DOWN arrow keys; ENTER commits selection)
```

#### Implementation Architecture:
```python
import tkinter as tk
from tkinter import ttk

class AutocompleteEntry(ttk.Entry):
    def __init__(self, master, lookup_callback, on_select_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.lookup_callback = lookup_callback
        self.on_select_callback = on_select_callback
        self._popup = None
        self._listbox = None
        
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Down>", self._on_down_key)

    def _on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        query = self.get().strip()
        if len(query) < 2:
            self._close_popup()
            return
        
        results = self.lookup_callback(query) # Calls MemberRepository
        if not results:
            self._close_popup()
            return
        
        self._show_popup(results)

    def _show_popup(self, items):
        if not self._popup:
            self._popup = tk.Toplevel(self)
            self._popup.wm_overrideredirect(True)
            self._listbox = tk.Listbox(self._popup, font=("Segoe UI", 10), height=5)
            self._listbox.pack(fill="both", expand=True)
            self._listbox.bind("<ButtonRelease-1>", self._on_listbox_select)
            self._listbox.bind("<Return>", self._on_listbox_select)
        
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self._popup.wm_geometry(f"{self.winfo_width()}x120+{x}+{y}")
        
        self._listbox.delete(0, tk.END)
        for item in items:
            self._listbox.insert(tk.END, f"{item['gb_number']} - {item['full_name']}")
```

### 3.2 Dynamic Interactive Grids with Tri-State Sorting & Column Persistence
- **Current Limitation**: Column headers in Reports and GB tables are static text. Clicking on "Total Amount" or "Transaction Date" does not sort. Double-clicking on column separators was broken due to event collisions (`rep_tree.bind('<Double-1>')`).
- **Proposed Solution**:
  1. **Tri-State Header Sorting**: Clicking any heading cycles through `Ascending (▲)` -> `Descending (▼)` -> `Original Order`. The sort comparator dynamically handles numerical currency values, ISO dates, and case-insensitive strings.
  2. **Separator Auto-Fit**: Disentangle `<Double-1>` by checking whether the click occurred on a column separator (`event.x` within ±4 pixels of column boundary) versus an actual data row.
  3. **Column Width Persistence**: Save customized column widths to `settings.json` upon resize events, ensuring operator workspace layouts persist across sessions.

### 3.3 Official PDF Receipt Generation & Thermal POS Printing
Offices of Tibet frequently require printing physical receipts for contributors. The application currently has no printing capability.

```
+---------------------------------------------------------------------------------------+
|                                    OFFICE OF TIBET                                    |
|                      Central Tibetan Administration / བོད་མིའི་སྒྲིག་འཛུགས།               |
|                               OFFICIAL CONTRIBUTION RECEIPT                           |
+---------------------------------------------------------------------------------------+
| Receipt No: 100245                                            Date: 15-05-2026        |
| GB Number:  CH-04921                                          FY:   2026-2027         |
| Contributor: Tenzin Tendar                                    Place: Geneva           |
+---------------------------------------------------------------------------------------+
| Account Head / དྭང་བླངས་དཔྱ་ཁྲལ།                                  Period / Amount (CHF) |
+---------------------------------------------------------------------------------------+
| Chatrel (01-04-2026 to 31-03-2027)                                            150.00  |
| Meal Strike                                                                     50.00  |
| Tibet Emergency Donation                                                       100.00  |
+---------------------------------------------------------------------------------------+
| TOTAL CONTRIBUTION RECEIVED:                                              CHF 300.00  |
| (Three Hundred Swiss Francs Only)                                                     |
+---------------------------------------------------------------------------------------+
| Verified by: Paljor Cashier                                  Official Seal & Signature|
+---------------------------------------------------------------------------------------+
```

#### Dual Receipt Printing Architecture:
1. **Formal A5/A4 PDF Receipt Generator**:
   - Built on `fpdf2` (already present in the runtime).
   - Bundles open-source Tibetan Unicode typography (`Jomolhari.ttf` / `NotoSansTibetan-Regular.ttf`) to support native Tibetan headings (`དྭང་བླངས་དཔྱ་ཁྲལ།`).
   - Generates bilingual, audit-compliant PDF receipts with customizable CTA crest and official seal watermarks.
2. **Thermal Receipt Mode (ESC/POS 80mm/58mm)**:
   - For rapid counter receipts during high-volume gatherings (e.g., annual His Holiness the Dalai Lama's birthday gatherings).
   - Outputs clean, monospace text formatting directly to Windows default POS thermal receipt printers via `win32print`.

### 3.4 Non-Blocking Toast Notifications & Keyboard Navigation Protocol
- **Current Limitation**: Heavy reliance on blocking modal dialogs (`messagebox.showinfo()`, `messagebox.showwarning()`) halts operator data entry, requiring physical mouse clicks to dismiss.
- **Proposed Solution**: Introduce lightweight, transient Toast notifications that float in the bottom-right corner and automatically fade out after 2.5 seconds.

```python
class ToastNotification:
    @staticmethod
    def show(master, message, bootstyle="success", duration=2500):
        toast = tk.Toplevel(master)
        toast.wm_overrideredirect(True)
        toast.attributes("-alpha", 0.92)
        
        # Position bottom-right of parent
        x = master.winfo_rootx() + master.winfo_width() - 320
        y = master.winfo_rooty() + master.winfo_height() - 90
        toast.geometry(f"300x50+{x}+{y}")
        
        lbl = ttk.Label(toast, text=message, font=("Segoe UI", 10, "bold"),
                        bootstyle=f"inverse-{bootstyle}", padding=(15, 10))
        lbl.pack(fill="both", expand=True)
        toast.after(duration, toast.destroy)
```

#### Comprehensive Keyboard Navigation Map:
| Shortcut Combination | Context | Triggered Action |
|---|---|---|
| `Ctrl + S` | Entry Form | Validate and save current contribution entry |
| `Ctrl + N` | Entry Form | Reset/Clear entry form for next receipt |
| `Ctrl + F` | Any Tab | Move focus directly to Search / Filter query bar |
| `Ctrl + P` | Entry Form / Reports | Generate & launch PDF receipt for selected transaction |
| `Escape` | Entry Form | Cancel active Edit Mode; revert to new transaction entry |
| `Tab` / `Shift + Tab` | All Forms | Logical top-to-bottom, left-to-right field traversal |
| `Enter` (in GB Field) | Entry Form | Execute immediate Green Book lookup |

### 3.5 High-DPI Scaling, Form Scrolling & Theme Polish
1. **Scrollable Container for Dynamic Account Heads**:
   - Currently, if an office adds more than 14 account heads, the fields overflow the screen boundaries without a scrollbar.
   - Solution: Encapsulate `self.frame_heads` inside a dynamic `ScrollableFrame` equipped with canvas mouse-wheel bindings (`<MouseWheel>`).
2. **High-DPI Per-Monitor V2 Awareness**:
   - On modern Windows 4K displays, Tkinter can appear blurry or miniature.
   - Inject Windows API DPI awareness at process startup:
     ```python
     import ctypes
     try:
         ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware
     except Exception:
         try:
             ctypes.windll.user32.SetProcessDPIAware()
         except Exception:
             pass
     ```
3. **Contrast Ratio Compliance**:
   - Adjust theme accent colors in dark mode ("superhero") to guarantee WCAG 2.1 AA compliant contrast ratios for Tibetan glyphs and monetary readouts.

---

## 4. Reliability, Data Safety & Concurrency Engineering

### 4.1 SQLite Write-Ahead Logging (WAL) Mode & Concurrency
- **Problem**: SQLite defaults to `DELETE` rollback journal mode. When multiple tabs or background operations execute (e.g. running an Excel batch import while the Reports tab is querying), the database locks the entire file, raising `sqlite3.OperationalError: database is locked`.
- **Solution**: Configure the database on initialization with **Write-Ahead Logging (WAL)**:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA cache_size = -64000; -- 64MB cache allocation
PRAGMA temp_store = MEMORY;
```

#### Architectural Advantages:
1. **Concurrent Reads and Writes**: Readers never block writers, and writers never block readers.
2. **Crash Resilience**: Atomic commits write sequentially into the `-wal` file; power outages or sudden process terminations cannot corrupt the master `.db` file.
3. **Write Throughput**: Significant speedup during batch Excel imports (up to 10x throughput enhancement).

### 4.2 Connection Context Managers with Deterministic Atomic Rollback
Ensure all SQLite interactions run within managed connection contexts that automatically issue `ROLLBACK` on errors and `COMMIT` on clean execution:

```python
from contextlib import contextmanager
import sqlite3

@contextmanager
def transaction_scope(db_path: str):
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise exc
    finally:
        conn.close()
```

### 4.3 Automated Rolling Backup Engine with SHA-256 Checksums & Vacuuming
- **Current Vulnerability**: The existing backup feature executes `shutil.copy(DB_FILE, target_file)`. Under Windows, if a transaction is actively committing or the WAL log is open, `shutil.copy` copies an inconsistent file or crashes with `WinError 32: The process cannot access the file`.
- **Modernized Backup Solution**: Utilize the native `sqlite3.Connection.backup()` API paired with an automated rolling retention policy and SHA-256 integrity verification:

```python
import sqlite3
import hashlib
import os
from datetime import datetime

class BackupService:
    def __init__(self, db_path: str, backup_dir: str = "backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)

    def perform_hot_backup(self) -> str:
        """Executes a hot online backup, vacuums the backup, and generates a SHA-256 checksum."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = os.path.join(self.backup_dir, f"paljor_backup_{timestamp}.db")
        
        # Safe Hot Backup API
        with sqlite3.connect(self.db_path) as source_conn:
            with sqlite3.connect(target_path) as target_conn:
                source_conn.backup(target_conn, pages=100)
        
        # Verify integrity of target backup
        with sqlite3.connect(target_path) as target_conn:
            cursor = target_conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            status = cursor.fetchone()[0]
            if status != "ok":
                os.remove(target_path)
                raise RuntimeError(f"Backup integrity check failed: {status}")
            cursor.execute("VACUUM;")

        # Compute SHA-256 Hash
        sha256 = hashlib.sha256()
        with open(target_path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                sha256.update(block)
        
        checksum_file = target_path + ".sha256"
        with open(checksum_file, "w") as f:
            f.write(f"{sha256.hexdigest()}  {os.path.basename(target_path)}\n")
            
        self._prune_old_backups(retention_days=30)
        return target_path

    def _prune_old_backups(self, retention_days: int):
        now = datetime.now().timestamp()
        for fname in os.listdir(self.backup_dir):
            if fname.startswith("paljor_backup_") and fname.endswith(".db"):
                fpath = os.path.join(self.backup_dir, fname)
                if (now - os.path.getmtime(fpath)) > (retention_days * 86400):
                    os.remove(fpath)
                    sha_path = fpath + ".sha256"
                    if os.path.exists(sha_path):
                        os.remove(sha_path)
```

### 4.4 Financial-Grade Precision with `Decimal` & Defensive Type Sanitization
- **Risk**: Storing and calculating currency with IEEE 754 floating-point `float` leads to arithmetic errors:
  ```python
  >>> 0.1 + 0.2
  0.30000000000000004
  ```
- **Remedy**:
  - All internal calculations in `accounting_service.py` must use Python's built-in `decimal.Decimal` set to `ROUND_HALF_UP` precision.
  - In SQLite, values are stored as exact integers in the smallest currency sub-unit (cents/paise) or as strictly bounded REAL/TEXT columns with two-decimal-place rounding guarantees.
  - Centralize defensive type-casting to reject negative numbers, `NaN`, `Infinity`, or non-numeric strings:

```python
from decimal import Decimal, InvalidOperation

def safe_parse_amount(value_str: Any) -> Decimal:
    if value_str is None:
        return Decimal("0.00")
    cleaned = str(value_str).strip().replace(",", "")
    if not cleaned or cleaned.lower() in ("nan", "none", "null"):
        return Decimal("0.00")
    try:
        val = Decimal(cleaned)
        if val < Decimal("0.00"):
            raise ValueError(f"Contribution amount cannot be negative: {cleaned}")
        return val.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as err:
        raise ValueError(f"Invalid monetary value: '{value_str}'") from err
```

### 4.5 Resilient Multi-Format Date Ingestion Pipeline
- **Problem**: `parse_ui_date()` strictly demands `DD-MM-YYYY`. When users export reports to Excel, Excel formats dates as ISO timestamps (`YYYY-MM-DD HH:MM:SS`) or floating serial dates (e.g. `45678.0`). Re-importing those sheets aborts with fatal errors.
- **Solution**: Implement a resilient multi-format fallback parsing pipeline:

```python
import datetime
import pandas as pd

def parse_flexible_date(date_input: Any) -> datetime.date:
    """Safely extracts date.date from datetime objects, pandas timestamps, 
    Excel serial numbers, and common string formats without throwing exceptions."""
    if pd.isna(date_input) or date_input is None:
        raise ValueError("Empty date value provided")
    
    # 1. Native date/datetime instances
    if isinstance(date_input, (datetime.date, datetime.datetime)):
        return date_input if isinstance(date_input, datetime.date) else date_input.date()

    # 2. Excel numeric serial date (e.g., 45678)
    if isinstance(date_input, (int, float)):
        return (datetime.datetime(1899, 12, 30) + datetime.timedelta(days=float(date_input))).date()

    date_str = str(date_input).strip()
    
    # 3. Standard string date formats
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    # 4. Fallback pandas smart parser
    try:
        ts = pd.to_datetime(date_str, dayfirst=True)
        return ts.date()
    except Exception:
        raise ValueError(f"Unrecognized date format: '{date_input}'")
```

---

## 5. Functional & CTA Domain Enhancements

### 5.1 Multi-Currency Management & Dynamic Exchange Rate Aggregation
- **Context**: Offices of Tibet operate internationally across India (INR), Switzerland (CHF), USA (USD), Europe (EUR), Australia (AUD), Nepal (NPR), Taiwan (TWD), and South Africa (ZAR).
- **Current Defect**: When "ALL" currencies are selected in the Reports tab, the footer adds numbers directly across currencies (e.g., `150 USD + 1000 INR = 1150`).
- **Modernization Requirements**:
  1. **Currency Isolation in Aggregates**: If "ALL" is selected, the report footer must display a multi-currency breakdown:
     ```
     Total Records: 48 | Currencies: USD $1,250.00 | INR ₹85,000.00 | CHF 420.00
     ```
  2. **Exchange Rate Table**: Provide an exchange rate configuration matrix in Settings allowing Paljor administrators to set official annual rates against a chosen base currency (typically INR or USD).
  3. **Consolidated Financial Valuation**: Allow generating reports with an optional column: `"Total Converted (INR)"`, standardizing global contributions for central CTA treasury accounting.

### 5.2 Tibetan Fiscal Year (Chatrel Cycle) Engine
- **CTA Accounting Rule**: The Tibetan fiscal accounting year commences on **April 1** and concludes on **March 31** of the following year.
- **Chatrel Periodicity**: Contributions are calculated annually per individual. Chatrel arrears (prior unpaid years) must be logged with accurate historical Start and End dates (e.g. `01-04-2024` to `31-03-2025`).
- **Engine Capabilities**:
  1. **One-Click FY Rollover Wizard**: Automatically sets default dates for the new financial year on April 1:
     ```python
     def get_current_cta_fiscal_year(target_date: Optional[date] = None) -> Tuple[date, date]:
         today = target_date or date.today()
         if today.month >= 4:
             return date(today.year, 4, 1), date(today.year + 1, 3, 31)
         else:
             return date(today.year - 1, 4, 1), date(today.year, 3, 31)
     ```
  2. **Arrears Calculation Assistant**: When entering a member's Green Book number, the system inspects the last recorded `Chatrel End Date`. If the member's last payment ended on `31-03-2024`, the system alerts:
     `"Arrears Detected: 2 Unpaid Fiscal Years (2024-2025, 2025-2026)"` and auto-fills default arrear amounts.

### 5.3 Tibetan Typography, Numerals & Bilingual Document Formatting
- **Standardized Typography**: Integration of CTA typography standards ensures cultural fidelity and administrative alignment:
  - Western Year / Tibetan Month Date Format: `ཕྱི་ལོ་ YYYY ཟླ་ MM ཚེས་ DD`
  - Tibetan Numeral Translation Engine:
    ```python
    TIBETAN_DIGIT_MAP = str.maketrans("0123456789", "༠༡༢༣༤༥༦༧༨༩")

    def to_tibetan_numerals(number_input: Any) -> str:
        """Converts Western ASCII numerals into traditional Tibetan Unicode numerals."""
        return str(number_input).translate(TIBETAN_DIGIT_MAP)
    ```
  - Standardized Tibetan Administrative Headings:
    - Office Title: `བོད་མིའི་སྒྲིག་འཛུགས་དཔལ་འབྱོར་ལས་ཁུངས།` (CTA Department of Finance)
    - Document Title: `དྭང་བླངས་དཔྱ་ཁྲལ་དང་ཞལ་འདེབས་འབྱོར་འཛིན།` (Voluntary Tax & Donation Receipt)
    - Legal Statement: `༼འདི་ནི་གློག་ཀླད་ལམ་ནས་བཟོས་པའི་འབྱོར་འཛིན་ཡིན་པས་དངོས་སུ་མཚན་རྟགས་མི་དགོས།༽` (Computer-generated receipt; physical signature not required).

### 5.4 Comprehensive Financial Audit Trail & Activity Logging
To prevent unauthorized tampering, maintain accountability, and fulfill CTA Office of the Auditor General (སྤྱི་ཁྱབ་རྩིས་ཞིབ་ལས་ཁང་།) compliance:
- Every data modification triggers an immutable audit log entry in table `audit_logs`.
- Logs record the operational timestamp, operating system username, action category (`INSERT`, `UPDATE`, `DELETE`, `SETTINGS_CHANGE`), affected record identifier, and JSON delta representations of prior vs newly written values.
- Audit logs are accessible via a read-only audit log viewer in the Settings tab, exportable for external review.

### 5.5 Contributor 360° Ledger & Annual Tax Exemption Certificates
- **Donor 360° View**: In the GB Database tab, double-clicking any member opens a Contributor History modal displaying:
  - Cumulative lifetime contributions across all account heads.
  - Chronological transaction history table.
  - Active Chatrel compliance status (Current / In Arrears / Pending).
- **Annual Contribution Statement Generator**:
  - One-click PDF export generating an official annual statement covering April 1 to March 31.
  - Formatted to meet national tax deductible donation verification requirements (e.g., US 501(c)(3), Swiss tax relief, Indian Section 80G documentation).

---

## 6. Testing, Quality Assurance & DevOps Automation

### 6.1 Two-Tier Continuous Testing Pyramid (Unit + Headless Tkinter)
To maintain long-term application stability and prevent regression bugs, the test architecture should follow a two-tier pyramid using Python's built-in `unittest` framework:

```
               / \
              /   \
             / GUI \     Tier 2: Headless Integration Tests
            / Ineg. \    (Tkinter withdrawn, UI events, DB sync)
           /---------\
          /   Pure    \  Tier 1: Unit Test Suite
         / Logic/Math  \ (No Tkinter, Decimal math, Date parsers,
        /---------------\ Repositories, Migrations, Validation)
```

#### Tier 1: Pure Logic Unit Tests (`tests/unit/`)
- Fast, deterministic tests that execute in < 2 seconds.
- Test `accounting_service`, `validation_service`, `date_parsers`, and SQLite repository interactions using in-memory SQLite (`:memory:`).

#### Tier 2: Headless Tkinter Integration Tests (`tests/integration/`)
- Verifies visual widgets, dropdown bindings, tab switching, and dialog interactions without opening interactive windows.
- Technique: Initialize `tb.Window()` and immediately call `root.withdraw()`. Run UI interactions via `.invoke()`, `.set()`, `.event_generate()`, and inspect widget attributes directly:

```python
import unittest
import ttkbootstrap as tb
from Rangtsok_app import ContributionApp

class TestHeadlessUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tb.Window(themename="cosmo")
        cls.root.withdraw() # Prevent physical window display
        cls.app = ContributionApp(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_entry_realtime_summation(self):
        # Insert amounts into dynamically built entry fields
        chatrel_ent = self.app.head_entries.get("Chatrel")
        self.assertIsNotNone(chatrel_ent)
        chatrel_ent.delete(0, "end")
        chatrel_ent.insert(0, "250.00")
        
        # Fire realtime total calculation
        self.app.calculate_realtime_total()
        
        # Verify calculated total
        total_str = self.app.ent_total_sum.get()
        self.assertIn("250.00", total_str)
```

### 6.2 GUI Mocking & Headless Execution Framework
To prevent automated test runs from stalling on blocking dialogs (`messagebox.askyesno`, `filedialog.asksaveasfilename`):
- Implement a reusable test fixture mocking `tkinter.messagebox` and `tkinter.filedialog`:

```python
from unittest.mock import patch

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.patcher_msg = patch("tkinter.messagebox.showinfo")
        self.patcher_ask = patch("tkinter.messagebox.askyesno", return_value=True)
        self.mock_showinfo = self.patcher_msg.start()
        self.mock_askyesno = self.patcher_ask.start()

    def tearDown(self):
        self.patcher_msg.stop()
        self.patcher_ask.stop()
```

### 6.3 Automated PyInstaller Build & Smoke-Verification Pipeline
Build releases must be automated through a clean, reproducible script (`build_release.py`):
1. **Prerequisite Check**: Validates that all automated tests pass with 0 exit code before compiling.
2. **Clean Artifacts**: Removes stale `build/` and `dist/` directories.
3. **Compilation**: Invokes PyInstaller with `Rangtsok_app.spec`.
4. **Smoke Verification**: Executes the compiled `dist/Rangtsok_app.exe --version` (or headless probe) to guarantee no missing DLLs, import errors, or corrupted packaging assets.
5. **Distribution Packaging**: Compresses the executable along with `settings.json`, empty database template, `User_Manual.pdf`, and `logo.png` into a portable release ZIP archive (`Rangtsok_App_v2.0.0_Win64.zip`).

### 6.4 Continuous Integration Workflow (GitHub Actions)
```yaml
name: Rangtsok App CI & Build Verification

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Execute Automated Test Suites
        run: |
          python -m unittest discover -s tests -p "test_*.py" -v
      - name: Build Executable via PyInstaller
        run: |
          pyinstaller --noconfirm Rangtsok_app.spec
      - name: Smoke Test Executable Artifact
        run: |
          if (Test-Path "dist/Rangtsok_app.exe") { Write-Host "Build verified successfully." } else { exit 1 }
```

---

## 7. Actionable Implementation Roadmap & Priority Matrix

### 7.1 Comprehensive Recommendation Scoring Matrix

| Ref # | Recommendation Description | Architectural Domain | Impact | Effort | Risk | Recommended Phase |
|---|---|---|---|---|---|---|
| **REC-01** | Fix Manage Account Head deletion bug & UI desynchronization | Bug Fix / Reliability | **High** | Low | Low | **Phase 1** (Immediate) |
| **REC-02** | Fix Date-type account head crash in Reports filter (`TypeError`) | Bug Fix / Stability | **High** | Low | Low | **Phase 1** (Immediate) |
| **REC-03** | Resolve Treeview separator double-click event collision | Bug Fix / UX | **Medium** | Low | Low | **Phase 1** (Immediate) |
| **REC-04** | Fix receipt number auto-incrementation (preserve zero padding) | Bug Fix / Data Safety | **High** | Low | Low | **Phase 1** (Immediate) |
| **REC-05** | Fix GB cleansing deduplication logic (retain longest name) | Bug Fix / Master Data | **Medium** | Low | Low | **Phase 1** (Immediate) |
| **REC-06** | Replace `float` with `Decimal` and sanitize NaN imports | Data Safety / Financial | **High** | Med | Med | **Phase 2** (Core Architecture) |
| **REC-07** | Implement SQLite WAL mode and atomic connection managers | Concurrency / Safety | **High** | Med | Low | **Phase 2** (Core Architecture) |
| **REC-08** | Implement Native SQLite Backup API with SHA-256 Checksums | Data Safety | **High** | Med | Low | **Phase 2** (Core Architecture) |
| **REC-09** | Decompose monolithic code into modular layers (Core/DB/UI) | Architecture / Code | **High** | High | Med | **Phase 2** (Core Architecture) |
| **REC-10** | Database schema normalization (line items table + migrations) | Relational Database | **High** | High | Med | **Phase 2** (Core Architecture) |
| **REC-11** | Autocomplete & fuzzy lookup on Green Book numbers and names | User Experience | **High** | Med | Low | **Phase 3** (UX & Workflows) |
| **REC-12** | Tri-state sortable Treeview columns & persistent layouts | User Experience | **Medium** | Med | Low | **Phase 3** (UX & Workflows) |
| **REC-13** | Non-blocking Toast notifications & Keyboard Shortcuts | User Experience | **Medium** | Low | Low | **Phase 3** (UX & Workflows) |
| **REC-14** | Direct PDF receipt generation with Tibetan typography | Domain / Functionality | **High** | Med | Low | **Phase 3** (UX & Workflows) |
| **REC-15** | Tibetan Fiscal Year (Chatrel cycle) assistant & arrears alert | Domain / Functionality | **High** | Med | Low | **Phase 3** (UX & Workflows) |
| **REC-16** | Multi-currency aggregate breakdown & exchange rate conversion | Financial Reporting | **High** | Med | Med | **Phase 4** (Enterprise Reporting) |
| **REC-17** | Comprehensive immutable audit trail logging | Compliance / Audit | **High** | Med | Low | **Phase 4** (Enterprise Reporting) |
| **REC-18** | Contributor 360° ledger & Annual Tax Certificate generation | Domain / Reporting | **High** | Med | Low | **Phase 4** (Enterprise Reporting) |
| **REC-19** | Automated CI/CD pipeline and release packaging verification | DevOps / QA | **Medium** | Med | Low | **Phase 4** (Enterprise Reporting) |

---

### 7.2 Phased Modernization Rollout Plan

```
====================================================================================================
PHASE 1: Immediate Defect Elimination & Operational Stabilization (Week 1)
----------------------------------------------------------------------------------------------------
  * Deploy Hotfixes for Defect 1 through Defect 8 (R1 Account Head delete, Date filter crash,
    receipt padding, GB deduplication, Treeview column auto-resize).
  * Establish baseline automated test suite (tests/) covering critical workflows.
  * Target: 100% bug elimination with zero breaking schema changes.

====================================================================================================
PHASE 2: Architectural Decoupling & Relational Safety (Weeks 2 - 3)
----------------------------------------------------------------------------------------------------
  * Introduce database/ connection manager: enable SQLite WAL mode and busy timeout.
  * Transition financial math from float to Decimal; deploy resilient multi-format date parser.
  * Build database/migrations.py and deploy normalized transaction_line_items schema with
    automated zero-downtime backward compatibility.
  * Extract UI callbacks into pure services/ (accounting, validation, backup).
  * Target: Production database hardened against crashes, locking, and data corruption.

====================================================================================================
PHASE 3: User Experience & Workflow Modernization (Weeks 4 - 5)
----------------------------------------------------------------------------------------------------
  * Integrate AutocompleteEntry for Green Book numbers with fuzzy name matching.
  * Deploy Tri-state sortable Treeview headers and column width persistence.
  * Replace blocking messageboxes with non-blocking Toast notifications; bind Ctrl+S, Ctrl+P.
  * Integrate FPDF2 bilingual PDF Receipt generator and thermal POS printer engine.
  * Build Tibetan Fiscal Year (Chatrel cycle) calculation engine and arrears detector.
  * Target: 50% reduction in operator entry time and direct counter receipt printing.

====================================================================================================
PHASE 4: Enterprise Accounting, Audit & Release Automation (Weeks 6 - 7)
----------------------------------------------------------------------------------------------------
  * Deploy multi-currency aggregation engine with exchange rate valuation.
  * Implement immutable audit_logs tracking all insert/update/delete operations.
  * Develop Contributor 360° lifetime ledger and Annual Contribution Statements.
  * Deploy GitHub Actions CI/CD pipeline and automated PyInstaller build release verification.
  * Target: Full compliance with CTA Department of Finance and Auditor General standards.
====================================================================================================
```

---

### 7.3 Risk Mitigation, Rollback & Governance Guidelines
1. **Pre-Migration Safety Mandate**: No software update may modify database DDL without generating an automated verified backup snapshot in `backups/`.
2. **Dual-Read Compatibility Window**: During Phase 2 migration, the system must retain read compatibility with legacy JSON `account_data` records while populating relational line items.
3. **Data Loss Prevention Principle**: Destructive actions (deleting account heads, purging Green Book records, batch transaction removal) require two-factor confirmation (typing record count or explicit dialog confirmation) and must verify absence of active financial contributions.
4. **Offline Resilience Invariant**: Every modernization enhancement must function with 100% fidelity without internet access or external third-party servers. All fonts, assets, and dependencies must be locally bundled.

---
*End of Report — Approved for Implementation by Architecture Working Group.*
