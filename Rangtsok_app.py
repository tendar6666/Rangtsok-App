import csv
import datetime
import json
import os
import re

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
        self.de = TBDateEntry(self, bootstyle="primary", width=width, dateformat="%d-%m-%Y")
        self.de.pack(fill="both", expand=True)

    def get(self):
        return self.de.entry.get()

    def set_date(self, date_obj):
        self.de.entry.delete(0, tk.END)
        self.de.entry.insert(0, date_obj.strftime("%d-%m-%Y"))

    def bind(self, sequence=None, func=None, add=None):
        self.de.bind(sequence, func, add)
        self.de.entry.bind(sequence, func, add)
        
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


def parse_ui_date(dd_mm_yyyy):
    """Convert DD-MM-YYYY to YYYY-MM-DD for accurate SQLite range sorting."""
    try:
        return datetime.datetime.strptime(dd_mm_yyyy, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
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


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS gb_database (
            gb_number TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """
    )
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
    conn.commit()
    conn.close()


# --- MAIN APPLICATION CLASS ---
class ContributionApp:

    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        init_db()

        self.current_edit_id = None

        self.update_title()
        self.root.geometry("1200x850")
        self.root.minsize(850, 600)
        
        # Maximize the window on startup
        try:
            self.root.state("zoomed")
        except Exception:
            pass

        # Set App Icon and Background Watermark
        try:
            if os.path.exists("logo.png"):
                img = Image.open("logo.png").convert("RGBA")
                # Set App Window Icon
                icon_img = ImageTk.PhotoImage(img)
                self.root.iconphoto(False, icon_img)
                self.root.icon_img = icon_img  # keep ref

        except Exception as e:
            print("Logo load error:", e)

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

    def update_title(self):
        office = self.settings.get("office_name", "Office of Tibet")
        self.root.title(f"Voluntary Contribution Recording System | {office}")

    def on_tab_change(self, event):
        self.update_title()
        
        # Only refresh the specific tab that was clicked to prevent massive lag
        selected_tab = self.notebook.index(self.notebook.select())
        
        if selected_tab == 0:  # Entry Form
            self.refresh_entry_dropdowns()
            if not getattr(self, "current_edit_id", None):
                # We only rebuild if needed, but doing it once per tab visit is much better than every click
                self.build_dynamic_account_inputs()
        elif selected_tab == 1:  # GB Database
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
        self.ent_gb.bind("<FocusOut>", self.lookup_gb)
        self.ent_gb.bind("<Return>", self.lookup_gb)

        btn_lookup = ttk.Button(frame_gb, text="🔍 Lookup", command=self.lookup_gb)
        btn_lookup.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(frame_gb, text="Full Name:").grid(row=0, column=3, sticky="w", padx=10, pady=5)
        self.ent_name = ttk.Entry(frame_gb, width=30)
        self.ent_name.grid(row=0, column=4, padx=5, pady=5)

        self.lbl_gb_status = ttk.Label(frame_gb, text="", font=("Arial", 9, "italic"))
        self.lbl_gb_status.grid(row=0, column=5, padx=10, pady=5)

        self.btn_update_name = ttk.Button(
            frame_gb, text="Update Name in DB", state="disabled", command=self.update_gb_name
        )
        self.btn_update_name.grid(row=0, column=6, padx=5, pady=5)

        self.frame_heads = ttk.LabelFrame(self.tab_entry, text="Contribution Amounts", padding=10)
        lbl_info_logic = tk.Label(self.frame_heads, text="ⓘ How dates work", fg="#007bff", cursor="hand2", font=("Segoe UI", 9, "bold"))
        lbl_info_logic.place(relx=1.0, rely=0.0, anchor="ne", x=-5, y=5)
        ToolTip(lbl_info_logic, "Date Logic Explanation:\n\n1. Start/End Dates are auto-filled from your 'FY Period From/To' settings.\n2. If you change a date here, the app assumes you are paying for that specific period.\n3. This allows you to log Back-Arrears or Advance Payments separate from the current FY.\n4. Syncs automatically with the main FY fields at the top!")
        self.frame_heads.pack(fill="both", expand=True, padx=15, pady=5)

        self.head_entries = {}
        self.build_dynamic_account_inputs()

        frame_actions = ttk.Frame(self.tab_entry)
        frame_actions.pack(fill="x", padx=15, pady=10)

        self.btn_save_tx = ttk.Button(
            frame_actions, text="💾 Save Contribution Entry", command=self.save_entry
        )
        self.btn_save_tx.pack(side="left", padx=5)

        btn_clear = ttk.Button(frame_actions, text="🔄 Clear Form", command=self.clear_entry_form)
        btn_clear.pack(side="left", padx=5)

        self.refresh_entry_dropdowns()
        self.auto_set_next_receipt()

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

    def on_entry_currency_change(self, event=None):
        curr_symbol = self.cmb_entry_currency.get().split()[0]
        for head_name, (lbl, ent, head_type) in self.head_entries.items():
            if head_type == "Amount":
                lbl.config(text=f"{head_name} ({curr_symbol}):")
            else:
                lbl.config(text=f"{head_name}:")
        self.lbl_total_title.config(text=f"TOTAL AMOUNT ({curr_symbol}):")

    def build_dynamic_account_inputs(self):
        for widget in self.frame_heads.winfo_children():
            widget.destroy()

        self.head_entries.clear()
        curr_symbol = self.cmb_entry_currency.get().split()[0] if self.cmb_entry_currency.get() else ""

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

    def lookup_gb(self, event=None):
        gb_num = self.ent_gb.get().strip()
        if not gb_num:
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM gb_database WHERE LOWER(gb_number) = LOWER(?)", (gb_num,))
        result = cursor.fetchone()
        conn.close()

        self.ent_name.delete(0, tk.END)
        if result:
            self.ent_name.insert(0, result[0])
            self.lbl_gb_status.config(text="✓ GB Found", foreground="green")
            self.btn_update_name.config(state="normal")
        else:
            self.lbl_gb_status.config(text="⚠ Data not found. Enter Name to add.", foreground="red")
            self.btn_update_name.config(state="normal")

    def update_gb_name(self):
        gb_num = self.ent_gb.get().strip()
        name = self.ent_name.get().strip()

        if not gb_num or not name:
            messagebox.showwarning("Missing Data", "Both GB Number and Name must be filled.")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO gb_database (gb_number, name) VALUES (?, ?)", (gb_num, name)
        )
        conn.commit()
        conn.close()

        self.lbl_gb_status.config(text="✓ Database Updated", foreground="blue")
        self.refresh_db_table()

    def auto_set_next_receipt(self):
        if self.current_edit_id:
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT receipt_no FROM transactions ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()

        self.ent_receipt.delete(0, tk.END)
        if result:
            try:
                old_rec = result[0]
                num_part = "".join(filter(str.isdigit, old_rec))
                if num_part:
                    next_num = int(num_part) + 1
                    new_rec = old_rec.replace(num_part, str(next_num))
                    self.ent_receipt.insert(0, new_rec)
                else:
                    self.ent_receipt.insert(0, old_rec + "_1")
            except Exception:
                self.ent_receipt.insert(0, "")
        else:
            self.ent_receipt.insert(0, "100000")

    def save_entry(self):
        receipt = self.ent_receipt.get().strip()
        gb_num = self.ent_gb.get().strip()
        name = self.ent_name.get().strip()
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

        cursor.execute("INSERT OR IGNORE INTO gb_database (gb_number, name) VALUES (?, ?)", (gb_num, name))

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

        messagebox.showinfo("Success", f"{msg}\nTotal: {total:,.2f} {currency.split()[0]}")
        self.clear_entry_form()
        self.auto_set_next_receipt()
        self.refresh_db_table()

    def clear_entry_form(self):
        self.current_edit_id = None
        self.btn_save_tx.config(text="💾 Save Contribution Entry")
        self.lbl_edit_warning.config(text="")

        self.ent_gb.delete(0, tk.END)
        self.ent_name.delete(0, tk.END)
        self.lbl_gb_status.config(text="")
        self.btn_update_name.config(state="disabled")

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

    def load_entry_for_edit(self, tx_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT receipt_no, gb_number, name, country, place, currency, tx_date, account_data FROM transactions WHERE id=?",
            (tx_id,),
        )
        row = cursor.fetchone()
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
2. Copy two columns: GB Number (left) and Name (right)
3. Click this button to paste them instantly into the database!""""")

        btn_clean = ttk.Button(
            frame_controls, text="🧹 Clean Database", command=self.cleanse_gb_database
        )
        btn_clean.pack(side="left", padx=(5, 0))
        lbl_info_clean = tk.Label(frame_controls, text=" ⓘ", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_clean.pack(side="left", padx=(0, 15))
        ToolTip(lbl_info_clean, """""Clean Database:
This scans the entire database for duplicates.
If someone has multiple entries, it merges them, keeping the longest name.
It also removes blank rows and fixes formatting issues.""""")

        btn_del_gb = ttk.Button(
            frame_controls, text="❌ Delete Selected", command=self.delete_selected_gbs
        )
        btn_del_gb.pack(side="right", padx=5)

        btn_backup = ttk.Button(frame_controls, text="💾 Backup Database", command=self.backup_db)
        btn_backup.pack(side="right", padx=5)

        frame_table = ttk.LabelFrame(self.tab_db, text="Green Book Master Records", padding=10)
        frame_table.pack(fill="both", expand=True, padx=15, pady=5)

        self.db_tree = ttk.Treeview(frame_table, columns=("gb", "name"), show="headings")
        self.db_tree.heading("gb", text="Green Book Number")
        self.db_tree.heading("name", text="Full Name")
        self.db_tree.column("gb", width=200, anchor="center")
        self.db_tree.column("name", width=600, anchor="w")
        self.db_tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.db_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.db_tree.configure(yscrollcommand=scrollbar.set)

        self.refresh_db_table()

    def refresh_db_table(self):
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT gb_number, name FROM gb_database ORDER BY gb_number")
        for row in cursor.fetchall():
            self.db_tree.insert("", "end", values=row)
        conn.close()

    def import_from_clipboard(self):
        try:
            clipboard_data = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("Clipboard Empty", "No data found in clipboard. Copy from Excel first.")
            return

        lines = clipboard_data.split("\n")
        imported, skipped = 0, 0

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        for line in lines:
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                gb_num = parts[0].strip()
                name = parts[1].strip()
                if gb_num and name:
                    cursor.execute(
                        "INSERT OR REPLACE INTO gb_database (gb_number, name) VALUES (?, ?)", (gb_num, name)
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
        cursor.execute("SELECT gb_number, name FROM gb_database")
        rows = cursor.fetchall()

        unique_gbs = {}
        duplicates_removed = 0

        # Process and deduplicate in memory
        for old_gb, old_name in rows:
            # Clean GB: force lowercase, strip spaces and special characters
            clean_gb = re.sub(r"[-\s#/|\\]", "", old_gb).lower()
            # Proper case Name
            clean_name = old_name.title()

            if clean_gb not in unique_gbs:
                unique_gbs[clean_gb] = clean_name
            else:
                duplicates_removed += 1  # Skip duplicate GB entirely

        # Wipe old table and bulk insert the clean, 100% unique data
        cursor.execute("DELETE FROM gb_database")
        
        for gb_key, name_val in unique_gbs.items():
            cursor.execute(
                "INSERT INTO gb_database (gb_number, name) VALUES (?, ?)",
                (gb_key, name_val),
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
        frame_filters = ttk.LabelFrame(self.tab_reports, text="Search & Filter Parameters", padding=10)
        frame_filters.pack(fill="x", padx=15, pady=5)

        ttk.Label(frame_filters, text="From Date:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.flt_from_date = DateEntry(
            frame_filters, width=12, background="darkblue", foreground="white", date_pattern="dd-mm-yyyy"
        )
        self.flt_from_date.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame_filters, text="To Date:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.flt_to_date = DateEntry(
            frame_filters, width=12, background="darkblue", foreground="white", date_pattern="dd-mm-yyyy"
        )
        self.flt_to_date.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(frame_filters, text="Country:").grid(row=0, column=4, sticky="w", padx=5, pady=5)
        self.flt_country = ttk.Combobox(frame_filters, state="readonly", width=12)
        self.flt_country.grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(frame_filters, text="Place:").grid(row=0, column=6, sticky="w", padx=5, pady=5)
        self.flt_place = ttk.Combobox(frame_filters, state="readonly", width=12)
        self.flt_place.grid(row=0, column=7, padx=5, pady=5)

        ttk.Label(frame_filters, text="Currency:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.flt_currency = ttk.Combobox(frame_filters, state="readonly", width=12)
        self.flt_currency.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(frame_filters, text="Name Search:").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.flt_name = ttk.Entry(frame_filters, width=12)
        self.flt_name.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(frame_filters, text="GB Number:").grid(row=1, column=4, sticky="w", padx=5, pady=5)
        self.flt_gb = ttk.Entry(frame_filters, width=12)
        self.flt_gb.grid(row=1, column=5, padx=5, pady=5)

        ttk.Label(frame_filters, text="Account Head:").grid(row=1, column=6, sticky="w", padx=5, pady=5)
        self.flt_head = ttk.Combobox(frame_filters, state="readonly", width=12)
        self.flt_head.grid(row=1, column=7, padx=5, pady=5)

        btn_filter = ttk.Button(frame_filters, text="🔍 Run Report", command=self.run_report)
        btn_filter.grid(row=0, column=8, rowspan=2, padx=10, pady=5)

        btn_export = ttk.Button(frame_filters, text="📥 Export Excel", command=self.export_report)
        btn_export.grid(row=0, column=9, padx=5, pady=2)

        btn_import = ttk.Button(frame_filters, text="📤 Import Excel", command=self.import_batch_excel)
        btn_import.grid(row=1, column=9, padx=5, pady=2)

        btn_del_batch = ttk.Button(
            frame_filters, text="❌ Delete Batch", command=self.delete_batch_transactions
        )
        btn_del_batch.grid(row=0, column=10, rowspan=2, padx=5, pady=5)

        # --- INSTRUCTIONAL TIPS ---
        frame_tips = ttk.Frame(self.tab_reports)
        frame_tips.pack(fill="x", padx=15, pady=2)

        ttk.Label(
            frame_tips, 
            text="💡 Edit Tip: Double-click any row below to open it in the Entry Form for instant updates.", 
            font=("Arial", 9, "italic")
        ).pack(anchor="w")

        ttk.Label(
            frame_tips, 
            text="💡 Import Tip: To prevent Excel date errors, export a report first to get the exact layout, then paste your new entries into that sheet.", 
            font=("Arial", 9, "bold"),
            foreground="darkgreen"
        ).pack(anchor="w")

        self.frame_rep_table = ttk.LabelFrame(self.tab_reports, text="Filtered Contributions", padding=5)
        self.frame_rep_table.pack(fill="both", expand=True, padx=15, pady=5)

        self.rep_tree = None
        self.current_report_df = pd.DataFrame()
        self.current_report_raw_ids = []
        
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

        if self.flt_name.get().strip():
            query += " AND name LIKE ?"
            params.append(f"%{self.flt_name.get().strip()}%")

        if self.flt_gb.get().strip():
            query += " AND gb_number LIKE ?"
            params.append(f"%{self.flt_gb.get().strip()}%")

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        parsed_rows = []
        self.current_report_raw_ids.clear()
        all_heads = [h["head"] for h in self.settings.get("account_heads", [])]

        for r in rows:
            self.current_report_raw_ids.append(r[0])
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
                if data_json.get(selected_head, 0.0) <= 0:
                    self.current_report_raw_ids.pop()
                    continue

            for h in all_heads:
                base[h] = data_json.get(h, 0.0)

            base["Total"] = r[9]
            parsed_rows.append(base)

        self.current_report_df = pd.DataFrame(parsed_rows)

        for w in self.frame_rep_table.winfo_children():
            w.destroy()

        if self.current_report_df.empty:
            ttk.Label(self.frame_rep_table, text="No records match your filters.").pack(pady=20)
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

        for c in cols:
            self.rep_tree.heading(c, text=c)
            w_size = 180 if c == "Name" else 110
            self.rep_tree.column(c, width=w_size, anchor="center" if c != "Name" else "w", minwidth=90, stretch=False)
            
        self.rep_tree.bind("<Double-1>", self._rep_tree_auto_resize_column)

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
                    is_amount = False
                    for h in self.settings.get("account_heads", []):
                        if h["head"] == col and h.get("type", "Amount") == "Amount":
                            is_amount = True
                            break
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
        
        curr_symbol = self.settings.get("currency", "").split()[0]
        self.lbl_rep_summary.config(
            text=f"Total Displayed Records: {total_records}   |   IMMEDIATE SUM TOTAL: {immediate_sum:,.2f} {curr_symbol}"
        )

    def on_report_double_click(self, event):
        selected = self.rep_tree.selection()
        if not selected:
            return
        if selected[0] == "total":
            return
        idx = int(selected[0])
        tx_id = self.current_report_raw_ids[idx]
        self.load_entry_for_edit(tx_id)

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
        if region != "separator":
            return
            
        col = self.rep_tree.identify_column(event.x)
        if not col:
            return
            
        col_idx = int(col.replace('#', '')) - 1
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
            if hasattr(val, "strftime"):
                val_str = val.strftime("%d-%m-%Y")
            else:
                val_str = str(val).strip()

            parsed = parse_ui_date(val_str)
            if not parsed:
                bad_dates.append(f"Row {idx+2}: '{val_str}'")

        if bad_dates:
            err_msg = (
                "IMPORT REJECTED: Invalid 'Transaction Date' formats detected.\n"
                "Dates must strictly match the DD-MM-YYYY format (e.g., 30-01-2026).\n\n"
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
            if hasattr(raw_d, "strftime"):
                d_str = raw_d.strftime("%d-%m-%Y")
            else:
                d_str = str(raw_d).strip()
            tx_date_db = parse_ui_date(d_str)

            acc_data = {}
            for item in self.settings.get("account_heads", []):
                h = item["head"]
                h_type = item.get("type", "Amount")
                val = row[h]
                if h_type == "Amount":
                    try:
                        acc_data[h] = float(val)
                    except Exception:
                        acc_data[h] = 0.0
                else:
                    if hasattr(val, "strftime"):
                        acc_data[h] = val.strftime("%d-%m-%Y")
                    else:
                        acc_data[h] = str(val).strip() if pd.notna(val) else ""

            total = float(row["Total"]) if "Total" in row else sum(v for v in acc_data.values() if isinstance(v, (int, float)))

            cursor.execute(
                "INSERT OR IGNORE INTO gb_database (gb_number, name) VALUES (?, ?)", (gb_num, name)
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
        btn_theme.grid(row=0, column=3, padx=30, pady=5)

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
        self.ent_new_head.delete(0, tk.END)
        self.cmb_new_type.set("Amount")
        self.on_head_type_change()
        self.ent_new_def.delete(0, tk.END)
        self.ent_new_def.insert(0, "")

    def delete_account_head(self):
        selected = self.tree_heads.selection()
        if not selected:
            return
        idx = self.tree_heads.index(selected[0])
        heads_list = self.settings.get("account_heads", [])
        
        target_head = heads_list[idx]["name"]
        
        # Check if head is used in the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE account_data LIKE ?", (f'%"{target_head} (%',))
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            messagebox.showerror(
                "Deletion Blocked",
                f"Cannot delete Account Head '{target_head}'.\n\n"
                f"There are {count} recorded entries in the database using this head.\n"
                "You must delete those entries from the GB Database/Report first before deleting the head."
            )
            return

        heads_list.pop(idx)
        self.settings["account_heads"] = heads_list
        save_settings(self.settings)
        self.refresh_settings_heads_list()

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
    # Load settings early just for theme
    import os, json
    init_theme = "cosmo"
    if os.path.exists("settings.json"):
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                init_theme = json.load(f).get("theme", "cosmo")
        except:
            pass
    root = tb.Window(themename=init_theme)
    style = tb.Style()
    style.map("Treeview", background=[("selected", "#007bff")], foreground=[("selected", "white")])
    style.configure("Treeview", fieldbackground=style.colors.bg)
    style.configure("TNotebook.Tab", padding=(20, 10), font=("Segoe UI", 11, "bold"))
    app = ContributionApp(root)
    root.mainloop()