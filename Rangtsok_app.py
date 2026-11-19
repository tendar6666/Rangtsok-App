import csv
import datetime
import json
import os
import re
import sys


def resource_path(relative_path):
    """Resolve resource paths cleanly for both PyInstaller (--onefile) bundles and source runs."""
    if hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(bundled):
            return bundled
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(script_dir, relative_path)
    if os.path.exists(local):
        return local
    return relative_path

class ToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
        self.tw = None

    def enter(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}""")
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#333333", foreground="white", relief='solid', borderwidth=1,
                       font=("Segoe UI", 9, "normal"), padx=5, pady=5)
        label.pack()

    def close(self, event=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None

import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import ttkbootstrap as tb
from ttkbootstrap.widgets.dateentry import DateEntry as TBDateEntry
from PIL import Image, ImageTk, ImageEnhance

class DateEntry(ttk.Frame):
    def __init__(self, master, width=12, date_pattern="dd-mm-yyyy", **kwargs):
        super().__init__(master)
        self.de = TBDateEntry(self, bootstyle="primary", width=width, date_format="%d-%m-%Y")
        self.de.pack(fill="both", expand=True)

    def get(self):
        return self.de.entry.get()

    def set_date(self, date_obj):
        self.de.entry.delete(0, tk.END)
        self.de.entry.insert(0, date_obj.strftime("%d-%m-%Y"))

    def delete(self, first, last=None):
        self.de.entry.delete(first, last)

    def insert(self, index, string):
        self.de.entry.insert(index, string)

    def bind(self, sequence=None, func=None, add=None):
        return self.de.entry.bind(sequence, func, add)

# --- CONFIGURATION & DATABASE SETUP ---
SETTINGS_FILE = "settings.json"
DB_FILE = "paljor_contribution.db"

DEFAULT_SETTINGS = {
    "office_name": "Office of Tibet",
    "from_date": datetime.date.today().strftime("%d-%m-%Y"),
    "to_date": datetime.date.today().strftime("%d-%m-%Y"),
    "theme": "cosmo",
    "enable_aadhaar": True,
    "currency": "INR",
    "currencies": ["AUD", "CHF", "INR", "NPR", "TWD", "USD", "ZAR"],
    "countries": {
        "India": ["Dharamshala", "Delhi", "Bylakuppe", "Mundgod", "Dehradun"],
        "Switzerland": ["Geneva", "Zurich"],
        "United States": ["New York", "Washington DC", "California"],
    },
    "account_heads": [
        {"head": "Chatrel", "type": "Amount", "default": 150},
        {"head": "Chatrel Start Date", "type": "Date", "default": "01-04-2026"},
        {"head": "Chatrel End Date", "type": "Date", "default": "31-03-2027"},
        {"head": "Meal Strike", "type": "Amount", "default": 50},
        {"head": "Salary Contribution", "type": "Amount", "default": ""},
        {"head": "Salary Start Date", "type": "Date", "default": "01-04-2026"},
        {"head": "Salary End Date", "type": "Date", "default": "31-03-2027"},
        {"head": "Business Contribution", "type": "Amount", "default": ""},
        {"head": "Arrear", "type": "Amount", "default": ""},
        {"head": "Arear Start Date", "type": "Date", "default": "01-04-2025"},
        {"head": "Arrear End Date", "type": "Date", "default": "31-03-2026"},
        {"head": "Donation", "type": "Amount", "default": ""},
        {"head": "TsangKhe", "type": "Amount", "default": ""}
    ],
}


def parse_ui_date(date_val):
    """Convert DD-MM-YYYY or ISO YYYY-MM-DD to YYYY-MM-DD for accurate SQLite range sorting."""
    if date_val is None:
        return None
    if hasattr(date_val, "strftime"):
        return date_val.strftime("%Y-%m-%d")
    d_str = str(date_val).strip()
    if not d_str or d_str.lower() in ("nan", "nat", "none"):
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(d_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    try:
        ts = pd.to_datetime(d_str, dayfirst=True, errors="coerce")
        if pd.notna(ts):
            return ts.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def format_db_date(yyyy_mm_dd):
    """Convert YYYY-MM-DD back to DD-MM-YYYY for UI display."""
    try:
        return datetime.datetime.strptime(yyyy_mm_dd, "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        return yyyy_mm_dd


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=4)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "account_heads" in data and data["account_heads"]:
                if isinstance(data["account_heads"][0], str):
                    data["account_heads"] = [{"head": h, "default": 0.0} for h in data["account_heads"]]
            for k, v in DEFAULT_SETTINGS.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)


def clean_aadhaar(val):
    """Sanitize Aadhaar number input (handles NaN, Excel '.0' floats, spaces/hyphens)."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "nat"):
        return ""
    # Strip trailing .0 produced when Excel/pandas reads numeric cells as float
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".")[0]
    # Normalize spaces/hyphens when the value is purely numeric with separators
    stripped = re.sub(r"[\s\-]+", "", s)
    if stripped.isdigit():
        return stripped
    return s


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS gb_database (
            gb_number TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            aadhaar_number TEXT DEFAULT ''
        )
    """
    )
    # Safe migration for existing databases that predate aadhaar_number
    cursor.execute("PRAGMA table_info(gb_database)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if "aadhaar_number" not in existing_cols:
        cursor.execute("ALTER TABLE gb_database ADD COLUMN aadhaar_number TEXT DEFAULT ''")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT NOT NULL,
            gb_number TEXT NOT NULL,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            place TEXT NOT NULL,
            currency TEXT NOT NULL,
            tx_date TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            account_data TEXT NOT NULL,
            total_amount REAL NOT NULL
        )
    """
    )
    # Performance indexes for fast lookups, filtering, and reporting on large datasets
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(tx_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_gb ON transactions(gb_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_receipt ON transactions(receipt_no)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gb_lower ON gb_database(LOWER(gb_number))")
    conn.commit()
    conn.close()


# --- MAIN APPLICATION CLASS ---
class ContributionApp:

    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        init_db()

        self.current_edit_id = None
        self._lookup_after_id = None
        self._last_looked_up_gb = None
        self._recent_tx_ids = []

        self.update_title()
        self.root.geometry("1200x850")
        self.root.minsize(850, 600)
        
        # Maximize the window on startup
        try:
            self.root.state("zoomed")
        except Exception:
            pass

        # Set App Window & Taskbar Icon (works in both dev mode and bundled PyInstaller .exe)
        self._hicon_small = None
        self._hicon_big = None
        self._apply_window_icon()
        # Re-apply after initial window mapping/maximize so Windows 11 taskbar & title bar always lock it in
        try:
            self.root.after(150, self._apply_window_icon)
        except Exception:
            pass

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_entry = ttk.Frame(self.notebook)
        self.tab_db = ttk.Frame(self.notebook)
        self.tab_reports = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_entry, text="📝 Entry Form")
        self.notebook.add(self.tab_db, text="📇 GB Database")
        self.notebook.add(self.tab_reports, text="📊 Reports & Filters")
        self.notebook.add(self.tab_settings, text="⚙️ Settings")

        self.build_settings_tab()
        self.build_db_tab()
        self.build_entry_tab()
        self.build_reports_tab()

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.root.bind("<Control-s>", self._on_ctrl_s)
        self.root.bind("<Control-S>", self._on_ctrl_s)
        self.apply_aadhaar_visibility()

    def _on_ctrl_s(self, event=None):
        """Quick keyboard shortcut (Ctrl+S) to save when on the Entry Form tab."""
        try:
            if self.notebook.index(self.notebook.select()) == 0:
                self.save_entry()
                return "break"
        except Exception:
            pass

    def is_aadhaar_enabled(self):
        return bool(self.settings.get("enable_aadhaar", True))

    def apply_aadhaar_visibility(self):
        """Show or hide Aadhaar Number UI elements across Entry Form and GB Database."""
        enabled = self.is_aadhaar_enabled()
        if hasattr(self, "lbl_aadhaar") and hasattr(self, "ent_aadhaar"):
            if enabled:
                self.lbl_aadhaar.grid()
                self.ent_aadhaar.grid()
            else:
                self.lbl_aadhaar.grid_remove()
                self.ent_aadhaar.grid_remove()
        if hasattr(self, "db_tree"):
            if enabled:
                self.db_tree.configure(displaycolumns=("gb", "name", "aadhaar"))
            else:
                self.db_tree.configure(displaycolumns=("gb", "name"))

    def update_title(self):
        office = self.settings.get("office_name", "Office of Tibet")
        self.root.title(f"Voluntary Contribution Recording System | {office}")

    def _apply_window_icon(self):
        """Apply logo.ico to both the top-left window title bar and the Windows taskbar."""
        try:
            ico_path = os.path.abspath(resource_path("logo.ico"))
            if not os.path.exists(ico_path):
                return

            # Set Tk iconbitmap for child dialogs & standard Tk windows
            try:
                self.root.wm_iconbitmap(ico_path)
            except Exception:
                pass

            # On Windows, explicitly set Win32 ICON_SMALL (title bar) and ICON_BIG (taskbar)
            if sys.platform == "win32":
                import ctypes
                from ctypes import wintypes

                u32 = ctypes.windll.user32
                u32.GetParent.argtypes = [wintypes.HWND]
                u32.GetParent.restype = wintypes.HWND
                u32.LoadImageW.argtypes = [
                    wintypes.HINSTANCE,
                    wintypes.LPCWSTR,
                    wintypes.UINT,
                    ctypes.c_int,
                    ctypes.c_int,
                    wintypes.UINT,
                ]
                u32.LoadImageW.restype = wintypes.HANDLE
                u32.SendMessageW.argtypes = [
                    wintypes.HWND,
                    wintypes.UINT,
                    wintypes.WPARAM,
                    wintypes.LPARAM,
                ]
                u32.SendMessageW.restype = ctypes.c_ssize_t

                self.root.update_idletasks()
                hwnd = u32.GetParent(self.root.winfo_id()) or self.root.winfo_id()

                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1

                sm_w = u32.GetSystemMetrics(49) or 16  # SM_CXSMICON
                sm_h = u32.GetSystemMetrics(50) or 16  # SM_CYSMICON
                big_w = u32.GetSystemMetrics(11) or 32  # SM_CXICON
                big_h = u32.GetSystemMetrics(12) or 32  # SM_CYICON

                if not self._hicon_small:
                    self._hicon_small = u32.LoadImageW(None, ico_path, IMAGE_ICON, sm_w, sm_h, LR_LOADFROMFILE)
                if not self._hicon_big:
                    self._hicon_big = u32.LoadImageW(None, ico_path, IMAGE_ICON, big_w, big_h, LR_LOADFROMFILE)

                if self._hicon_small:
                    u32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, self._hicon_small)
                if self._hicon_big:
                    u32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, self._hicon_big)
        except Exception as e:
            print("Logo load error:", e)

    def _get_heads_signature(self):
        return tuple(
            (h.get("head"), h.get("type", "Amount"), h.get("default", ""))
            for h in self.settings.get("account_heads", [])
        )

    def on_tab_change(self, event):
        self.update_title()
        
        # Only refresh the specific tab that was clicked to prevent massive lag
        selected_tab = self.notebook.index(self.notebook.select())
        
        if selected_tab == 0:  # Entry Form
            self.refresh_entry_dropdowns()
            self.apply_aadhaar_visibility()
            if not getattr(self, "current_edit_id", None):
                if getattr(self, "_heads_signature", None) != self._get_heads_signature():
                    self.build_dynamic_account_inputs()
            self.refresh_recent_entries()
        elif selected_tab == 1:  # GB Database
            self.apply_aadhaar_visibility()
            self.refresh_db_table()
        elif selected_tab == 2:  # Reports
            self.refresh_report_filters()

    # =========================================================================
    # TAB 1: ENTRY FORM
    # =========================================================================
    def build_entry_tab(self):
        frame_top = ttk.LabelFrame(self.tab_entry, text="Transaction Details", padding=10)
        frame_top.pack(fill="x", padx=15, pady=5)

        ttk.Label(frame_top, text="Receipt Number:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ent_receipt = ttk.Entry(frame_top, width=15)
        self.ent_receipt.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame_top, text="Country:").grid(row=0, column=2, sticky="w", padx=10, pady=5)
        self.cmb_country = ttk.Combobox(frame_top, state="readonly", width=18)
        self.cmb_country.grid(row=0, column=3, padx=5, pady=5)
        self.cmb_country.bind("<<ComboboxSelected>>", self.on_country_select)

        ttk.Label(frame_top, text="Place:").grid(row=0, column=4, sticky="w", padx=10, pady=5)
        self.cmb_place = ttk.Combobox(frame_top, state="readonly", width=18)
        self.cmb_place.grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(frame_top, text="Currency Selection:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.cmb_entry_currency = ttk.Combobox(frame_top, state="readonly", width=15)
        self.cmb_entry_currency.grid(row=1, column=1, padx=5, pady=5)
        self.cmb_entry_currency.bind("<<ComboboxSelected>>", self.on_entry_currency_change)

        ttk.Label(frame_top, text="Transaction Date:").grid(row=1, column=2, sticky="w", padx=10, pady=5)
        self.ent_tx_date = DateEntry(
            frame_top, width=15, background="darkblue", foreground="white", borderwidth=2, date_pattern="dd-mm-yyyy"
        )
        self.ent_tx_date.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(frame_top, text="FY Period From:").grid(row=1, column=4, sticky="w", padx=10, pady=5)
        self.ent_entry_fdate = DateEntry(frame_top, width=12, background="darkblue", foreground="white", date_pattern="dd-mm-yyyy")
        self.ent_entry_fdate.grid(row=1, column=5, padx=5, pady=5)
        self.ent_entry_fdate.bind("<<DateEntrySelected>>", self.sync_period_from_entry)
        self.ent_entry_fdate.bind("<FocusOut>", self.sync_period_from_entry)

        ttk.Label(frame_top, text="To:").grid(row=1, column=6, sticky="w", padx=10, pady=5)
        self.ent_entry_tdate = DateEntry(frame_top, width=12, background="darkblue", foreground="white", date_pattern="dd-mm-yyyy")
        self.ent_entry_tdate.grid(row=1, column=7, padx=5, pady=5)
        self.ent_entry_tdate.bind("<<DateEntrySelected>>", self.sync_period_from_entry)
        self.ent_entry_tdate.bind("<FocusOut>", self.sync_period_from_entry)

        if self.settings.get("from_date"):
            try:
                self.ent_entry_fdate.set_date(datetime.datetime.strptime(self.settings.get("from_date"), "%d-%m-%Y"))
                self.ent_entry_tdate.set_date(datetime.datetime.strptime(self.settings.get("to_date"), "%d-%m-%Y"))
            except Exception:
                pass

        self.lbl_edit_warning = ttk.Label(
            frame_top, text="", font=("Arial", 10, "bold"), foreground="red"
        )
        self.lbl_edit_warning.grid(row=2, column=0, columnspan=8, padx=10, pady=5, sticky="w")

        frame_gb = ttk.LabelFrame(self.tab_entry, text="Green Book Holder Verification", padding=10)
        frame_gb.pack(fill="x", padx=15, pady=5)

        ttk.Label(frame_gb, text="GB Number:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ent_gb = ttk.Entry(frame_gb, width=15)
        self.ent_gb.grid(row=0, column=1, padx=5, pady=5)
        self.ent_gb.bind("<KeyRelease>", self._schedule_auto_lookup)
        self.ent_gb.bind("<FocusOut>", self._on_gb_focus_out)
        self.ent_gb.bind("<Return>", self._on_gb_enter)

        ttk.Label(frame_gb, text="Full Name:").grid(row=0, column=2, sticky="w", padx=(12, 5), pady=5)
        self.ent_name = ttk.Entry(frame_gb, width=26)
        self.ent_name.grid(row=0, column=3, padx=5, pady=5)
        self.ent_name.bind("<KeyRelease>", self._on_gb_details_modified)

        self.lbl_aadhaar = ttk.Label(frame_gb, text="Aadhaar Number:")
        self.lbl_aadhaar.grid(row=0, column=4, sticky="w", padx=(12, 5), pady=5)
        self.ent_aadhaar = ttk.Entry(frame_gb, width=18)
        self.ent_aadhaar.grid(row=0, column=5, padx=5, pady=5)
        self.ent_aadhaar.bind("<KeyRelease>", self._on_gb_details_modified)

        self.lbl_gb_status = ttk.Label(frame_gb, text="", font=("Arial", 9, "italic"))
        self.lbl_gb_status.grid(row=0, column=6, padx=10, pady=5, sticky="w")

        # Middle split container: Left = Contribution Amounts, Right = Centered Recent Entries
        frame_body = ttk.Frame(self.tab_entry)
        frame_body.pack(fill="x", expand=False, padx=15, pady=5)

        self.frame_heads = ttk.LabelFrame(frame_body, text="Contribution Amounts", padding=10)
        self.frame_heads.pack(side="left", anchor="nw", fill="none", expand=False, padx=(0, 12))

        self.head_entries = {}
        self.build_dynamic_account_inputs()

        # Spacer container fills the area between Contribution Amounts and the right window edge
        frame_recent_container = ttk.Frame(frame_body)
        frame_recent_container.pack(side="left", fill="both", expand=True, padx=(20, 10))

        self.frame_recent = ttk.LabelFrame(frame_recent_container, text="Recent Entries (Last 10)", padding=10)
        self.frame_recent.pack(anchor="n", fill="none", expand=False)

        recent_table_wrap = ttk.Frame(self.frame_recent)
        recent_table_wrap.pack(fill="none", expand=False)

        self.recent_tree = ttk.Treeview(
            recent_table_wrap,
            columns=("receipt", "gb", "name", "total"),
            show="headings",
            height=10,
        )
        self.recent_tree.heading("receipt", text="Receipt No")
        self.recent_tree.heading("gb", text="GB Number")
        self.recent_tree.heading("name", text="Name")
        self.recent_tree.heading("total", text="Total Amount")

        self.recent_tree.column("receipt", width=100, minwidth=95, anchor="center", stretch=False)
        self.recent_tree.column("gb", width=115, minwidth=105, anchor="center", stretch=False)
        self.recent_tree.column("name", width=210, minwidth=160, anchor="w", stretch=False)
        self.recent_tree.column("total", width=125, minwidth=115, anchor="e", stretch=False)

        recent_xscroll = ttk.Scrollbar(recent_table_wrap, orient="horizontal", command=self.recent_tree.xview)
        self.recent_tree.configure(xscrollcommand=recent_xscroll.set)

        self.recent_tree.pack(side="top", fill="x", expand=False)
        recent_xscroll.pack(side="bottom", fill="x")
        self.recent_tree.bind("<Double-1>", self.on_recent_double_click)

        ttk.Label(
            self.frame_recent,
            text="💡 Showing latest 10 entries. Double-click any row to edit.",
            font=("Segoe UI", 8, "italic"),
            foreground="gray",
        ).pack(anchor="w", pady=(5, 0))

        frame_actions = ttk.Frame(self.tab_entry)
        frame_actions.pack(fill="x", padx=15, pady=10)

        self.btn_save_tx = ttk.Button(
            frame_actions, text="💾 Save Contribution Entry", command=self.save_entry
        )
        self.btn_save_tx.pack(side="left", padx=5)

        btn_clear = ttk.Button(frame_actions, text="🔄 Clear Form", command=self.clear_entry_form)
        btn_clear.pack(side="left", padx=5)

        ttk.Label(
            frame_actions,
            text="⚡ Tip: Type GB Number for instant auto-lookup • Name/Aadhaar auto-update on Save • Press Ctrl+S to Save",
            font=("Segoe UI", 8, "italic"),
            foreground="gray",
        ).pack(side="left", padx=15)

        self.refresh_entry_dropdowns()
        self.auto_set_next_receipt()
        self.refresh_recent_entries()
        self.apply_aadhaar_visibility()

    def refresh_entry_dropdowns(self):
        currencies = self.settings.get("currencies", [])
        self.cmb_entry_currency["values"] = currencies
        if currencies and not self.cmb_entry_currency.get():
            default_curr = self.settings.get("currency", "")
            self.cmb_entry_currency.set(default_curr if default_curr in currencies else currencies[0])

        countries = list(self.settings.get("countries", {}).keys())
        self.cmb_country["values"] = countries
        if countries and not self.cmb_country.get():
            self.cmb_country.set(countries[0])
            self.on_country_select()

    def on_country_select(self, event=None):
        selected_country = self.cmb_country.get()
        places = self.settings.get("countries", {}).get(selected_country, [])
        self.cmb_place["values"] = places
        if places:
            self.cmb_place.set(places[0])
        else:
            self.cmb_place.set("")

    def sync_period_from_entry(self, event=None):
        if not hasattr(self, "_syncing"): self._syncing = False
        if self._syncing: return
        self._syncing = True
        self.settings["from_date"] = self.ent_entry_fdate.get().strip()
        self.settings["to_date"] = self.ent_entry_tdate.get().strip()
        save_settings(self.settings)
        try:
            if hasattr(self, "set_fdate"):
                self.set_fdate.set_date(datetime.datetime.strptime(self.settings["from_date"], "%d-%m-%Y"))
                self.set_tdate.set_date(datetime.datetime.strptime(self.settings["to_date"], "%d-%m-%Y"))
            if hasattr(self, "flt_from_date"):
                self.flt_from_date.set_date(datetime.datetime.strptime(self.settings["from_date"], "%d-%m-%Y"))
                self.flt_to_date.set_date(datetime.datetime.strptime(self.settings["to_date"], "%d-%m-%Y"))
        except Exception:
            pass
        self._syncing = False

    def get_safe_currency_symbol(self, val=None):
        if val is not None:
            parts = str(val).split()
            if parts:
                return parts[0]
        setting_val = self.settings.get("currency") if hasattr(self, "settings") and self.settings else "₹"
        setting_parts = (setting_val or "").split()
        return setting_parts[0] if setting_parts else "₹"

    def on_entry_currency_change(self, event=None):
        curr_symbol = self.get_safe_currency_symbol(self.cmb_entry_currency.get())
        for head_name, (lbl, ent, head_type) in self.head_entries.items():
            if head_type == "Amount":
                lbl.config(text=f"{head_name} ({curr_symbol}):")
            else:
                lbl.config(text=f"{head_name}:")
        self.lbl_total_title.config(text=f"TOTAL AMOUNT ({curr_symbol}):")

    def build_dynamic_account_inputs(self):
        self._heads_signature = self._get_heads_signature()
        for widget in self.frame_heads.winfo_children():
            widget.destroy()

        self.head_entries.clear()
        curr_symbol = self.get_safe_currency_symbol(self.cmb_entry_currency.get())

        row, col = 0, 0
        is_first = True
        
        for item in self.settings.get("account_heads", []):
            head = item["head"]
            head_type = item.get("type", "Amount")
            default_val = item.get("default", "")
            if head_type == "Amount" and isinstance(default_val, float):
                default_val = int(default_val) if default_val.is_integer() else default_val

            if head_type == "Amount":
                if not is_first:
                    row += 1
                col = 0
            else:
                if not is_first:
                    if col < 4:
                        col += 2
                    else:
                        row += 1
                        col = 0
            is_first = False

            if head_type == "Amount":
                lbl = ttk.Label(self.frame_heads, text=f"{head} ({curr_symbol}):")
                lbl.grid(row=row, column=col, sticky="w", padx=10, pady=8)
                ent = ttk.Entry(self.frame_heads, width=15)
                ent.grid(row=row, column=col + 1, padx=5, pady=8)
                ent.insert(0, str(default_val))
                ent.bind("<KeyRelease>", self.calculate_realtime_total)
            else:
                lbl = ttk.Label(self.frame_heads, text=f"{head}:")
                lbl.grid(row=row, column=col, sticky="w", padx=10, pady=8)
                ent = DateEntry(self.frame_heads, width=12, background="darkblue", foreground="white", borderwidth=2, date_pattern="dd-mm-yyyy")
                ent.grid(row=row, column=col + 1, padx=5, pady=8)
                if default_val:
                    try:
                        ent.set_date(datetime.datetime.strptime(str(default_val), "%d-%m-%Y"))
                    except Exception:
                        pass
                else:
                    ent.set_date(datetime.date.today())

            self.head_entries[head] = (lbl, ent, head_type)

        sep = ttk.Separator(self.frame_heads, orient="horizontal")
        sep.grid(row=row + 1, column=0, columnspan=6, sticky="ew", pady=10)

        self.lbl_total_title = ttk.Label(
            self.frame_heads, text=f"TOTAL AMOUNT ({curr_symbol}):", font=("Arial", 11, "bold")
        )
        self.lbl_total_title.grid(row=row + 2, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        self.ent_total_sum = ttk.Entry(
            self.frame_heads, width=20, font=("Arial", 11, "bold"), state="readonly"
        )
        self.ent_total_sum.grid(row=row + 2, column=2, columnspan=2, sticky="w", padx=5, pady=5)

        lbl_info_logic = tk.Label(
            self.frame_heads, text="ⓘ How dates work", fg="#007bff", cursor="hand2", font=("Segoe UI", 9, "bold")
        )
        lbl_info_logic.grid(row=row + 2, column=4, columnspan=2, sticky="e", padx=8, pady=5)
        ToolTip(
            lbl_info_logic,
            "Date Logic Explanation:\n\n1. Start/End Dates are auto-filled from your 'FY Period From/To' settings.\n2. If you change a date here, the app assumes you are paying for that specific period.\n3. This allows you to log Back-Arrears or Advance Payments separate from the current FY.\n4. Syncs automatically with the main FY fields at the top!",
        )

        self.calculate_realtime_total()
        
    def calculate_realtime_total(self, event=None):
        total = 0.0
        for lbl, ent, head_type in self.head_entries.values():
            if head_type == "Amount":
                try:
                    val_str = ent.get().strip()
                    total += float(val_str) if val_str else 0.0
                except ValueError:
                    pass

        self.ent_total_sum.config(state="normal")
        self.ent_total_sum.delete(0, tk.END)
        self.ent_total_sum.insert(0, f"{total:,.2f}")
        self.ent_total_sum.config(state="readonly")

    def _schedule_auto_lookup(self, event=None):
        """Debounced live lookup as the user types a GB Number."""
        if event and getattr(event, "keysym", "") in ("Tab", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Return"):
            return
        if self._lookup_after_id:
            try:
                self.root.after_cancel(self._lookup_after_id)
            except Exception:
                pass
            self._lookup_after_id = None
        gb_num = self.ent_gb.get().strip()
        if not gb_num:
            self._last_looked_up_gb = None
            self.lbl_gb_status.config(text="")
            return
        self._lookup_after_id = self.root.after(250, lambda: self.lookup_gb(auto=True))

    def _on_gb_focus_out(self, event=None):
        if self._lookup_after_id:
            try:
                self.root.after_cancel(self._lookup_after_id)
            except Exception:
                pass
            self._lookup_after_id = None
        gb_num = self.ent_gb.get().strip()
        if not gb_num:
            return
        # Only run lookup if this GB number hasn't already been looked up
        if not self._last_looked_up_gb or self._last_looked_up_gb[0] != gb_num.lower():
            self.lookup_gb()

    def _on_gb_enter(self, event=None):
        """Immediate lookup on Enter and smart focus jump for rapid data entry."""
        if self._lookup_after_id:
            try:
                self.root.after_cancel(self._lookup_after_id)
            except Exception:
                pass
            self._lookup_after_id = None
        self.lookup_gb()
        name_val = self.ent_name.get().strip()
        aadhaar_val = self.ent_aadhaar.get().strip() if hasattr(self, "ent_aadhaar") else ""
        if not name_val:
            self.ent_name.focus_set()
        elif self.is_aadhaar_enabled() and not aadhaar_val:
            self.ent_aadhaar.focus_set()
        else:
            # Jump straight to the first Amount input box for fast entry
            for _, ent, h_type in self.head_entries.values():
                if h_type == "Amount":
                    ent.focus_set()
                    ent.selection_range(0, tk.END)
                    break
        return "break"

    def _on_gb_details_modified(self, event=None):
        """Show subtle indicator when Name or Aadhaar is edited so user knows DB will auto-update."""
        gb_num = self.ent_gb.get().strip()
        if not gb_num:
            return
        if self._last_looked_up_gb and self._last_looked_up_gb[0] == gb_num.lower():
            orig_name = self._last_looked_up_gb[1]
            orig_aadhaar = self._last_looked_up_gb[2]
            curr_name = self.ent_name.get().strip()
            curr_aadhaar = clean_aadhaar(self.ent_aadhaar.get()) if hasattr(self, "ent_aadhaar") else orig_aadhaar
            if orig_name:
                if curr_name != orig_name or (self.is_aadhaar_enabled() and curr_aadhaar != orig_aadhaar):
                    self.lbl_gb_status.config(text="✎ Edited (auto-updates DB on Save)", foreground="#d97706")
                else:
                    self.lbl_gb_status.config(text="✓ GB Found", foreground="green")

    def _upsert_gb_record(self, cursor, gb_num, name, aadhaar_val="", update_aadhaar=True):
        """Insert new GB record or automatically update existing GB holder's name & Aadhaar (case-insensitive)."""
        clean_aad = clean_aadhaar(aadhaar_val)
        cursor.execute(
            "SELECT gb_number, name, COALESCE(aadhaar_number, '') FROM gb_database WHERE LOWER(gb_number) = LOWER(?)",
            (gb_num,),
        )
        existing = cursor.fetchone()
        if existing:
            existing_gb, _, existing_aadhaar = existing
            new_aadhaar = clean_aad if update_aadhaar else existing_aadhaar
            cursor.execute(
                "UPDATE gb_database SET name = ?, aadhaar_number = ? WHERE gb_number = ?",
                (name, new_aadhaar, existing_gb),
            )
        else:
            new_aadhaar = clean_aad if update_aadhaar else ""
            cursor.execute(
                "INSERT INTO gb_database (gb_number, name, aadhaar_number) VALUES (?, ?, ?)",
                (gb_num, name, new_aadhaar),
            )

    def lookup_gb(self, event=None, auto=False):
        gb_num = self.ent_gb.get().strip()
        if not gb_num:
            return

        if auto and self._last_looked_up_gb and self._last_looked_up_gb[0] == gb_num.lower():
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, COALESCE(aadhaar_number, '') FROM gb_database WHERE LOWER(gb_number) = LOWER(?)",
            (gb_num,),
        )
        result = cursor.fetchone()
        conn.close()

        self.ent_name.delete(0, tk.END)
        if hasattr(self, "ent_aadhaar"):
            self.ent_aadhaar.delete(0, tk.END)

        if result:
            found_name, found_aadhaar = result[0], result[1] or ""
            self.ent_name.insert(0, found_name)
            if hasattr(self, "ent_aadhaar") and found_aadhaar:
                self.ent_aadhaar.insert(0, found_aadhaar)
            self.lbl_gb_status.config(text="✓ GB Found", foreground="green")
            self._last_looked_up_gb = (gb_num.lower(), found_name, found_aadhaar)
        else:
            self.lbl_gb_status.config(text="★ Data not found — New GB (auto-saves)", foreground="#0d6efd")
            self._last_looked_up_gb = (gb_num.lower(), "", "")

    def update_gb_name(self):
        gb_num = self.ent_gb.get().strip()
        name = self.ent_name.get().strip()
        aadhaar = clean_aadhaar(self.ent_aadhaar.get()) if hasattr(self, "ent_aadhaar") else ""

        if not gb_num or not name:
            messagebox.showwarning("Missing Data", "Both GB Number and Name must be filled.")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        self._upsert_gb_record(cursor, gb_num, name, aadhaar, update_aadhaar=self.is_aadhaar_enabled())
        conn.commit()
        conn.close()

        self._last_looked_up_gb = (gb_num.lower(), name, aadhaar)
        self.lbl_gb_status.config(text="✓ Database Updated", foreground="blue")
        self.refresh_db_table()

    def refresh_recent_entries(self, limit=10):
        """Refresh the Recent Entries panel on the Entry Form tab."""
        if not hasattr(self, "recent_tree"):
            return
        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)
        self._recent_tx_ids = []

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, receipt_no, gb_number, name, total_amount, currency FROM transactions ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()

        for idx, (tx_id, rec_no, gb_num, name, total_amt, curr) in enumerate(rows):
            self._recent_tx_ids.append(tx_id)
            curr_sym = self.get_safe_currency_symbol(curr)
            amt_display = f"{float(total_amt or 0.0):,.2f} {curr_sym}".strip()
            self.recent_tree.insert("", "end", iid=str(idx), values=(rec_no, gb_num, name, amt_display))

        self._auto_size_recent_columns()

    def _auto_size_recent_columns(self):
        """Auto-size Recent Entries columns to fit headers and displayed values cleanly."""
        if not hasattr(self, "recent_tree"):
            return
        try:
            import tkinter.font as tkFont
            font = tkFont.nametofont("TkDefaultFont")
        except Exception:
            return

        min_widths = {"receipt": 100, "gb": 115, "name": 210, "total": 125}
        max_widths = {"receipt": 150, "gb": 170, "name": 280, "total": 170}

        for col_id in ("receipt", "gb", "name", "total"):
            header_text = str(self.recent_tree.heading(col_id, "text"))
            best_w = max(min_widths[col_id], font.measure(header_text) + 28)
            for item in self.recent_tree.get_children(""):
                val = str(self.recent_tree.set(item, col_id))
                w = font.measure(val) + 26
                if w > best_w:
                    best_w = w
            best_w = min(best_w, max_widths[col_id])
            self.recent_tree.column(col_id, width=best_w)

    def on_recent_double_click(self, event=None):
        """Double-click a recent entry to load it into the Entry Form for quick editing."""
        if not hasattr(self, "recent_tree"):
            return
        if event and hasattr(event, "x") and hasattr(event, "y"):
            region = self.recent_tree.identify_region(event.x, event.y)
            if region in ("heading", "separator", "nothing"):
                return
        selected = self.recent_tree.selection()
        if not selected:
            return
        try:
            idx = int(selected[0])
            tx_id = self._recent_tx_ids[idx]
            self.load_entry_for_edit(tx_id)
        except (ValueError, IndexError):
            pass

    def auto_set_next_receipt(self):
        if self.current_edit_id:
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT receipt_no FROM transactions ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()

        self.ent_receipt.delete(0, tk.END)
        if result and result[0]:
            try:
                old_rec = str(result[0]).strip()
                match = re.search(r'(\d+)$', old_rec)
                if match:
                    digits = match.group(1)
                    next_num = int(digits) + 1
                    new_rec = f"{old_rec[:match.start()]}{next_num:0{len(digits)}d}"
                    self.ent_receipt.insert(0, new_rec)
                elif old_rec:
                    self.ent_receipt.insert(0, old_rec + "_1")
                else:
                    self.ent_receipt.insert(0, "100000")
            except Exception:
                self.ent_receipt.insert(0, "")
        else:
            self.ent_receipt.insert(0, "100000")

    def save_entry(self):
        receipt = self.ent_receipt.get().strip()
        gb_num = self.ent_gb.get().strip()
        name = self.ent_name.get().strip()
        aadhaar = clean_aadhaar(self.ent_aadhaar.get()) if hasattr(self, "ent_aadhaar") else ""
        country = self.cmb_country.get()
        place = self.cmb_place.get()
        currency = self.cmb_entry_currency.get()
        tx_date_ui = self.ent_tx_date.get().strip()

        if not receipt or not country or not place or not name or not gb_num or not currency:
            messagebox.showerror(
                "Validation Error",
                "Receipt, GB Number, Name, Country, Place, and Currency cannot be empty.",
            )
            return

        tx_date_db = parse_ui_date(tx_date_ui)
        if not tx_date_db:
            messagebox.showerror(
                "Date Error", "Invalid date format. Must strictly be DD-MM-YYYY via calendar."
            )
            return

        f_date_db = parse_ui_date(self.settings.get("from_date", ""))
        t_date_db = parse_ui_date(self.settings.get("to_date", ""))

        if f_date_db and t_date_db:
            if not (f_date_db <= tx_date_db <= t_date_db):
                messagebox.showerror(
                    "Out of Period",
                    f"Transaction date has to be in between the From and To date\n({self.settings.get('from_date')} to {self.settings.get('to_date')}).\n\nPlease go to the Settings tab to set the period, or update the FY Period dates directly here in the Entry Form!"
                )
                return

        account_data = {}
        total = 0.0
        for head, (lbl, ent, head_type) in self.head_entries.items():
            if head_type == "Amount":
                try:
                    val = float(ent.get().strip() or 0.0)
                    account_data[head] = val
                    total += val
                except ValueError:
                    messagebox.showerror("Input Error", f"Invalid number in account head: {head}")
                    return
            else:
                account_data[head] = ent.get().strip()

        entry_date_db = datetime.date.today().strftime("%Y-%m-%d")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Automatically insert or update GB holder (name & Aadhaar) in gb_database
        self._upsert_gb_record(cursor, gb_num, name, aadhaar, update_aadhaar=self.is_aadhaar_enabled())

        if self.current_edit_id:
            cursor.execute(
                """
                UPDATE transactions 
                SET receipt_no=?, gb_number=?, name=?, country=?, place=?, currency=?, tx_date=?, account_data=?, total_amount=?
                WHERE id=?
            """,
                (
                    receipt,
                    gb_num,
                    name,
                    country,
                    place,
                    currency,
                    tx_date_db,
                    json.dumps(account_data),
                    total,
                    self.current_edit_id,
                ),
            )
            msg = f"Contribution entry updated successfully for {name}."
        else:
            cursor.execute(
                """
                INSERT INTO transactions 
                (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    receipt,
                    gb_num,
                    name,
                    country,
                    place,
                    currency,
                    tx_date_db,
                    entry_date_db,
                    json.dumps(account_data),
                    total,
                ),
            )
            msg = f"Contribution successfully saved for {name}."

        conn.commit()
        conn.close()

        curr_symbol = self.get_safe_currency_symbol(currency)
        messagebox.showinfo("Success", f"{msg}\nTotal: {total:,.2f} {curr_symbol}")
        self.clear_entry_form()
        self.auto_set_next_receipt()
        self.refresh_recent_entries()
        self.refresh_db_table()

    def clear_entry_form(self):
        self.current_edit_id = None
        self._last_looked_up_gb = None
        if self._lookup_after_id:
            try:
                self.root.after_cancel(self._lookup_after_id)
            except Exception:
                pass
            self._lookup_after_id = None

        self.btn_save_tx.config(text="💾 Save Contribution Entry")
        self.lbl_edit_warning.config(text="")

        self.ent_gb.delete(0, tk.END)
        self.ent_name.delete(0, tk.END)
        if hasattr(self, "ent_aadhaar"):
            self.ent_aadhaar.delete(0, tk.END)
        self.lbl_gb_status.config(text="")

        for head_name, (lbl, ent, head_type) in self.head_entries.items():
            if head_type == "Amount":
                ent.delete(0, tk.END)
                def_val = 0.0
                for item in self.settings.get("account_heads", []):
                    if item["head"] == head_name:
                        def_val = item.get("default", 0.0)
                        break
                ent.insert(0, str(def_val))
            else:
                def_val = ""
                for item in self.settings.get("account_heads", []):
                    if item["head"] == head_name:
                        def_val = item.get("default", "")
                        break
                if def_val:
                    try:
                        ent.set_date(datetime.datetime.strptime(str(def_val), "%d-%m-%Y"))
                    except Exception:
                        ent.set_date(datetime.date.today())
                else:
                    ent.set_date(datetime.date.today())

        self.calculate_realtime_total()
        self.auto_set_next_receipt()
        try:
            self.ent_gb.focus_set()
        except Exception:
            pass

    def load_entry_for_edit(self, tx_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT receipt_no, gb_number, name, country, place, currency, tx_date, account_data FROM transactions WHERE id=?",
            (tx_id,),
        )
        row = cursor.fetchone()
        aadhaar_val = ""
        if row:
            cursor.execute(
                "SELECT COALESCE(aadhaar_number, '') FROM gb_database WHERE LOWER(gb_number) = LOWER(?)",
                (row[1],),
            )
            aad_row = cursor.fetchone()
            if aad_row:
                aadhaar_val = aad_row[0] or ""
        conn.close()

        if not row:
            return

        self.clear_entry_form()
        self.current_edit_id = tx_id

        self.lbl_edit_warning.config(text=f"⚠ EDITING EXISTING RECORD ID: {tx_id}")
        self.btn_save_tx.config(text="💾 Update Contribution Entry")

        self.ent_receipt.delete(0, tk.END)
        self.ent_receipt.insert(0, row[0])

        self.ent_gb.delete(0, tk.END)
        self.ent_gb.insert(0, row[1])

        self.ent_name.delete(0, tk.END)
        self.ent_name.insert(0, row[2])

        if hasattr(self, "ent_aadhaar"):
            self.ent_aadhaar.delete(0, tk.END)
            if aadhaar_val:
                self.ent_aadhaar.insert(0, aadhaar_val)

        self._last_looked_up_gb = (row[1].strip().lower(), row[2], aadhaar_val)
        self.lbl_gb_status.config(text="✓ Loaded for Editing", foreground="blue")

        self.cmb_country.set(row[3])
        self.on_country_select()
        self.cmb_place.set(row[4])

        self.cmb_entry_currency.set(row[5])
        self.on_entry_currency_change()

        ui_date = format_db_date(row[6])
        self.ent_tx_date.set_date(datetime.datetime.strptime(ui_date, "%d-%m-%Y"))

        data_json = json.loads(row[7])
        for head_name, (lbl, ent, head_type) in self.head_entries.items():
            if head_type == "Amount":
                ent.delete(0, tk.END)
                ent.insert(0, str(data_json.get(head_name, 0.0)))
            else:
                val = data_json.get(head_name, "")
                if val:
                    try:
                        ent.set_date(datetime.datetime.strptime(str(val), "%d-%m-%Y"))
                    except Exception:
                        pass

        self.calculate_realtime_total()
        self.notebook.select(self.tab_entry)

    # =========================================================================
    # TAB 2: GB DATABASE
    # =========================================================================
    def build_db_tab(self):
        frame_controls = ttk.Frame(self.tab_db)
        frame_controls.pack(fill="x", padx=15, pady=10)

        btn_clipboard = ttk.Button(
            frame_controls, text="📋 Paste directly from Excel Clipboard", command=self.import_from_clipboard
        )
        btn_clipboard.pack(side="left", padx=(5, 0))
        lbl_info_clip = tk.Label(frame_controls, text=" ⓘ", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_clip.pack(side="left", padx=(0, 15))
        ToolTip(lbl_info_clip, """""How to import:
1. Open your Excel file
2. Copy 2 columns: GB Number, Name
   OR 3 columns: GB Number, Name, Aadhaar Number
3. Click this button to paste them instantly into the database!""""")

        btn_clean = ttk.Button(
            frame_controls, text="🧹 Clean Database", command=self.cleanse_gb_database
        )
        btn_clean.pack(side="left", padx=(5, 0))
        lbl_info_clean = tk.Label(frame_controls, text=" ⓘ", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_clean.pack(side="left", padx=(0, 15))
        ToolTip(lbl_info_clean, """""Clean Database:
This scans the entire database for duplicates.
If someone has multiple entries, it merges them, keeping the longest name and Aadhaar number.
It also removes blank rows and fixes formatting issues.""""")

        btn_del_gb = ttk.Button(
            frame_controls, text="❌ Delete Selected", command=self.delete_selected_gbs
        )
        btn_del_gb.pack(side="right", padx=5)

        btn_backup = ttk.Button(frame_controls, text="💾 Backup Database", command=self.backup_db)
        btn_backup.pack(side="right", padx=5)

        # Search & Sort toolbar for GB Database
        frame_db_bar = ttk.Frame(self.tab_db)
        frame_db_bar.pack(fill="x", padx=15, pady=(0, 6))

        ttk.Label(frame_db_bar, text="Search:").pack(side="left", padx=(5, 4))
        self.ent_db_search = ttk.Entry(frame_db_bar, width=26)
        self.ent_db_search.pack(side="left", padx=(0, 15))
        self.ent_db_search.bind("<KeyRelease>", lambda e: self.refresh_db_table())

        ttk.Label(frame_db_bar, text="Sort By:").pack(side="left", padx=(0, 4))
        self.cmb_db_sort = ttk.Combobox(
            frame_db_bar,
            values=[
                "Recently Added (Newest First)",
                "Name (A → Z)",
                "Name (Z → A)",
                "GB Number (A → Z)",
                "GB Number (Z → A)",
            ],
            state="readonly",
            width=28,
        )
        self.cmb_db_sort.set("Recently Added (Newest First)")
        self.cmb_db_sort.pack(side="left", padx=(0, 4))
        self.cmb_db_sort.bind("<<ComboboxSelected>>", lambda e: self.refresh_db_table())

        lbl_info_db_sort = tk.Label(
            frame_db_bar, text=" ⓘ", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold")
        )
        lbl_info_db_sort.pack(side="left", padx=(0, 10))
        ToolTip(
            lbl_info_db_sort,
            "GB Database Search & Sort:\n"
            "• Recently Added: Shows newly pasted/added records at the top.\n"
            "• Name (A → Z / Z → A): Alphabetical sorting by Full Name.\n"
            "• GB Number: Natural numeric order.\n"
            "• You can also click any column header below to sort!",
        )

        self.lbl_db_count = ttk.Label(frame_db_bar, text="Total Records: 0", font=("Segoe UI", 9, "italic"), foreground="gray")
        self.lbl_db_count.pack(side="right", padx=5)

        frame_table = ttk.LabelFrame(self.tab_db, text="Green Book Master Records", padding=10)
        frame_table.pack(fill="both", expand=True, padx=15, pady=5)

        self.db_tree = ttk.Treeview(frame_table, columns=("gb", "name", "aadhaar"), show="headings")
        self.db_tree.heading("gb", text="Green Book Number", command=lambda: self.sort_db_by_column("gb"))
        self.db_tree.heading("name", text="Full Name", command=lambda: self.sort_db_by_column("name"))
        self.db_tree.heading("aadhaar", text="Aadhaar Number", command=lambda: self.sort_db_by_column("aadhaar"))
        self.db_tree.column("gb", width=200, anchor="center")
        self.db_tree.column("name", width=480, anchor="w")
        self.db_tree.column("aadhaar", width=220, anchor="center")
        self.db_tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.db_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.db_tree.configure(yscrollcommand=scrollbar.set)

        self.apply_aadhaar_visibility()
        self.refresh_db_table()

    def sort_db_by_column(self, col_id):
        """Toggle GB Database sort when clicking a column header."""
        current = self.cmb_db_sort.get() if hasattr(self, "cmb_db_sort") else ""
        if col_id == "name":
            self.cmb_db_sort.set("Name (Z → A)" if current == "Name (A → Z)" else "Name (A → Z)")
        elif col_id == "gb":
            self.cmb_db_sort.set("GB Number (Z → A)" if current == "GB Number (A → Z)" else "GB Number (A → Z)")
        elif col_id == "aadhaar":
            self.cmb_db_sort.set("Recently Added (Newest First)")
        self.refresh_db_table()

    def refresh_db_table(self):
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT rowid, gb_number, name, COALESCE(aadhaar_number, '') FROM gb_database")
        all_rows = cursor.fetchall()
        conn.close()

        total_count = len(all_rows)
        search_q = self.ent_db_search.get().strip().lower() if hasattr(self, "ent_db_search") else ""
        if search_q:
            rows = [
                r for r in all_rows
                if search_q in str(r[1]).lower()
                or search_q in str(r[2]).lower()
                or search_q in str(r[3]).lower()
            ]
        else:
            rows = list(all_rows)

        sort_mode = self.cmb_db_sort.get() if hasattr(self, "cmb_db_sort") else "Recently Added (Newest First)"
        if sort_mode == "Recently Added (Newest First)":
            rows.sort(key=lambda r: r[0], reverse=True)
        elif sort_mode == "Name (A → Z)":
            rows.sort(key=lambda r: (str(r[2]).strip().lower(), self._natural_sort_key(r[1])))
        elif sort_mode == "Name (Z → A)":
            rows.sort(key=lambda r: (str(r[2]).strip().lower(), self._natural_sort_key(r[1])), reverse=True)
        elif sort_mode == "GB Number (A → Z)":
            rows.sort(key=lambda r: self._natural_sort_key(r[1]))
        elif sort_mode == "GB Number (Z → A)":
            rows.sort(key=lambda r: self._natural_sort_key(r[1]), reverse=True)

        # Update column header arrows cleanly
        self.db_tree.heading(
            "gb",
            text="Green Book Number ▲" if sort_mode == "GB Number (A → Z)"
            else ("Green Book Number ▼" if sort_mode == "GB Number (Z → A)" else "Green Book Number"),
        )
        self.db_tree.heading(
            "name",
            text="Full Name ▲" if sort_mode == "Name (A → Z)"
            else ("Full Name ▼" if sort_mode == "Name (Z → A)" else "Full Name"),
        )

        for _, gb_num, name, aadhaar in rows:
            self.db_tree.insert("", "end", values=(gb_num, name, aadhaar))

        if hasattr(self, "lbl_db_count"):
            if search_q:
                self.lbl_db_count.config(text=f"Showing {len(rows)} of {total_count} records")
            else:
                self.lbl_db_count.config(text=f"Total Records: {total_count}")

    def import_from_clipboard(self):
        try:
            clipboard_data = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("Clipboard Empty", "No data found in clipboard. Copy from Excel first.")
            return

        lines = clipboard_data.splitlines()
        imported, skipped = 0, 0
        header_tokens = {"gb number", "gb_number", "gb no", "green book number", "green book no"}

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        for line in lines:
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                gb_num = parts[0].strip()
                name = parts[1].strip()
                if gb_num.lower() in header_tokens and name.lower() in ("name", "full name", "fullname"):
                    continue
                has_third_col = len(parts) >= 3
                aadhaar = clean_aadhaar(parts[2]) if has_third_col else ""
                if gb_num and name:
                    # Only overwrite existing Aadhaar if a 3rd column was pasted (and non-empty or Aadhaar enabled)
                    self._upsert_gb_record(
                        cursor,
                        gb_num,
                        name,
                        aadhaar,
                        update_aadhaar=(has_third_col and bool(aadhaar)),
                    )
                    imported += 1
                else:
                    skipped += 1
            else:
                skipped += 1

        conn.commit()
        conn.close()

        self.refresh_db_table()
        messagebox.showinfo(
            "Import Complete",
            f"Successfully imported/updated {imported} records from clipboard.\nSkipped rows: {skipped}",
        )

    def cleanse_gb_database(self):
        if not messagebox.askyesno(
            "Confirm Cleansing & Deduplication",
            "This will reformat all GB numbers (lowercase, no spaces/special chars), convert names to Proper Case, and KEEP ONLY ONE record per unique GB number while deleting duplicates. Proceed?",
        ):
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT gb_number, name, COALESCE(aadhaar_number, '') FROM gb_database")
        rows = cursor.fetchall()

        unique_gbs = {}
        duplicates_removed = 0

        # Process and deduplicate in memory
        for old_gb, old_name, old_aadhaar in rows:
            # Clean GB: force lowercase, strip spaces and special characters
            clean_gb = re.sub(r"[-\s#/|\\]", "", old_gb).lower()
            # Proper case Name
            clean_name = old_name.title()
            clean_aad = clean_aadhaar(old_aadhaar)

            if clean_gb not in unique_gbs:
                unique_gbs[clean_gb] = [clean_name, clean_aad]
            else:
                duplicates_removed += 1
                if len(clean_name) > len(unique_gbs[clean_gb][0]):
                    unique_gbs[clean_gb][0] = clean_name
                if clean_aad and (not unique_gbs[clean_gb][1] or len(clean_aad) > len(unique_gbs[clean_gb][1])):
                    unique_gbs[clean_gb][1] = clean_aad

        # Wipe old table and bulk insert the clean, 100% unique data
        cursor.execute("DELETE FROM gb_database")
        
        for gb_key, (name_val, aad_val) in unique_gbs.items():
            cursor.execute(
                "INSERT INTO gb_database (gb_number, name, aadhaar_number) VALUES (?, ?, ?)",
                (gb_key, name_val, aad_val),
            )

        conn.commit()
        conn.close()

        self.refresh_db_table()
        messagebox.showinfo(
            "Database Cleaned", 
            f"Standardization complete.\n\nUnique Records Kept: {len(unique_gbs)}\nDuplicates Removed: {duplicates_removed}"
        )

    def delete_selected_gbs(self):
        selected = self.db_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select one or more records to delete.")
            return

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you strictly sure you want to permanently delete these {len(selected)} Green Book records?",
        ):
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        for item in selected:
            gb_val = self.db_tree.item(item, "values")[0]
            cursor.execute("DELETE FROM gb_database WHERE gb_number=?", (gb_val,))

        conn.commit()
        conn.close()

        self.refresh_db_table()
        messagebox.showinfo("Deleted", "Selected GB records successfully deleted.")

    def backup_db(self):
        target_file = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db")],
            initialfile=f"PaljorDB_Backup_{datetime.date.today().strftime('%d%m%Y')}.db",
        )
        if not target_file:
            return

        import shutil

        try:
            shutil.copy(DB_FILE, target_file)
            messagebox.showinfo("Backup Success", f"Database backed up securely to:\n{target_file}")
        except Exception as e:
            messagebox.showerror("Backup Failed", str(e))

    # =========================================================================
    # TAB 3: REPORTS & FILTERS
    # =========================================================================
    def build_reports_tab(self):
        # --- ZONE 1: SEARCH, FILTER & SORT PARAMETERS ---
        frame_filters = ttk.LabelFrame(self.tab_reports, text="Search, Filter & Sort Parameters", padding=10)
        frame_filters.pack(fill="x", padx=15, pady=(6, 4))

        # Row 0: Dates & Geography / Currency
        ttk.Label(frame_filters, text="From Date:").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        self.flt_from_date = DateEntry(
            frame_filters, width=12, background="darkblue", foreground="white", date_pattern="dd-mm-yyyy"
        )
        self.flt_from_date.grid(row=0, column=1, padx=5, pady=4, sticky="w")

        ttk.Label(frame_filters, text="To Date:").grid(row=0, column=2, sticky="w", padx=(12, 5), pady=4)
        self.flt_to_date = DateEntry(
            frame_filters, width=12, background="darkblue", foreground="white", date_pattern="dd-mm-yyyy"
        )
        self.flt_to_date.grid(row=0, column=3, padx=5, pady=4, sticky="w")

        ttk.Label(frame_filters, text="Country:").grid(row=0, column=4, sticky="w", padx=(12, 5), pady=4)
        self.flt_country = ttk.Combobox(frame_filters, state="readonly", width=14)
        self.flt_country.grid(row=0, column=5, padx=5, pady=4, sticky="w")

        ttk.Label(frame_filters, text="Place:").grid(row=0, column=6, sticky="w", padx=(12, 5), pady=4)
        self.flt_place = ttk.Combobox(frame_filters, state="readonly", width=14)
        self.flt_place.grid(row=0, column=7, padx=5, pady=4, sticky="w")

        ttk.Label(frame_filters, text="Currency:").grid(row=0, column=8, sticky="w", padx=(12, 5), pady=4)
        self.flt_currency = ttk.Combobox(frame_filters, state="readonly", width=12)
        self.flt_currency.grid(row=0, column=9, padx=5, pady=4, sticky="w")

        # Row 1: Text Searches & Account Head
        ttk.Label(frame_filters, text="Receipt No:").grid(row=1, column=0, sticky="w", padx=5, pady=4)
        self.flt_receipt = ttk.Entry(frame_filters, width=15)
        self.flt_receipt.grid(row=1, column=1, padx=5, pady=4, sticky="w")
        self.flt_receipt.bind("<Return>", lambda e: self.run_report())

        ttk.Label(frame_filters, text="GB Number:").grid(row=1, column=2, sticky="w", padx=(12, 5), pady=4)
        self.flt_gb = ttk.Entry(frame_filters, width=15)
        self.flt_gb.grid(row=1, column=3, padx=5, pady=4, sticky="w")
        self.flt_gb.bind("<Return>", lambda e: self.run_report())

        ttk.Label(frame_filters, text="Name Search:").grid(row=1, column=4, sticky="w", padx=(12, 5), pady=4)
        self.flt_name = ttk.Entry(frame_filters, width=16)
        self.flt_name.grid(row=1, column=5, padx=5, pady=4, sticky="w")
        self.flt_name.bind("<Return>", lambda e: self.run_report())

        ttk.Label(frame_filters, text="Account Head:").grid(row=1, column=6, sticky="w", padx=(12, 5), pady=4)
        self.flt_head = ttk.Combobox(frame_filters, state="readonly", width=16)
        self.flt_head.grid(row=1, column=7, columnspan=2, padx=5, pady=4, sticky="w")

        # Row 2: Sort Controls + Run / Reset
        ttk.Label(frame_filters, text="Sort By:").grid(row=2, column=0, sticky="w", padx=5, pady=4)
        self.flt_sort_by = ttk.Combobox(
            frame_filters,
            values=["Entry Order (ID)", "Receipt Number", "Transaction Date", "Total Amount"],
            state="readonly",
            width=18,
        )
        self.flt_sort_by.set("Entry Order (ID)")
        self.flt_sort_by.grid(row=2, column=1, columnspan=2, padx=5, pady=4, sticky="w")
        self.flt_sort_by.bind("<<ComboboxSelected>>", self._on_sort_control_change)

        ttk.Label(frame_filters, text="Order:").grid(row=2, column=3, sticky="e", padx=(10, 5), pady=4)
        self.flt_sort_order = ttk.Combobox(
            frame_filters,
            values=["Ascending (Oldest / Lowest First)", "Descending (Newest / Highest First)"],
            state="readonly",
            width=30,
        )
        self.flt_sort_order.set("Ascending (Oldest / Lowest First)")
        self.flt_sort_order.grid(row=2, column=4, columnspan=2, padx=5, pady=4, sticky="w")
        self.flt_sort_order.bind("<<ComboboxSelected>>", self._on_sort_control_change)

        lbl_info_sort = tk.Label(
            frame_filters, text="ⓘ", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold")
        )
        lbl_info_sort.grid(row=2, column=6, sticky="w", padx=(2, 8), pady=4)
        ToolTip(
            lbl_info_sort,
            "Sorting Guide:\n"
            "• Entry Order (ID): Shows entries in the exact order recorded (even if backdated).\n"
            "• Receipt Number: Natural numeric order (e.g., 99 before 100).\n"
            "• Transaction Date: Chronological order by payment date.\n"
            "• Total Amount: Sort by contribution total.\n\n"
            "Tip: You can also click any column header in the table to sort,\n"
            "and Export Excel will preserve your exact sort order!",
        )

        f_run_btns = ttk.Frame(frame_filters)
        f_run_btns.grid(row=2, column=7, columnspan=3, sticky="e", padx=5, pady=4)

        btn_filter = tb.Button(
            f_run_btns, text="🔍 Run Report", command=self.run_report, bootstyle="primary"
        )
        btn_filter.pack(side="left", padx=(0, 6))

        btn_reset = tb.Button(
            f_run_btns, text="↺ Reset", command=self.reset_report_filters, bootstyle="secondary-outline"
        )
        btn_reset.pack(side="left")

        # --- ZONE 2: ACTION TOOLBAR (Cleanly separated from Filters) ---
        frame_toolbar = ttk.Frame(self.tab_reports)
        frame_toolbar.pack(fill="x", padx=15, pady=(4, 4))

        ttk.Label(
            frame_toolbar,
            text="💡 Double-click any row to edit  •  Click any column header to sort",
            font=("Segoe UI", 9, "italic"),
        ).pack(side="left", padx=(2, 6))

        lbl_info_tips = tk.Label(
            frame_toolbar, text="ⓘ Tips & Import Help", fg="#007bff", cursor="hand2", font=("Segoe UI", 9, "bold")
        )
        lbl_info_tips.pack(side="left", padx=(2, 10))
        ToolTip(
            lbl_info_tips,
            "Reports & Filters Quick Tips:\n"
            "1. Edit Entry: Double-click any row to load it in the Entry Form.\n"
            "2. Quick Sort: Click any column header to toggle Ascending (▲) / Descending (▼).\n"
            "   The TOTAL row always stays pinned at the bottom.\n"
            "3. Auto-Fit Column: Double-click a column border/header to auto-resize.\n"
            "4. Excel Import Tip: To avoid Excel date errors, click 'Export Excel' first\n"
            "   to get the exact template layout, paste your new entries, then click 'Import Excel'.",
        )

        btn_del_batch = tb.Button(
            frame_toolbar, text="🗑 Delete Selected", command=self.delete_batch_transactions, bootstyle="danger"
        )
        btn_del_batch.pack(side="right", padx=(6, 0))

        ttk.Separator(frame_toolbar, orient="vertical").pack(side="right", fill="y", padx=8, pady=2)

        btn_import = tb.Button(
            frame_toolbar, text="📤 Import Excel", command=self.import_batch_excel, bootstyle="info-outline"
        )
        btn_import.pack(side="right", padx=(0, 4))

        btn_export = tb.Button(
            frame_toolbar, text="📥 Export Excel", command=self.export_report, bootstyle="success"
        )
        btn_export.pack(side="right", padx=(0, 6))

        self.frame_rep_table = ttk.LabelFrame(self.tab_reports, text="Filtered Contributions", padding=5)
        self.frame_rep_table.pack(fill="both", expand=True, padx=15, pady=4)

        self.rep_tree = None
        self.current_report_df = pd.DataFrame()
        self.current_report_raw_ids = []
        self._report_records = []
        self._active_sort_col = "__id__"
        self._active_sort_desc = False
        
        # Initialize default dates once during startup safely
        def_f = self.settings.get("from_date", "")
        def_t = self.settings.get("to_date", "")
        if def_f:
            self.flt_from_date.set_date(datetime.datetime.strptime(def_f, "%d-%m-%Y"))
        if def_t:
            self.flt_to_date.set_date(datetime.datetime.strptime(def_t, "%d-%m-%Y"))

        self.refresh_report_filters()

        # --- FIXED SUMMATION FOOTER (Does not scroll) ---
        frame_footer = ttk.Frame(self.tab_reports, relief="solid", borderwidth=1)
        frame_footer.pack(side="bottom", fill="x", padx=15, pady=5)

        self.lbl_rep_summary = ttk.Label(
            frame_footer, 
            text="Total Records: 0  |  IMMEDIATE SUM TOTAL: 0.00", 
            font=("Arial", 12, "bold"), 
            foreground="darkblue",
            padding=8
        )
        self.lbl_rep_summary.pack(side="right", padx=10)

    def reset_report_filters(self):
        """Reset all report filters and sort controls back to defaults and re-run."""
        def_f = self.settings.get("from_date", "")
        def_t = self.settings.get("to_date", "")
        try:
            if def_f:
                self.flt_from_date.set_date(datetime.datetime.strptime(def_f, "%d-%m-%Y"))
            if def_t:
                self.flt_to_date.set_date(datetime.datetime.strptime(def_t, "%d-%m-%Y"))
        except Exception:
            pass
        self.refresh_report_filters()
        if hasattr(self, "flt_receipt"):
            self.flt_receipt.delete(0, tk.END)
        self.flt_gb.delete(0, tk.END)
        self.flt_name.delete(0, tk.END)
        self.flt_sort_by.set("Entry Order (ID)")
        self.flt_sort_order.set("Ascending (Oldest / Lowest First)")
        self._active_sort_col = "__id__"
        self._active_sort_desc = False
        self.run_report()

    def _natural_sort_key(self, val):
        parts = re.split(r"(\d+)", str(val or "").strip().lower())
        return [int(p) if p.isdigit() else p for p in parts]

    def _sync_sort_state_from_dropdowns(self):
        sort_map = {
            "Entry Order (ID)": "__id__",
            "Receipt Number": "Receipt",
            "Transaction Date": "Transaction Date",
            "Total Amount": "Total",
        }
        self._active_sort_col = sort_map.get(self.flt_sort_by.get(), "__id__")
        self._active_sort_desc = "Descending" in self.flt_sort_order.get()

    def _on_sort_control_change(self, event=None):
        self._sync_sort_state_from_dropdowns()
        if self._report_records:
            self._apply_report_sort_and_render()

    def sort_report_by_column(self, col_name):
        """Sort the currently displayed report by clicking a column header (toggles Asc/Desc)."""
        if not self._report_records:
            return
        if self._active_sort_col == col_name:
            self._active_sort_desc = not self._active_sort_desc
        else:
            self._active_sort_col = col_name
            self._active_sort_desc = False

        # Keep Sort By / Order dropdowns synchronized when applicable
        rev_map = {
            "Receipt": "Receipt Number",
            "Transaction Date": "Transaction Date",
            "Total": "Total Amount",
        }
        if col_name in rev_map:
            self.flt_sort_by.set(rev_map[col_name])
        self.flt_sort_order.set(
            "Descending (Newest / Highest First)"
            if self._active_sort_desc
            else "Ascending (Oldest / Lowest First)"
        )
        self._apply_report_sort_and_render()

    def refresh_report_filters(self):
        
        countries = ["ALL"] + list(self.settings.get("countries", {}).keys())
        self.flt_country["values"] = countries
        self.flt_country.set("ALL")

        places = ["ALL"]
        for p_list in self.settings.get("countries", {}).values():
            places.extend(p_list)
        self.flt_place["values"] = list(set(places))
        self.flt_place.set("ALL")

        self.flt_currency["values"] = ["ALL"] + self.settings.get("currencies", [])
        self.flt_currency.set("ALL")

        heads = ["ALL"] + [h["head"] for h in self.settings.get("account_heads", [])]
        self.flt_head["values"] = heads
        self.flt_head.set("ALL")

    def run_report(self):
        conn = sqlite3.connect(DB_FILE)
        query = "SELECT id, receipt_no, gb_number, name, country, place, currency, tx_date, account_data, total_amount FROM transactions WHERE 1=1"
        params = []

        f_date_db = parse_ui_date(self.flt_from_date.get().strip())
        t_date_db = parse_ui_date(self.flt_to_date.get().strip())

        if f_date_db and t_date_db:
            query += " AND tx_date BETWEEN ? AND ?"
            params.extend([f_date_db, t_date_db])

        if self.flt_country.get() != "ALL":
            query += " AND country = ?"
            params.append(self.flt_country.get())

        if self.flt_place.get() != "ALL":
            query += " AND place = ?"
            params.append(self.flt_place.get())

        if self.flt_currency.get() != "ALL":
            query += " AND currency = ?"
            params.append(self.flt_currency.get())

        if hasattr(self, "flt_receipt") and self.flt_receipt.get().strip():
            query += " AND receipt_no LIKE ?"
            params.append(f"%{self.flt_receipt.get().strip()}%")

        if self.flt_name.get().strip():
            query += " AND name LIKE ?"
            params.append(f"%{self.flt_name.get().strip()}%")

        if self.flt_gb.get().strip():
            query += " AND gb_number LIKE ?"
            params.append(f"%{self.flt_gb.get().strip()}%")

        query += " ORDER BY id ASC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        self._report_records = []
        all_heads = [h["head"] for h in self.settings.get("account_heads", [])]

        for r in rows:
            base = {
                "Receipt": r[1],
                "GB Number": r[2],
                "Name": r[3],
                "Country": r[4],
                "Place": r[5],
                "Currency": r[6],
                "Transaction Date": format_db_date(r[7]),
            }
            data_json = json.loads(r[8])

            selected_head = self.flt_head.get()
            if selected_head != "ALL":
                val = data_json.get(selected_head)
                if val is None:
                    continue
                elif isinstance(val, (int, float)):
                    if val <= 0:
                        continue
                elif isinstance(val, str):
                    if not val.strip():
                        continue
                else:
                    if not val:
                        continue

            for h in all_heads:
                base[h] = data_json.get(h, 0.0)

            base["Total"] = r[9]
            self._report_records.append((r[0], base))

        self._sync_sort_state_from_dropdowns()
        self._apply_report_sort_and_render()

    def _apply_report_sort_and_render(self):
        """Sort self._report_records, sync DataFrame & raw IDs, and render the report Treeview."""
        sort_col = self._active_sort_col
        reverse = self._active_sort_desc

        date_heads = {
            h["head"] for h in self.settings.get("account_heads", []) if h.get("type") == "Date"
        }
        amount_heads = {
            h["head"] for h in self.settings.get("account_heads", []) if h.get("type", "Amount") == "Amount"
        }

        def sort_key(record):
            tx_id, row_dict = record
            if sort_col == "__id__" or sort_col is None:
                return tx_id
            val = row_dict.get(sort_col, "")
            if sort_col == "Receipt":
                return (self._natural_sort_key(val), tx_id)
            if sort_col == "Transaction Date" or sort_col in date_heads:
                return (parse_ui_date(val) or "", tx_id)
            if sort_col == "Total" or sort_col in amount_heads:
                try:
                    return (float(val or 0.0), tx_id)
                except (ValueError, TypeError):
                    return (0.0, tx_id)
            return (str(val or "").strip().lower(), tx_id)

        sorted_records = sorted(self._report_records, key=sort_key, reverse=reverse)
        self._report_records = sorted_records
        self.current_report_raw_ids = [rec[0] for rec in sorted_records]
        self.current_report_df = pd.DataFrame([rec[1] for rec in sorted_records])

        for w in self.frame_rep_table.winfo_children():
            w.destroy()

        if self.current_report_df.empty:
            self.rep_tree = None
            ttk.Label(self.frame_rep_table, text="No records match your filters.").pack(pady=20)
            curr_symbol = self.get_safe_currency_symbol(self.settings.get("currency"))
            self.lbl_rep_summary.config(
                text=f"Total Displayed Records: 0   |   IMMEDIATE SUM TOTAL: 0.00 {curr_symbol}"
            )
            return

        cols = list(self.current_report_df.columns)

        scroll_y = ttk.Scrollbar(self.frame_rep_table, orient="vertical")
        scroll_x = ttk.Scrollbar(self.frame_rep_table, orient="horizontal")

        self.rep_tree = ttk.Treeview(
            self.frame_rep_table,
            columns=cols,
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )

        scroll_y.config(command=self.rep_tree.yview)
        scroll_x.config(command=self.rep_tree.xview)

        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.rep_tree.pack(side="left", fill="both", expand=True)

        arrow = " ▼" if reverse else " ▲"
        for c in cols:
            heading_label = f"{c}{arrow}" if sort_col == c else c
            self.rep_tree.heading(c, text=heading_label, command=lambda col=c: self.sort_report_by_column(col))
            w_size = 180 if c == "Name" else 110
            self.rep_tree.column(c, width=w_size, anchor="center" if c != "Name" else "w", minwidth=90, stretch=False)

        for idx, row_data in self.current_report_df.iterrows():
            self.rep_tree.insert("", "end", iid=str(idx), values=list(row_data))

        if not self.current_report_df.empty:
            total_values = []
            for col in cols:
                if col == "Receipt":
                    total_values.append("TOTAL")
                elif col == "Total":
                    col_sum = self.current_report_df[col].apply(pd.to_numeric, errors='coerce').sum()
                    total_values.append(round(col_sum, 1))
                else:
                    is_amount = col in amount_heads
                    if is_amount:
                        col_sum = self.current_report_df[col].apply(pd.to_numeric, errors='coerce').sum()
                        total_values.append(round(col_sum, 1))
                    else:
                        total_values.append("")
            self.rep_tree.insert("", "end", iid="total", values=total_values, tags=("total_row",))
            try:
                import ttkbootstrap as tb
                current_theme = tb.Style().theme.name
                if current_theme == "superhero":
                    self.rep_tree.tag_configure("total_row", font=("TkDefaultFont", 10, "bold"), background="#1a2b3c", foreground="white")
                else:
                    self.rep_tree.tag_configure("total_row", font=("TkDefaultFont", 10, "bold"), background="#d9edf7", foreground="black")
            except Exception:
                pass

        self.rep_tree.bind("<Double-1>", self.on_report_double_click)
        # --- UPDATE FIXED FOOTER SUMMATION ---
        total_records = len(self.current_report_df)
        immediate_sum = self.current_report_df["Total"].sum() if not self.current_report_df.empty else 0.0
        
        curr_symbol = self.get_safe_currency_symbol(self.settings.get("currency"))
        self.lbl_rep_summary.config(
            text=f"Total Displayed Records: {total_records}   |   IMMEDIATE SUM TOTAL: {immediate_sum:,.2f} {curr_symbol}"
        )

    def on_report_double_click(self, event=None):
        if event and hasattr(event, "x") and hasattr(event, "y"):
            region = self.rep_tree.identify_region(event.x, event.y)
            if region in ("separator", "heading"):
                self._rep_tree_auto_resize_column(event)
                return
        selected = self.rep_tree.selection()
        if not selected:
            return
        if selected[0] == "total":
            return
        try:
            idx = int(selected[0])
            tx_id = self.current_report_raw_ids[idx]
            self.load_entry_for_edit(tx_id)
        except (ValueError, IndexError):
            pass

    def export_report(self):
        if self.current_report_df.empty:
            messagebox.showwarning("Export Empty", "Run a report first to export data.")
            return

        target_file = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Spreadsheet", "*.xlsx")],
            initialfile=f"Paljor_Report_{datetime.date.today().strftime('%d%m%Y')}.xlsx",
        )
        if not target_file:
            return

        try:
            export_df = self.current_report_df.copy()
            if "Transaction Date" in export_df.columns:
                export_df["Transaction Date"] = pd.to_datetime(export_df["Transaction Date"], format="%d-%m-%Y", errors="coerce").dt.date
            for item in self.settings.get("account_heads", []):
                h = item["head"]
                if item.get("type") == "Date" and h in export_df.columns:
                    export_df[h] = pd.to_datetime(export_df[h], format="%d-%m-%Y", errors="coerce").dt.date

            # Add TOTAL row for the exported Excel
            total_values = {}
            for col in export_df.columns:
                if col == "Receipt":
                    total_values[col] = "TOTAL"
                elif col == "Total":
                    col_sum = self.current_report_df[col].apply(pd.to_numeric, errors='coerce').sum()
                    total_values[col] = round(col_sum, 1)
                else:
                    is_amount = False
                    for h in self.settings.get("account_heads", []):
                        if h["head"] == col and h.get("type", "Amount") == "Amount":
                            is_amount = True
                            break
                    if is_amount:
                        col_sum = self.current_report_df[col].apply(pd.to_numeric, errors='coerce').sum()
                        total_values[col] = round(col_sum, 1)
                    else:
                        total_values[col] = ""
            
            total_df = pd.DataFrame([total_values])
            export_df = pd.concat([export_df, total_df], ignore_index=True)

            export_df.to_excel(target_file, index=False, sheet_name="Contributions")
            messagebox.showinfo("Export Success", f"Report saved cleanly to:\n{target_file}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save Excel:\n{e}")

    def _rep_tree_auto_resize_column(self, event):
        region = self.rep_tree.identify_region(event.x, event.y)
        if region not in ("separator", "heading"):
            return
            
        col = self.rep_tree.identify_column(event.x)
        if not col:
            return
            
        try:
            col_idx = int(col.replace('#', '')) - 1
        except ValueError:
            return
        cols = self.rep_tree["columns"]
        if col_idx < 0 or col_idx >= len(cols):
            return
            
        col_id = cols[col_idx]
        header_text = self.rep_tree.heading(col_id, "text")
        
        import tkinter.font as tkFont
        font = tkFont.nametofont("TkDefaultFont")
        
        max_w = font.measure(str(header_text)) + 20
        
        for item in self.rep_tree.get_children(""):
            val = self.rep_tree.set(item, col_id)
            w = font.measure(str(val)) + 20
            if w > max_w:
                max_w = w
                
        self.rep_tree.column(col_id, width=max_w)

    def import_batch_excel(self):
        source_file = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if not source_file:
            return

        try:
            df_import = pd.read_excel(source_file)
        except Exception as e:
            messagebox.showerror("File Read Error", f"Cannot open Excel file:\n{e}")
            return

        expected_heads = [
            "Receipt",
            "GB Number",
            "Name",
            "Country",
            "Place",
            "Currency",
            "Transaction Date",
        ]
        all_acc_heads = [h["head"] for h in self.settings.get("account_heads", [])]
        expected_heads.extend(all_acc_heads)
        expected_heads.append("Total")

        missing_cols = [c for c in expected_heads if c not in df_import.columns]
        if missing_cols:
            err_msg = (
                "IMPORT REJECTED: Excel column headings do not match the database setup exactly.\n\n"
                f"Missing Expected Columns:\n{', '.join(missing_cols)}\n\n"
                "Tip: Export an empty report first to get the exact copyable header layout."
            )
            messagebox.showerror("Header Mismatch Error", err_msg)
            return

        bad_dates = []
        for idx, row in df_import.iterrows():
            if str(row.get("Receipt", "")).strip().upper() == "TOTAL":
                continue
                
            val = row.get("Transaction Date", "")
            parsed = parse_ui_date(val)
            if not parsed:
                val_str = val.strftime("%d-%m-%Y") if hasattr(val, "strftime") else str(val).strip()
                bad_dates.append(f"Row {idx+2}: '{val_str}'")

        if bad_dates:
            err_msg = (
                "IMPORT REJECTED: Invalid 'Transaction Date' formats detected.\n"
                "Dates must be in DD-MM-YYYY or ISO YYYY-MM-DD format (e.g., 30-01-2026 or 2026-01-30).\n\n"
                "💡 PRO TIP FOR EASY IMPORTING:\n"
                "Excel often breaks date formats automatically. To bypass this:\n"
                "1. Export a report from the app first (pass a dummy entry if needed).\n"
                "2. Open that exported sheet and copy-paste your new dates directly into its 'Transaction Date' column as General Text.\n"
                "3. Save and import that file.\n\n"
                f"Problematic Rows:\n{chr(10).join(bad_dates[:8])}"
                f"{chr(10) + '...' if len(bad_dates) > 8 else ''}"
            )
            messagebox.showerror("Date Format Error", err_msg)
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        imported = 0
        entry_date_db = datetime.date.today().strftime("%Y-%m-%d")

        for _, row in df_import.iterrows():
            receipt = str(row["Receipt"]).strip()
            if receipt.upper() == "TOTAL":
                continue
                
            gb_num = str(row["GB Number"]).strip()
            name = str(row["Name"]).strip()
            country = str(row["Country"]).strip()
            place = str(row["Place"]).strip()
            currency = str(row["Currency"]).strip()

            raw_d = row["Transaction Date"]
            tx_date_db = parse_ui_date(raw_d)
            if not tx_date_db:
                tx_date_db = datetime.date.today().strftime("%Y-%m-%d")

            acc_data = {}
            for item in self.settings.get("account_heads", []):
                h = item["head"]
                h_type = item.get("type", "Amount")
                val = row.get(h) if h in row else None
                if h_type == "Amount":
                    try:
                        if pd.isna(val):
                            acc_data[h] = 0.0
                        else:
                            f_val = float(val)
                            import math
                            if math.isnan(f_val) or math.isinf(f_val):
                                acc_data[h] = 0.0
                            else:
                                acc_data[h] = f_val
                    except Exception:
                        acc_data[h] = 0.0
                else:
                    if hasattr(val, "strftime"):
                        acc_data[h] = val.strftime("%d-%m-%Y")
                    elif pd.isna(val):
                        acc_data[h] = ""
                    else:
                        v_str = str(val).strip()
                        if v_str.lower() in ("nan", "nat", "none"):
                            acc_data[h] = ""
                        else:
                            parsed_d = parse_ui_date(v_str)
                            if parsed_d:
                                acc_data[h] = format_db_date(parsed_d)
                            else:
                                acc_data[h] = v_str

            total_val = row.get("Total") if "Total" in row else None
            try:
                if pd.isna(total_val):
                    total = sum(v for v in acc_data.values() if isinstance(v, (int, float)))
                else:
                    total = float(total_val)
                    import math
                    if math.isnan(total) or math.isinf(total):
                        total = sum(v for v in acc_data.values() if isinstance(v, (int, float)))
            except Exception:
                total = sum(v for v in acc_data.values() if isinstance(v, (int, float)))

            aadhaar_col_val = ""
            for aad_col in ("Aadhaar Number", "Adhaar Number", "Aadhaar", "Adhaar"):
                if aad_col in row:
                    aadhaar_col_val = clean_aadhaar(row.get(aad_col))
                    break

            self._upsert_gb_record(
                cursor,
                gb_num,
                name,
                aadhaar_col_val,
                update_aadhaar=bool(aadhaar_col_val),
            )
            cursor.execute(
                """
                INSERT INTO transactions 
                (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    receipt,
                    gb_num,
                    name,
                    country,
                    place,
                    currency,
                    tx_date_db,
                    entry_date_db,
                    json.dumps(acc_data),
                    total,
                ),
            )
            imported += 1

        conn.commit()
        conn.close()

        self.run_report()
        self.refresh_recent_entries()
        self.refresh_db_table()
        messagebox.showinfo("Import Complete", f"Successfully imported {imported} transaction records.")

    def delete_batch_transactions(self):
        if not self.rep_tree:
            return
        selected = self.rep_tree.selection()
        
        # Filter out the total row
        selected = [s for s in selected if s != "total"]
        
        if not selected:
            messagebox.showwarning("No Selection", "Select rows from the report table to delete.")
            return

        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Are you absolutely sure you want to permanently delete these {len(selected)} contribution entries?",
        ):
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        for item_id in selected:
            idx = int(item_id)
            tx_id = self.current_report_raw_ids[idx]
            cursor.execute("DELETE FROM transactions WHERE id=?", (tx_id,))

        conn.commit()
        conn.close()

        self.run_report()
        self.refresh_recent_entries()
        messagebox.showinfo("Deleted", "Batch records deleted successfully.")

    # =========================================================================
    # TAB 4: SETTINGS
    # =========================================================================
    def build_settings_tab(self):
        frame_hdr = ttk.LabelFrame(self.tab_settings, text="Form Title Configuration", padding=10)
        frame_hdr.pack(fill="x", padx=15, pady=5)

        ttk.Label(frame_hdr, text="Office Heading Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.set_office = ttk.Entry(frame_hdr, width=30)
        self.set_office.grid(row=0, column=1, padx=5, pady=5)
        self.set_office.insert(0, self.settings.get("office_name", "Office of Tibet"))

        f_title_btn = ttk.Frame(frame_hdr)
        f_title_btn.grid(row=0, column=2, padx=15, pady=5, sticky="w")
        btn_save_hdr = ttk.Button(f_title_btn, text="Update Title", command=self.save_title_settings)
        btn_save_hdr.pack(side="left")
        lbl_info_title = tk.Label(f_title_btn, text=" ⓘ", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_title.pack(side="left", padx=(5, 0))
        ToolTip(lbl_info_title, "Updates the Office Title displayed\nat the very top of the application window.")
        
        self.theme_var = tk.StringVar(value="On" if self.settings.get("theme", "cosmo") == "superhero" else "Off")
        btn_theme = tb.Checkbutton(frame_hdr, text=" Dark Mode", bootstyle="round-toggle", variable=self.theme_var, onvalue="On", offvalue="Off", command=self.toggle_theme)
        btn_theme.grid(row=0, column=3, padx=20, pady=5)

        f_aadhaar_toggle = ttk.Frame(frame_hdr)
        f_aadhaar_toggle.grid(row=0, column=4, padx=15, pady=5, sticky="w")
        self.aadhaar_var = tk.BooleanVar(value=bool(self.settings.get("enable_aadhaar", True)))
        btn_aadhaar = tb.Checkbutton(
            f_aadhaar_toggle,
            text=" Enable Aadhaar Number",
            bootstyle="round-toggle",
            variable=self.aadhaar_var,
            command=self.toggle_aadhaar_setting,
        )
        btn_aadhaar.pack(side="left")
        lbl_info_aadhaar = tk.Label(f_aadhaar_toggle, text=" ⓘ", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_aadhaar.pack(side="left", padx=(5, 0))
        ToolTip(
            lbl_info_aadhaar,
            "Show or hide the Aadhaar Number field on the Entry Form\nand the Aadhaar Number column in the GB Database tab.\nTurning this off preserves any already-stored Aadhaar numbers.",
        )

        frame_other = ttk.LabelFrame(
            self.tab_settings, text="Other setting (Periods, Currencies & Geographies)", padding=10
        )
        frame_other.pack(fill="both", expand=True, padx=15, pady=5)

        ttk.Label(frame_other, text="From Date:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.set_fdate = DateEntry(
            frame_other, width=12, background="darkblue", foreground="white", date_pattern="dd-mm-yyyy"
        )
        self.set_fdate.grid(row=0, column=1, padx=5, pady=5)
        self.set_fdate.bind("<<DateEntrySelected>>", self.sync_period_from_settings)
        self.set_fdate.bind("<FocusOut>", self.sync_period_from_settings)
        if self.settings.get("from_date", ""):
            self.set_fdate.set_date(
                datetime.datetime.strptime(self.settings.get("from_date"), "%d-%m-%Y")
            )

        ttk.Label(frame_other, text="To Date:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.set_tdate = DateEntry(
            frame_other, width=12, background="darkblue", foreground="white", date_pattern="dd-mm-yyyy"
        )
        self.set_tdate.grid(row=0, column=3, padx=5, pady=5)
        self.set_tdate.bind("<<DateEntrySelected>>", self.sync_period_from_settings)
        self.set_tdate.bind("<FocusOut>", self.sync_period_from_settings)
        if self.settings.get("to_date", ""):
            self.set_tdate.set_date(
                datetime.datetime.strptime(self.settings.get("to_date"), "%d-%m-%Y")
            )

        f_per_btn = ttk.Frame(frame_other)
        f_per_btn.grid(row=0, column=4, sticky="w", padx=10, pady=5)
        btn_per = ttk.Button(f_per_btn, text="Apply Period", command=self.apply_period_setting)
        btn_per.pack(side="left")
        lbl_info_period = tk.Label(f_per_btn, text=" ⓘ", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_period.pack(side="left", padx=(5, 0))
        ToolTip(lbl_info_period, "Sets the default Financial Year Period.\nWhen you add new contributions in the Entry Form,\nthey will automatically use these dates.")

        ttk.Label(frame_other, text="Default Currency:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.cmb_set_curr = ttk.Combobox(
            frame_other, values=self.settings.get("currencies", []), state="readonly", width=15
        )
        self.cmb_set_curr.grid(row=1, column=1, padx=5, pady=5)
        self.cmb_set_curr.set(self.settings.get("currency", ""))

        ttk.Button(frame_other, text="Set Default Currency", command=self.apply_default_currency).grid(
            row=1, column=2, columnspan=2, sticky="w", padx=5, pady=5
        )
        ttk.Button(frame_other, text="❌ Delete Selected Currency", command=self.delete_currency).grid(
            row=1, column=4, columnspan=2, sticky="w", padx=5, pady=5
        )

        ttk.Label(frame_other, text="Add Currency Name:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.ent_new_curr = ttk.Entry(frame_other, width=15)
        self.ent_new_curr.grid(row=2, column=1, padx=5, pady=5)

        f_curr_btn = ttk.Frame(frame_other)
        f_curr_btn.grid(row=2, column=2, sticky="w", padx=5, pady=5)
        btn_curr = ttk.Button(f_curr_btn, text="💵 Add Currency", command=self.insert_currency)
        btn_curr.pack(side="left")
        lbl_info_curr = tk.Label(f_curr_btn, text=" ⓘ", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_curr.pack(side="left", padx=(5, 0))
        ToolTip(lbl_info_curr, "Type a currency symbol or code (e.g. USD, EUR)\nin the box and click Add to make it\navailable in the dropdowns.")
        

        sep = ttk.Separator(frame_other, orient="horizontal")
        sep.grid(row=3, column=0, columnspan=6, sticky="ew", pady=10)

        ttk.Label(frame_other, text="Select Country:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.cmb_geo_country = ttk.Combobox(
            frame_other, values=list(self.settings.get("countries", {}).keys()), width=15
        )
        self.cmb_geo_country.grid(row=4, column=1, padx=5, pady=5)

        ttk.Label(frame_other, text="New Place Name:").grid(row=4, column=2, sticky="w", padx=5, pady=5)
        self.ent_new_place = ttk.Entry(frame_other, width=15)
        self.ent_new_place.grid(row=4, column=3, padx=5, pady=5)

        f_loc_btn = ttk.Frame(frame_other)
        f_loc_btn.grid(row=4, column=4, sticky="w", padx=5, pady=5)
        btn_loc = ttk.Button(f_loc_btn, text="📍 Add Location", command=self.add_location)
        btn_loc.pack(side="left")
        lbl_info_loc = tk.Label(f_loc_btn, text=" ⓘ", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_loc.pack(side="left", padx=(5, 0))
        ToolTip(lbl_info_loc, "Add a new Place/City to the selected Country.\nUseful for categorizing contributors\nby region or chapter.")


        frame_heads = ttk.LabelFrame(
            self.tab_settings, text="Manage Account Heads (Add, Rearrange & Defaults)", padding=10
        )
        frame_heads.pack(fill="x", padx=15, pady=5)

        f_lst = ttk.Frame(frame_heads)
        f_lst.pack(side="left", fill="y", padx=5, pady=5)

        self.tree_heads = ttk.Treeview(f_lst, columns=("drag", "head", "type", "amt"), show="headings", height=25)
        self.tree_heads.heading("drag", text="↕")
        self.tree_heads.heading("head", text="Account Head")
        self.tree_heads.heading("type", text="Type")
        self.tree_heads.heading("amt", text="Default Amt / Date")
        self.tree_heads.column("drag", width=40, anchor="center", stretch=False)
        self.tree_heads.column("head", width=250, anchor="w")
        self.tree_heads.column("type", width=120, anchor="center")
        self.tree_heads.column("amt", width=150, anchor="center")
        self.tree_heads.pack(side="left", fill="both", expand=True)

        # BIND SELECTION TO INSTANTLY POPULATE THE INPUT BOXES BELOW
        self.tree_heads.bind("<<TreeviewSelect>>", self.on_head_select)
        self.tree_heads.bind("<ButtonPress-1>", self._tree_drag_start)
        self.tree_heads.bind("<B1-Motion>", self._tree_drag_motion)
        self.tree_heads.bind("<ButtonRelease-1>", self._tree_drag_release)
        self.tree_heads.bind("<Motion>", self._tree_hover)
        self.tree_heads.bind("<Leave>", self._tree_leave)

        self.refresh_settings_heads_list()

        f_add_h = ttk.Frame(frame_heads)
        f_add_h.pack(side="left", fill="both", padx=15, pady=5)

        ttk.Label(f_add_h, text="Head Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.ent_new_head = ttk.Entry(f_add_h, width=18)
        self.ent_new_head.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(f_add_h, text="Type:").grid(row=1, column=0, sticky="w", pady=2)
        self.cmb_new_type = ttk.Combobox(f_add_h, values=["Amount", "Date"], state="readonly", width=15)
        self.cmb_new_type.grid(row=1, column=1, padx=5, pady=2)
        self.cmb_new_type.set("Amount")
        self.cmb_new_type.bind("<<ComboboxSelected>>", self.on_head_type_change)

        self.lbl_new_def = ttk.Label(f_add_h, text="Default Amt:")
        self.lbl_new_def.grid(row=2, column=0, sticky="w", pady=2)
        self.ent_new_def = ttk.Entry(f_add_h, width=18)
        self.ent_new_def.grid(row=2, column=1, padx=5, pady=2)
        self.ent_new_def.insert(0, "")

        btn_frame = ttk.Frame(f_add_h)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky="w")
        tb.Button(btn_frame, text="💾 Save / Edit Head", command=self.add_account_head, bootstyle="success").pack(side="left", padx=(0, 5))
        tb.Button(btn_frame, text="🗑 Delete Head", command=self.delete_account_head, bootstyle="danger").pack(side="left")


    # --- NEW METHOD: AUTO-POPULATE SELECTED ACCOUNT HEAD ---
    def on_head_select(self, event):
        """Copies the selected existing account head and its default amount to the input boxes."""
        selected = self.tree_heads.selection()
        if not selected:
            return
        item_values = self.tree_heads.item(selected[0], "values")
        if item_values:
            self.ent_new_head.delete(0, tk.END)
            self.ent_new_head.insert(0, item_values[1])

            try:
                self.cmb_new_type.set(item_values[2])
            except Exception:
                pass
            
            self.on_head_type_change()

            if self.cmb_new_type.get() == "Date":
                try:
                    self.ent_new_def.set_date(datetime.datetime.strptime(str(item_values[3]), "%d-%m-%Y"))
                except Exception:
                    self.ent_new_def.set_date(datetime.date.today())
            else:
                self.ent_new_def.delete(0, tk.END)
                self.ent_new_def.insert(0, item_values[3])

    def on_head_type_change(self, event=None):
        parent = self.ent_new_def.master
        sel_type = self.cmb_new_type.get()
        curr_val = self.ent_new_def.get()
        self.ent_new_def.destroy()

        if sel_type == "Date":
            self.lbl_new_def.config(text="Default Date:")
            self.ent_new_def = DateEntry(parent, width=15, background="darkblue", foreground="white", borderwidth=2, date_pattern="dd-mm-yyyy")
            self.ent_new_def.grid(row=2, column=1, padx=5, pady=2)
            if curr_val:
                try:
                    self.ent_new_def.set_date(datetime.datetime.strptime(curr_val, "%d-%m-%Y"))
                except Exception:
                    self.ent_new_def.set_date(datetime.date.today())
            else:
                self.ent_new_def.set_date(datetime.date.today())
        else:
            self.lbl_new_def.config(text="Default Amt:")
            self.ent_new_def = ttk.Entry(parent, width=18)
            self.ent_new_def.grid(row=2, column=1, padx=5, pady=2)
            self.ent_new_def.insert(0, curr_val if curr_val else "0.0")

    def toggle_aadhaar_setting(self):
        self.settings["enable_aadhaar"] = bool(self.aadhaar_var.get())
        save_settings(self.settings)
        self.apply_aadhaar_visibility()

    def toggle_theme(self):
        current_theme = tb.Style().theme.name
        new_theme = "superhero" if current_theme == "cosmo" else "cosmo"
        tb.Style().theme_use(new_theme)
        
        self.settings["theme"] = new_theme
        save_settings(self.settings)
        
        # Update watermark background if it exists
        if hasattr(self, "watermark_lbl") and self.watermark_lbl.winfo_exists():
            self.watermark_lbl.configure(background=tb.Style().colors.bg)
            
        # Re-apply some custom styles that get lost on theme switch
        style = tb.Style()
        style.map("Treeview", background=[("selected", "#007bff")], foreground=[("selected", "white")])
        style.configure("Treeview", fieldbackground=style.colors.bg)
        style.configure("TNotebook.Tab", padding=(20, 10), font=("Segoe UI", 11, "bold"))

        # Update total row colors if report tree exists
        if getattr(self, "rep_tree", None) and self.rep_tree.exists("total"):
            if new_theme == "superhero":
                self.rep_tree.tag_configure("total_row", font=("TkDefaultFont", 10, "bold"), background="#1a2b3c", foreground="white")
            else:
                self.rep_tree.tag_configure("total_row", font=("TkDefaultFont", 10, "bold"), background="#d9edf7", foreground="black")
        
    def save_title_settings(self):
        self.settings["office_name"] = self.set_office.get().strip()
        save_settings(self.settings)
        self.update_title()
        messagebox.showinfo("Saved", "Office header title updated.")

    def sync_period_from_settings(self, event=None):
        if not hasattr(self, "_syncing"): self._syncing = False
        if self._syncing: return
        self._syncing = True
        self.settings["from_date"] = self.set_fdate.get().strip()
        self.settings["to_date"] = self.set_tdate.get().strip()
        save_settings(self.settings)
        try:
            self.flt_from_date.set_date(datetime.datetime.strptime(self.settings["from_date"], "%d-%m-%Y"))
            self.flt_to_date.set_date(datetime.datetime.strptime(self.settings["to_date"], "%d-%m-%Y"))
            if hasattr(self, "ent_entry_fdate"):
                self.ent_entry_fdate.set_date(datetime.datetime.strptime(self.settings["from_date"], "%d-%m-%Y"))
                self.ent_entry_tdate.set_date(datetime.datetime.strptime(self.settings["to_date"], "%d-%m-%Y"))
        except Exception:
            pass
        self._syncing = False

    def apply_period_setting(self):
        self.sync_period_from_settings()
        messagebox.showinfo("Period Applied", "Date constraints applied successfully.")

    def apply_default_currency(self):
        val = self.cmb_set_curr.get()
        if val:
            self.settings["currency"] = val
            save_settings(self.settings)
            messagebox.showinfo("Saved", f"Default currency set to {val}.")

    def insert_currency(self):
        new_c = self.ent_new_curr.get().strip()
        if not new_c:
            return
        curr_list = self.settings.get("currencies", [])
        if new_c not in curr_list:
            curr_list.append(new_c)
            self.settings["currencies"] = curr_list
            save_settings(self.settings)

            self.cmb_set_curr["values"] = curr_list
            self.refresh_entry_dropdowns()
            self.ent_new_curr.delete(0, tk.END)
            messagebox.showinfo("Added", "Currency added successfully.")

    def delete_currency(self):
        target_c = self.cmb_set_curr.get()
        if not target_c:
            messagebox.showwarning("No Selection", "Select a currency from the default dropdown to delete.")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE LOWER(currency)=LOWER(?)", (target_c,))
        count = cursor.fetchone()[0]
        conn.close()

        if count > 0:
            messagebox.showerror(
                "Deletion Blocked",
                f"Cannot delete currency '{target_c}'.\n\n"
                f"There are {count} recorded entries passed using this currency.\n"
                "Delete those entries from the report table first, then delete the currency afterward.",
            )
            return

        curr_list = self.settings.get("currencies", [])
        if target_c in curr_list:
            curr_list.remove(target_c)
            self.settings["currencies"] = curr_list
            if curr_list:
                self.settings["currency"] = curr_list[0]
                self.cmb_set_curr.set(curr_list[0])
            else:
                self.settings["currency"] = ""
                self.cmb_set_curr.set("")

            save_settings(self.settings)
            self.cmb_set_curr["values"] = curr_list
            self.refresh_entry_dropdowns()
            messagebox.showinfo("Deleted", f"Currency '{target_c}' deleted successfully.")

    def refresh_settings_heads_list(self):
        for item in self.tree_heads.get_children():
            self.tree_heads.delete(item)
        for item in self.settings.get("account_heads", []):
            head_type = item.get("type", "Amount")
            def_val = item.get("default", "")
            if head_type == "Amount" and isinstance(def_val, float):
                def_val = int(def_val) if def_val.is_integer() else def_val
            self.tree_heads.insert("", "end", values=("☰", item["head"], head_type, def_val))

    def _tree_drag_start(self, event):
        region = self.tree_heads.identify_region(event.x, event.y)
        if region == "nothing":
            self.tree_heads.selection_remove(self.tree_heads.selection())
            self._drag_item = None
            self.ent_new_head.delete(0, tk.END)
            self.cmb_new_type.set("Amount")
            self.on_head_type_change()
            self.ent_new_def.delete(0, tk.END)
            self.ent_new_def.insert(0, "")
            return
        self._drag_item = self.tree_heads.identify_row(event.y)

    def _tree_drag_motion(self, event):
        target = self.tree_heads.identify_row(event.y)
        if target and self._drag_item and target != self._drag_item:
            self.tree_heads.move(self._drag_item, '', self.tree_heads.index(target))
            
    def _tree_drag_release(self, event):
        if hasattr(self, '_drag_item') and self._drag_item:
            # Sync settings to new order
            new_heads = []
            for child in self.tree_heads.get_children():
                values = self.tree_heads.item(child, "values")
                h_name, h_type, h_def = values[1], values[2], values[3]
                try:
                    if h_type == "Amount" and str(h_def).strip() == "":
                        h_def = ""
                    else:
                        h_def = float(h_def) if h_type == "Amount" else str(h_def)
                except ValueError:
                    h_def = ""
                new_heads.append({"head": h_name, "type": h_type, "default": h_def})
            self.settings["account_heads"] = new_heads
            save_settings(self.settings)
            self.build_dynamic_account_inputs()
            self._drag_item = None

    def _tree_hover(self, event):
        col = self.tree_heads.identify_column(event.x)
        if col == "#1":
            if not hasattr(self, "_tt_win") or not self._tt_win:
                self._tt_win = tk.Toplevel(self.root)
                self._tt_win.wm_overrideredirect(True)
                lbl = tk.Label(self._tt_win, text="Drag to reorder in entry form", background="#ffffe0", relief="solid", borderwidth=1)
                lbl.pack(ipadx=2, ipady=1)
            x = self.root.winfo_pointerx() + 15
            y = self.root.winfo_pointery() + 15
            self._tt_win.wm_geometry(f"+{x}+{y}")
        else:
            self._tree_leave()

    def _tree_leave(self, event=None):
        if hasattr(self, "_tt_win") and self._tt_win:
            self._tt_win.destroy()
            self._tt_win = None

    def add_account_head(self):
        h_name = self.ent_new_head.get().strip()
        h_type = self.cmb_new_type.get()
        
        if h_type == "Amount":
            h_def_str = self.ent_new_def.get().strip()
            if not h_def_str:
                h_def = ""
            else:
                try:
                    h_def = float(h_def_str)
                except ValueError:
                    messagebox.showerror("Error", "Default amount must be a number.")
                    return
        else:
            h_def = self.ent_new_def.get().strip()

        if not h_name:
            return

        heads_list = self.settings.get("account_heads", [])
        updated = False
        for item in heads_list:
            # Case-insensitive match to overwrite existing existing entries
            if item["head"].lower() == h_name.lower():
                item["default"] = h_def
                item["type"] = h_type
                updated = True
                break

        if not updated:
            heads_list.append({"head": h_name, "type": h_type, "default": h_def})

        self.settings["account_heads"] = heads_list
        save_settings(self.settings)

        self.refresh_settings_heads_list()
        self.build_dynamic_account_inputs()
        self.refresh_report_filters()
        self.ent_new_head.delete(0, tk.END)
        self.cmb_new_type.set("Amount")
        self.on_head_type_change()
        self.ent_new_def.delete(0, tk.END)
        self.ent_new_def.insert(0, "")

    def delete_account_head(self):
        selected = self.tree_heads.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an Account Head to delete.")
            return

        item_values = self.tree_heads.item(selected[0], "values")
        if item_values and len(item_values) > 1:
            target_head = item_values[1]
        else:
            idx = self.tree_heads.index(selected[0])
            heads_list = self.settings.get("account_heads", [])
            if 0 <= idx < len(heads_list):
                target_head = heads_list[idx].get("head")
            else:
                return

        if not target_head:
            return

        # Check if head has active financial usage in the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, account_data FROM transactions")
        rows = cursor.fetchall()

        active_count = 0
        txs_with_head = []
        for tx_id, acc_data_str in rows:
            try:
                acc_data = json.loads(acc_data_str)
                if target_head in acc_data:
                    txs_with_head.append((tx_id, acc_data))
                    val = acc_data[target_head]
                    if isinstance(val, (int, float)) and abs(val) > 1e-6:
                        active_count += 1
                    elif isinstance(val, str) and val.strip() != "":
                        active_count += 1
            except Exception:
                pass

        if active_count > 0:
            conn.close()
            messagebox.showerror(
                "Deletion Blocked",
                f"Cannot delete Account Head '{target_head}'.\n\n"
                f"There are {active_count} recorded transaction(s) with active contributions under this head.\n"
                "To preserve financial integrity, you must delete or modify those transactions before deleting this head."
            )
            return

        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete the account head '{target_head}'?"
        ):
            conn.close()
            return

        # Cleanly purge any zero/empty keys for target_head from transactions.account_data in paljor_contribution.db so no orphan keys remain
        for tx_id, acc_data in txs_with_head:
            if target_head in acc_data:
                del acc_data[target_head]
                cursor.execute(
                    "UPDATE transactions SET account_data=? WHERE id=?",
                    (json.dumps(acc_data), tx_id)
                )
        conn.commit()
        conn.close()

        # Remove the head from heads_list and update self.settings["account_heads"]
        heads_list = self.settings.get("account_heads", [])
        self.settings["account_heads"] = [h for h in heads_list if h.get("head") != target_head]
        save_settings(self.settings)

        # Synchronize the entire UI immediately
        self.refresh_settings_heads_list()
        self.build_dynamic_account_inputs()
        self.refresh_report_filters()

        # Clear settings form input fields
        self.ent_new_head.delete(0, tk.END)
        self.cmb_new_type.set("Amount")
        self.on_head_type_change()
        self.ent_new_def.delete(0, tk.END)
        self.ent_new_def.insert(0, "")

        # Provide user feedback
        messagebox.showinfo("Deleted", f"Account head '{target_head}' was deleted successfully.")

    def add_location(self):
        country = self.cmb_geo_country.get().strip()
        place = self.ent_new_place.get().strip()

        if not country or not place:
            messagebox.showwarning("Error", "Enter both Country and Place.")
            return

        if country not in self.settings["countries"]:
            self.settings["countries"][country] = []

        if place not in self.settings["countries"][country]:
            self.settings["countries"][country].append(place)

        save_settings(self.settings)
        self.cmb_geo_country["values"] = list(self.settings["countries"].keys())
        self.ent_new_place.delete(0, tk.END)
        messagebox.showinfo("Added", f"Successfully added {place} to {country}.")


if __name__ == "__main__":
    # Set explicit Windows AppUserModelID so the Windows taskbar shows our custom icon (not the Tk feather)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CTA.Rangtsok.ContributionApp.1")
        except Exception:
            pass

    # Load settings early just for theme
    import os, json
    init_theme = "cosmo"
    if os.path.exists("settings.json"):
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                init_theme = json.load(f).get("theme", "cosmo")
        except:
            pass
    root = tb.Window(themename=init_theme, iconphoto=None)
    # Hide window while building UI & applying emblem icon so the default Tk feather never flashes
    root.withdraw()
    style = tb.Style()
    style.map("Treeview", background=[("selected", "#007bff")], foreground=[("selected", "white")])
    style.configure("Treeview", fieldbackground=style.colors.bg)
    style.configure("TNotebook.Tab", padding=(20, 10), font=("Segoe UI", 11, "bold"))
    app = ContributionApp(root)
    root.deiconify()
    try:
        root.state("zoomed")
    except Exception:
        pass
    app._apply_window_icon()
    root.mainloop()