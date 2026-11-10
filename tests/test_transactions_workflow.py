"""Integration tests covering end-to-end transaction workflows in Rangtsok App.

Covers:
1. Saving a new transaction via UI form, auto-increment receipt, and DB persistence.
2. Auto-increment receipt numbering patterns and preservation across saves.
3. Double-clicking a report row to load an existing record, modifying amount, and re-saving.
4. Deleting a transaction with confirmation and DB deletion.
5. Green Book auto-lookup (lookup_gb via Tab/FocusOut and Enter/Return bindings, name updates).
6. Dynamic real-time calculation of totals across configured account heads.
7. Report filtering by date range, GB number, country, place, and account head, plus totals.
8. Excel export (export_report) and database backup creation (backup_db).
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
import sqlite3
import shutil
import tempfile
import datetime
import tkinter as tk
import ttkbootstrap as tb
import pandas as pd

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import Rangtsok_app


class TestTransactionsWorkflow(unittest.TestCase):
    """End-to-end integration tests for contribution transaction workflows."""

    @classmethod
    def setUpClass(cls):
        # Create a single hidden root for headless testing
        cls.root = tb.Window(themename="cosmo")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        # Create an isolated temporary directory for test database and settings
        self.temp_dir = tempfile.mkdtemp()
        self.test_settings_path = os.path.join(self.temp_dir, "settings.json")
        self.test_db_path = os.path.join(self.temp_dir, "paljor_contribution.db")

        # Copy original settings or use defaults
        orig_settings_path = os.path.join(WORKSPACE_ROOT, "settings.json")
        if os.path.exists(orig_settings_path):
            shutil.copy(orig_settings_path, self.test_settings_path)
        else:
            with open(self.test_settings_path, "w", encoding="utf-8") as f:
                json.dump(Rangtsok_app.DEFAULT_SETTINGS, f, indent=4)

        # Patch module-level paths to isolated test paths
        self.orig_settings_file = Rangtsok_app.SETTINGS_FILE
        self.orig_db_file = Rangtsok_app.DB_FILE
        Rangtsok_app.SETTINGS_FILE = self.test_settings_path
        Rangtsok_app.DB_FILE = self.test_db_path

        # Initialize test database schema
        Rangtsok_app.init_db()

        # Instantiate the application
        self.app = Rangtsok_app.ContributionApp(self.root)

    def tearDown(self):
        # Restore module-level paths
        Rangtsok_app.SETTINGS_FILE = self.orig_settings_file
        Rangtsok_app.DB_FILE = self.orig_db_file

        # Clean up temporary test files
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _insert_sample_transaction(self, receipt="100000", gb="GB-2026-001", name="Tenzin Gyatso",
                                   country="India", place="Dharamshala", currency="INR",
                                   tx_date="2026-05-15", entry_date="2026-05-15",
                                   acc_data=None, total=200.0):
        """Helper to insert a known transaction directly into the test database."""
        if acc_data is None:
            acc_data = {"Chatrel": 150.0, "Meal Strike": 50.0}
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO transactions 
            (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (receipt, gb, name, country, place, currency, tx_date, entry_date, json.dumps(acc_data), total)
        )
        tx_id = cur.lastrowid
        cur.execute("INSERT OR IGNORE INTO gb_database (gb_number, name) VALUES (?, ?)", (gb, name))
        conn.commit()
        conn.close()
        return tx_id

    # =========================================================================
    # 1. NEW TRANSACTION ENTRY, AUTO-INCREMENT & DB PERSISTENCE
    # =========================================================================
    @patch("Rangtsok_app.messagebox.showinfo")
    def test_save_new_transaction_ui_and_db_persistence(self, mock_showinfo):
        """Verifies entering a new transaction via UI form, validating persistence and auto-increment."""
        # 1. Fill UI form fields
        self.app.ent_receipt.delete(0, tk.END)
        self.app.ent_receipt.insert(0, "100000")

        self.app.cmb_country.set("India")
        self.app.on_country_select()
        self.app.cmb_place.set("Dharamshala")

        self.app.cmb_entry_currency.set("INR")
        self.app.on_entry_currency_change()

        self.app.ent_tx_date.set_date(datetime.datetime(2026, 5, 15))
        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "GB-2026-001")
        self.app.ent_name.delete(0, tk.END)
        self.app.ent_name.insert(0, "Tenzin Gyatso")

        # Set account head amounts
        if "Chatrel" in self.app.head_entries:
            _, ent, _ = self.app.head_entries["Chatrel"]
            ent.delete(0, tk.END)
            ent.insert(0, "150.0")

        if "Meal Strike" in self.app.head_entries:
            _, ent, _ = self.app.head_entries["Meal Strike"]
            ent.delete(0, tk.END)
            ent.insert(0, "50.0")

        # Dynamic real-time calculation
        self.app.calculate_realtime_total()
        self.assertEqual(self.app.ent_total_sum.get(), "200.00", "Total sum field must reflect 200.00")

        # 2. Save entry
        self.app.save_entry()
        self.assertTrue(mock_showinfo.called, "messagebox.showinfo should be called on successful save")

        # 3. Verify database persistence in transactions table
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT receipt_no, gb_number, name, country, place, currency, tx_date, account_data, total_amount FROM transactions")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 1, "Exactly one transaction must be stored in the database")

        saved = rows[0]
        self.assertEqual(saved[0], "100000", "Receipt number mismatch")
        self.assertEqual(saved[1], "GB-2026-001", "GB number mismatch")
        self.assertEqual(saved[2], "Tenzin Gyatso", "Name mismatch")
        self.assertEqual(saved[3], "India", "Country mismatch")
        self.assertEqual(saved[4], "Dharamshala", "Place mismatch")
        self.assertEqual(saved[5], "INR", "Currency mismatch")
        self.assertEqual(saved[6], "2026-05-15", "Transaction date must be stored in ISO YYYY-MM-DD")
        self.assertEqual(float(saved[8]), 200.0, "Total amount mismatch")

        acc_json = json.loads(saved[7])
        self.assertEqual(acc_json.get("Chatrel"), 150.0, "Chatrel amount mismatch in JSON")
        self.assertEqual(acc_json.get("Meal Strike"), 50.0, "Meal Strike amount mismatch in JSON")

        # 4. Verify GB was added to gb_database table
        cur.execute("SELECT name FROM gb_database WHERE gb_number=?", ("GB-2026-001",))
        gb_row = cur.fetchone()
        self.assertIsNotNone(gb_row, "GB record must be inserted into gb_database")
        self.assertEqual(gb_row[0], "Tenzin Gyatso")
        conn.close()

        # 5. Verify UI cleared and next receipt number auto-incremented
        self.assertEqual(self.app.ent_gb.get(), "", "GB field must be cleared")
        self.assertEqual(self.app.ent_name.get(), "", "Name field must be cleared")
        self.assertEqual(self.app.ent_receipt.get(), "100001", "Next receipt number must auto-increment to 100001")

    # =========================================================================
    # 2. AUTO-INCREMENT RECEIPT NUMBERING
    # =========================================================================
    @patch("Rangtsok_app.messagebox.showinfo")
    def test_auto_increment_receipt_consecutive_saves(self, mock_showinfo):
        """Verifies consecutive transactions auto-increment the receipt number correctly."""
        # Save first transaction with receipt 100000
        self.app.ent_receipt.delete(0, tk.END)
        self.app.ent_receipt.insert(0, "100000")
        self.app.cmb_country.set("India")
        self.app.on_country_select()
        self.app.cmb_place.set("Dharamshala")
        self.app.cmb_entry_currency.set("INR")
        self.app.ent_tx_date.set_date(datetime.datetime(2026, 5, 10))
        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "GB-001")
        self.app.ent_name.delete(0, tk.END)
        self.app.ent_name.insert(0, "User One")
        self.app.save_entry()

        self.assertEqual(self.app.ent_receipt.get(), "100001", "After 100000, next receipt must be 100001")

        # Save second transaction using auto-set receipt
        self.app.cmb_country.set("India")
        self.app.on_country_select()
        self.app.cmb_place.set("Dharamshala")
        self.app.cmb_entry_currency.set("INR")
        self.app.ent_tx_date.set_date(datetime.datetime(2026, 5, 11))
        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "GB-002")
        self.app.ent_name.delete(0, tk.END)
        self.app.ent_name.insert(0, "User Two")
        self.app.save_entry()

        self.assertEqual(self.app.ent_receipt.get(), "100002", "After 100001, next receipt must be 100002")

    def test_auto_set_next_receipt_patterns(self):
        """Verifies auto_set_next_receipt handles zero-padding and string prefixes."""
        # Test 1: Zero-padded numeric receipt: "000500" -> "000501"
        self._insert_sample_transaction(receipt="000500")
        self.app.auto_set_next_receipt()
        self.assertEqual(self.app.ent_receipt.get(), "000501", "Zero padding must be preserved")

        # Test 2: Prefixed receipt: "REC-0019" -> "REC-0020"
        self._insert_sample_transaction(receipt="REC-0019")
        self.app.auto_set_next_receipt()
        self.assertEqual(self.app.ent_receipt.get(), "REC-0020", "Prefixed zero-padded number must increment correctly")

        # Test 3: Do not overwrite receipt when editing an existing record
        self.app.current_edit_id = 999
        self.app.ent_receipt.delete(0, tk.END)
        self.app.ent_receipt.insert(0, "KEEP-MY-RECEIPT")
        self.app.auto_set_next_receipt()
        self.assertEqual(self.app.ent_receipt.get(), "KEEP-MY-RECEIPT", "Receipt must not change while editing")

    # =========================================================================
    # 3. DOUBLE-CLICK LOAD, EDIT AND RESAVE
    # =========================================================================
    @patch("Rangtsok_app.messagebox.showinfo")
    def test_double_click_load_modify_and_resave_transaction(self, mock_showinfo):
        """Verifies loading record via report double-click, modifying amount, and updating DB."""
        # 1. Seed a transaction
        tx_id = self._insert_sample_transaction(
            receipt="100050", gb="GB-2026-050", name="Kelsang Tsering",
            country="India", place="Dharamshala", currency="INR",
            tx_date="2026-05-20", acc_data={"Chatrel": 150.0}, total=150.0
        )

        # 2. Run report to populate rep_tree
        self.app.run_report()
        self.assertIsNotNone(self.app.rep_tree, "Report treeview must exist after run_report")
        children = self.app.rep_tree.get_children()
        # First child is row "0" (the data row), second child is "total" row
        self.assertIn("0", children, "Row index 0 must be present in report tree")

        # 3. Select row and simulate double click
        self.app.rep_tree.selection_set("0")
        self.app.on_report_double_click()

        # 4. Verify fields loaded into Entry Form
        self.assertEqual(self.app.current_edit_id, tx_id, "current_edit_id must match loaded transaction ID")
        self.assertEqual(self.app.ent_receipt.get(), "100050", "Loaded receipt mismatch")
        self.assertEqual(self.app.ent_gb.get(), "GB-2026-050", "Loaded GB number mismatch")
        self.assertEqual(self.app.ent_name.get(), "Kelsang Tsering", "Loaded Name mismatch")
        self.assertEqual(self.app.cmb_country.get(), "India", "Loaded Country mismatch")
        self.assertEqual(self.app.cmb_place.get(), "Dharamshala", "Loaded Place mismatch")
        self.assertEqual(self.app.cmb_entry_currency.get(), "INR", "Loaded Currency mismatch")
        self.assertIn("EDITING EXISTING RECORD", self.app.lbl_edit_warning.cget("text"))
        self.assertEqual(self.app.btn_save_tx.cget("text"), "💾 Update Contribution Entry")

        # Verify active tab switched to Entry tab
        selected_tab = self.app.notebook.select()
        self.assertEqual(selected_tab, str(self.app.tab_entry), "Must switch to Entry tab on double-click")

        # 5. Modify amount: change Chatrel from 150 to 350
        _, ent, _ = self.app.head_entries["Chatrel"]
        ent.delete(0, tk.END)
        ent.insert(0, "350.0")
        self.app.calculate_realtime_total()
        self.assertEqual(self.app.ent_total_sum.get(), "350.00")

        # 6. Save update
        self.app.save_entry()
        self.assertTrue(mock_showinfo.called, "Success message must be displayed")

        # 7. Verify DB was updated in-place (no duplicate rows created)
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, total_amount, account_data FROM transactions")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 1, "Row count must remain 1 after update")
        self.assertEqual(rows[0][0], tx_id, "Transaction ID must remain unchanged")
        self.assertEqual(float(rows[0][1]), 350.0, "Total amount in DB must be updated to 350.0")
        updated_data = json.loads(rows[0][2])
        self.assertEqual(updated_data.get("Chatrel"), 350.0, "Account data must reflect updated amount")
        conn.close()

        # 8. Verify form reset to normal creation mode
        self.assertIsNone(self.app.current_edit_id, "current_edit_id must reset to None")
        self.assertEqual(self.app.btn_save_tx.cget("text"), "💾 Save Contribution Entry")
        self.assertEqual(self.app.lbl_edit_warning.cget("text"), "")

    # =========================================================================
    # 4. DELETING A TRANSACTION WITH CONFIRMATION
    # =========================================================================
    @patch("Rangtsok_app.messagebox.askyesno")
    @patch("Rangtsok_app.messagebox.showinfo")
    def test_delete_transaction_confirmation_and_db_deletion(self, mock_showinfo, mock_askyesno):
        """Verifies deleting transactions removes them from DB when confirmed, or retains them if cancelled."""
        tx1 = self._insert_sample_transaction(receipt="100001", gb="GB-001", name="Person One", total=100.0)
        tx2 = self._insert_sample_transaction(receipt="100002", gb="GB-002", name="Person Two", total=200.0)

        # Run report
        self.app.run_report()
        self.assertEqual(len(self.app.current_report_raw_ids), 2, "Report should contain 2 transactions")

        # Case A: Cancel deletion (askyesno -> False)
        mock_askyesno.return_value = False
        self.app.rep_tree.selection_set("0")
        self.app.delete_batch_transactions()

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM transactions")
        self.assertEqual(cur.fetchone()[0], 2, "No transactions should be deleted when cancelled")
        conn.close()

        # Case B: Confirm deletion (askyesno -> True)
        mock_askyesno.return_value = True
        self.app.rep_tree.selection_set("0")  # Select first item
        deleted_tx_id = self.app.current_report_raw_ids[0]
        self.app.delete_batch_transactions()

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT id FROM transactions")
        remaining_ids = [r[0] for r in cur.fetchall()]
        conn.close()

        self.assertEqual(len(remaining_ids), 1, "Exactly one transaction should remain in DB")
        self.assertNotIn(deleted_tx_id, remaining_ids, "Deleted transaction ID must not exist in DB")
        self.assertTrue(mock_showinfo.called, "Success message must be shown after deletion")

    @patch("Rangtsok_app.messagebox.showwarning")
    def test_delete_batch_transactions_empty_or_total_row_guard(self, mock_showwarning):
        """Verifies attempting to delete without selection or selecting only the total row is guarded."""
        self._insert_sample_transaction(receipt="100001", total=100.0)
        self.app.run_report()

        # Guard 1: No selection
        self.app.rep_tree.selection_remove(self.app.rep_tree.selection())
        self.app.delete_batch_transactions()
        self.assertTrue(mock_showwarning.called, "Must warn when no selection is made")

        # Guard 2: Only total row selected
        mock_showwarning.reset_mock()
        self.app.rep_tree.selection_set("total")
        self.app.delete_batch_transactions()
        self.assertTrue(mock_showwarning.called, "Must warn when only total row is selected")

    # =========================================================================
    # 5. GREEN BOOK AUTO-LOOKUP & EVENT BINDINGS
    # =========================================================================
    def test_gb_auto_lookup_and_status(self):
        """Verifies lookup_gb finds member names case-insensitively and updates status labels."""
        # Pre-seed GB database
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO gb_database (gb_number, name) VALUES (?, ?)", ("GB-5555", "Dawa Sangpo"))
        conn.commit()
        conn.close()

        # 1. Exact match lookup
        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "GB-5555")
        self.app.lookup_gb()
        self.assertEqual(self.app.ent_name.get(), "Dawa Sangpo", "Full name must be populated from GB database")
        self.assertEqual(self.app.lbl_gb_status.cget("text"), "✓ GB Found")

        # 2. Case-insensitive match lookup
        self.app.ent_name.delete(0, tk.END)
        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "gb-5555")
        self.app.lookup_gb()
        self.assertEqual(self.app.ent_name.get(), "Dawa Sangpo", "Case-insensitive lookup must succeed")

        # 3. Missing GB lookup
        self.app.ent_name.delete(0, tk.END)
        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "GB-NONEXISTENT")
        self.app.lookup_gb()
        self.assertEqual(self.app.ent_name.get(), "", "Name should be empty for unknown GB")
        self.assertIn("Data not found", self.app.lbl_gb_status.cget("text"))

    def test_gb_bindings_trigger_lookup(self):
        """Verifies <FocusOut> (Tab) and <Return> (Enter) event bindings trigger lookup_gb."""
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO gb_database (gb_number, name) VALUES (?, ?)", ("GB-7777", "Karma Lobsang"))
        conn.commit()
        conn.close()

        # Verify <FocusOut> binding
        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "GB-7777")
        self.app.ent_name.delete(0, tk.END)
        event_tab = tk.Event()
        event_tab.widget = self.app.ent_gb
        self.app.lookup_gb(event_tab)
        self.assertEqual(self.app.ent_name.get(), "Karma Lobsang", "FocusOut/Tab must invoke lookup_gb")

        # Verify <Return> binding
        self.app.ent_name.delete(0, tk.END)
        event_enter = tk.Event()
        event_enter.widget = self.app.ent_gb
        self.app.lookup_gb(event_enter)
        self.assertEqual(self.app.ent_name.get(), "Karma Lobsang", "Return/Enter must invoke lookup_gb")

    def test_update_gb_name_in_database(self):
        """Verifies update_gb_name persists new member name to gb_database."""
        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "GB-NEW-01")
        self.app.ent_name.delete(0, tk.END)
        self.app.ent_name.insert(0, "Sonam Wangchuk")

        self.app.update_gb_name()

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM gb_database WHERE gb_number=?", ("GB-NEW-01",))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row, "New GB number must be saved into gb_database")
        self.assertEqual(row[0], "Sonam Wangchuk", "Member name mismatch")
        self.assertEqual(self.app.lbl_gb_status.cget("text"), "✓ Database Updated")

    def test_country_select_updates_places(self):
        """Verifies selecting a country dynamically updates the places combobox."""
        self.app.cmb_country.set("India")
        self.app.on_country_select()
        places_india = list(self.app.cmb_place["values"])
        self.assertIn("Dharamshala", places_india, "India places must include Dharamshala")
        self.assertEqual(self.app.cmb_place.get(), places_india[0])

        self.app.cmb_country.set("United States")
        self.app.on_country_select()
        places_us = list(self.app.cmb_place["values"])
        self.assertIn("New York", places_us, "US places must include New York")
        self.assertEqual(self.app.cmb_place.get(), places_us[0])

    # =========================================================================
    # 6. DYNAMIC REAL-TIME CALCULATION ACROSS ACCOUNT HEADS
    # =========================================================================
    def test_dynamic_realtime_calculation_across_account_heads(self):
        """Verifies calculate_realtime_total calculates sums across Amount heads while ignoring Date heads."""
        # Ensure heads exist
        if "Chatrel" in self.app.head_entries:
            _, ent, _ = self.app.head_entries["Chatrel"]
            ent.delete(0, tk.END)
            ent.insert(0, "150.50")

        if "Meal Strike" in self.app.head_entries:
            _, ent, _ = self.app.head_entries["Meal Strike"]
            ent.delete(0, tk.END)
            ent.insert(0, "49.50")

        # Salary Contribution
        if "Salary Contribution" in self.app.head_entries:
            _, ent, _ = self.app.head_entries["Salary Contribution"]
            ent.delete(0, tk.END)
            ent.insert(0, "100.00")

        self.app.calculate_realtime_total()
        self.assertEqual(self.app.ent_total_sum.get(), "300.00", "Sum of 150.50 + 49.50 + 100.00 must be 300.00")

        # Test empty input is treated as 0.0
        if "Salary Contribution" in self.app.head_entries:
            _, ent, _ = self.app.head_entries["Salary Contribution"]
            ent.delete(0, tk.END)
        self.app.calculate_realtime_total()
        self.assertEqual(self.app.ent_total_sum.get(), "200.00", "Empty field must be treated as 0.0")

        # Test non-numeric input does not raise and is ignored
        if "Salary Contribution" in self.app.head_entries:
            _, ent, _ = self.app.head_entries["Salary Contribution"]
            ent.insert(0, "invalid_number")
        self.app.calculate_realtime_total()
        self.assertEqual(self.app.ent_total_sum.get(), "200.00", "Invalid string must be handled gracefully")

    def test_dynamic_account_head_addition_and_calculation(self):
        """Verifies adding a new account head at runtime updates dynamic UI inputs and calculations."""
        new_head = "Monastery Offering"
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, new_head)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "250.0")
        self.app.add_account_head()

        self.assertIn(new_head, self.app.head_entries, "New head must have dynamic input created")

        # Clear other heads to 0
        for h, (_, ent, h_type) in self.app.head_entries.items():
            if h_type == "Amount":
                ent.delete(0, tk.END)
                ent.insert(0, "250.0" if h == new_head else "0.0")

        self.app.calculate_realtime_total()
        self.assertEqual(self.app.ent_total_sum.get(), "250.00", "Dynamic total must reflect the newly added head")

    # =========================================================================
    # 7. REPORT FILTERING BY DATE RANGE, GB, PLACE & TOTALS
    # =========================================================================
    def test_report_filtering_and_totals(self):
        """Verifies filtering reports by date range, GB number, place, and calculating totals."""
        # Insert 4 distinct records
        self._insert_sample_transaction(
            receipt="101", gb="GB-101", name="Alice", country="India", place="Dharamshala",
            currency="INR", tx_date="2026-04-10", acc_data={"Chatrel": 100.0}, total=100.0
        )
        self._insert_sample_transaction(
            receipt="102", gb="GB-102", name="Bob", country="India", place="Bylakuppe",
            currency="INR", tx_date="2026-05-15", acc_data={"Chatrel": 200.0}, total=200.0
        )
        self._insert_sample_transaction(
            receipt="103", gb="GB-103", name="Charlie", country="United States", place="New York",
            currency="USD", tx_date="2026-06-20", acc_data={"Chatrel": 300.0}, total=300.0
        )
        self._insert_sample_transaction(
            receipt="104", gb="GB-104", name="David", country="India", place="Dharamshala",
            currency="INR", tx_date="2026-07-25", acc_data={"Chatrel": 400.0}, total=400.0
        )

        # 1. Filter by Date Range: 01-05-2026 to 30-06-2026 -> returns Bob (200) and Charlie (300)
        self.app.flt_country.set("ALL")
        self.app.flt_place.set("ALL")
        self.app.flt_currency.set("ALL")
        self.app.flt_head.set("ALL")
        self.app.flt_name.delete(0, tk.END)
        self.app.flt_gb.delete(0, tk.END)

        self.app.flt_from_date.set_date(datetime.date(2026, 5, 1))
        self.app.flt_to_date.set_date(datetime.date(2026, 6, 30))
        self.app.run_report()

        self.assertEqual(len(self.app.current_report_df), 2, "Date filter should return exactly 2 records")
        self.assertEqual(self.app.current_report_df["Total"].sum(), 500.0, "Sum of filtered records must be 500.0")
        self.assertIn("Total Displayed Records: 2", self.app.lbl_rep_summary.cget("text"))
        self.assertIn("500.00", self.app.lbl_rep_summary.cget("text"))

        # Verify treeview contains the total row
        total_item_values = self.app.rep_tree.item("total", "values")
        self.assertIn("TOTAL", total_item_values, "Treeview must include a TOTAL row")
        self.assertEqual(float(total_item_values[-1]), 500.0, "Total row value must equal 500.0")

        # 2. Filter by GB Number: "GB-102"
        self.app.flt_from_date.set_date(datetime.date(2026, 1, 1))
        self.app.flt_to_date.set_date(datetime.date(2026, 12, 31))
        self.app.flt_gb.insert(0, "GB-102")
        self.app.run_report()

        self.assertEqual(len(self.app.current_report_df), 1, "GB filter should return exactly 1 record")
        self.assertEqual(self.app.current_report_df.iloc[0]["Name"], "Bob")

        # 3. Filter by Place: "Dharamshala" -> returns Alice (100) and David (400)
        self.app.flt_gb.delete(0, tk.END)
        self.app.flt_place.set("Dharamshala")
        self.app.run_report()

        self.assertEqual(len(self.app.current_report_df), 2, "Place filter should return exactly 2 records")
        self.assertEqual(self.app.current_report_df["Total"].sum(), 500.0)

        # 4. Filter by Country: "United States" -> returns Charlie (300)
        self.app.flt_place.set("ALL")
        self.app.flt_country.set("United States")
        self.app.run_report()

        self.assertEqual(len(self.app.current_report_df), 1, "Country filter should return exactly 1 record")
        self.assertEqual(self.app.current_report_df.iloc[0]["Name"], "Charlie")

    # =========================================================================
    # 8. EXCEL EXPORT & DATABASE BACKUP
    # =========================================================================
    @patch("Rangtsok_app.filedialog.asksaveasfilename")
    @patch("Rangtsok_app.messagebox.showinfo")
    def test_excel_export_creates_valid_workbook(self, mock_showinfo, mock_asksave):
        """Verifies export_report generates a valid Excel workbook with data and total rows."""
        self._insert_sample_transaction(receipt="100001", total=150.0)
        self._insert_sample_transaction(receipt="100002", total=250.0)
        self.app.run_report()

        export_target = os.path.join(self.temp_dir, "test_export.xlsx")
        mock_asksave.return_value = export_target

        self.app.export_report()

        self.assertTrue(os.path.exists(export_target), "Exported Excel file must be written to disk")
        self.assertTrue(mock_showinfo.called, "Success message must be displayed after export")

        # Read back with pandas
        df = pd.read_excel(export_target, sheet_name="Contributions")
        self.assertIn("Receipt", df.columns)
        self.assertIn("Total", df.columns)
        self.assertEqual(len(df), 3, "DataFrame must have 2 data rows + 1 TOTAL row")
        self.assertEqual(str(df.iloc[-1]["Receipt"]).strip().upper(), "TOTAL")
        self.assertEqual(float(df.iloc[-1]["Total"]), 400.0, "Total sum in exported Excel must be 400.0")

    @patch("Rangtsok_app.filedialog.asksaveasfilename")
    @patch("Rangtsok_app.messagebox.showwarning")
    def test_excel_export_empty_guard(self, mock_showwarning, mock_asksave):
        """Verifies attempting to export an empty report shows a warning without writing a file."""
        self.app.current_report_df = pd.DataFrame()
        self.app.export_report()
        self.assertTrue(mock_showwarning.called, "Warning must be shown when exporting empty report")

    @patch("Rangtsok_app.filedialog.asksaveasfilename")
    @patch("Rangtsok_app.messagebox.showinfo")
    def test_database_backup_creates_valid_sqlite_clone(self, mock_showinfo, mock_asksave):
        """Verifies backup_db creates a complete and readable SQLite database copy."""
        self._insert_sample_transaction(receipt="100001", gb="GB-BK-01", name="Backup User", total=100.0)

        backup_target = os.path.join(self.temp_dir, "backup_paljor.db")
        mock_asksave.return_value = backup_target

        self.app.backup_db()

        self.assertTrue(os.path.exists(backup_target), "Backup SQLite database file must exist")
        self.assertTrue(mock_showinfo.called, "Success dialog must be shown")

        # Verify integrity of backup database
        conn = sqlite3.connect(backup_target)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM transactions")
        tx_count = cur.fetchone()[0]
        cur.execute("SELECT name FROM gb_database WHERE gb_number=?", ("GB-BK-01",))
        gb_name = cur.fetchone()[0]
        conn.close()

        self.assertEqual(tx_count, 1, "Backup must contain the transaction record")
        self.assertEqual(gb_name, "Backup User", "Backup must contain the green book record")

    @patch("Rangtsok_app.filedialog.asksaveasfilename")
    @patch("shutil.copy")
    @patch("Rangtsok_app.messagebox.showerror")
    def test_database_backup_error_handling(self, mock_showerror, mock_copy, mock_asksave):
        """Verifies backup_db handles file copy errors gracefully."""
        mock_asksave.return_value = os.path.join(self.temp_dir, "err_backup.db")
        mock_copy.side_effect = PermissionError("Simulated disk error")

        self.app.backup_db()
        self.assertTrue(mock_showerror.called, "Error dialog must be displayed on backup failure")


if __name__ == "__main__":
    unittest.main()
