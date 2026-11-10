import unittest
from unittest.mock import patch
import os
import sys
import json
import sqlite3
import shutil
import tempfile
import tkinter as tk
import ttkbootstrap as tb

# Ensure workspace root is in path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import Rangtsok_app


class TestAccountHeadManagement(unittest.TestCase):
    """Automated integration tests for Account Head Add, Edit, Delete, UI Sync, and DB Integrity."""

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
        # Create a temp dir for isolated settings and database
        self.temp_dir = tempfile.mkdtemp()
        self.test_settings_path = os.path.join(self.temp_dir, "settings.json")
        self.test_db_path = os.path.join(self.temp_dir, "paljor_contribution.db")

        # Copy original settings or use default
        orig_settings_path = os.path.join(WORKSPACE_ROOT, "settings.json")
        if os.path.exists(orig_settings_path):
            shutil.copy(orig_settings_path, self.test_settings_path)
        else:
            with open(self.test_settings_path, "w", encoding="utf-8") as f:
                json.dump(Rangtsok_app.DEFAULT_SETTINGS, f, indent=4)

        # Patch module-level paths
        self.orig_settings_file = Rangtsok_app.SETTINGS_FILE
        self.orig_db_file = Rangtsok_app.DB_FILE
        Rangtsok_app.SETTINGS_FILE = self.test_settings_path
        Rangtsok_app.DB_FILE = self.test_db_path

        # Initialize the test database schema
        Rangtsok_app.init_db()

        # Instantiate app
        self.app = Rangtsok_app.ContributionApp(self.root)

    def tearDown(self):
        # Restore paths
        Rangtsok_app.SETTINGS_FILE = self.orig_settings_file
        Rangtsok_app.DB_FILE = self.orig_db_file

        # Clean up temp dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_account_head_synchronizes_ui(self):
        """a) Adding a new head appears in settings, entry inputs, and report filters."""
        head_name = "COVID Relief Fund"
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "200")

        self.app.add_account_head()

        # 1. Verify in settings dictionary
        configured_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        self.assertIn(head_name, configured_heads, "New head must be present in self.settings['account_heads']")

        # 2. Verify in treeview
        tree_items = [self.app.tree_heads.item(item, "values")[1] for item in self.app.tree_heads.get_children()]
        self.assertIn(head_name, tree_items, "New head must be visible in settings tree_heads")

        # 3. Verify in entry dynamic inputs
        self.assertIn(head_name, self.app.head_entries, "New head must be instantiated in self.head_entries")

        # 4. Verify in report filters
        report_filter_values = list(self.app.flt_head["values"])
        self.assertIn(head_name, report_filter_values, "New head must be present in flt_head dropdown values")

    def test_delete_account_head_synchronizes_ui_cleanly(self):
        """b) Deleting that head disappears immediately from settings, entry inputs, and report filters."""
        # First add a head
        head_name = "Temporary Head"
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "50")
        self.app.add_account_head()

        # Select it in the treeview
        target_iid = None
        for item in self.app.tree_heads.get_children():
            if self.app.tree_heads.item(item, "values")[1] == head_name:
                target_iid = item
                break
        self.assertIsNotNone(target_iid, "Head should exist in treeview before deletion")
        self.app.tree_heads.selection_set(target_iid)

        # Mock confirm yes and info
        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True) as mock_ask, \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info:
            self.app.delete_account_head()
            mock_ask.assert_called_once()
            mock_info.assert_called_once()

        # 1. Verify removed from settings
        configured_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        self.assertNotIn(head_name, configured_heads, "Deleted head must not be in self.settings")

        # 2. Verify removed from settings treeview
        tree_items = [self.app.tree_heads.item(item, "values")[1] for item in self.app.tree_heads.get_children()]
        self.assertNotIn(head_name, tree_items, "Deleted head must not be in tree_heads")

        # 3. Verify removed from entry dynamic inputs
        self.assertNotIn(head_name, self.app.head_entries, "Deleted head must not be in head_entries")

        # 4. Verify removed from report filters
        report_filter_values = list(self.app.flt_head["values"])
        self.assertNotIn(head_name, report_filter_values, "Deleted head must not be in flt_head dropdown values")

        # 5. Form inputs cleared
        self.assertEqual(self.app.ent_new_head.get(), "", "Input entry should be cleared")

    def test_delete_active_head_blocked(self):
        """c) Attempting to delete an active head with real transactions (e.g. Chatrel) is safely blocked."""
        # Insert a transaction with active Chatrel contribution
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions 
            (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("REC001", "GB1234", "Tashi Delek", "India", "Dharamshala", "INR", "2026-05-01", "2026-05-01",
             json.dumps({"Chatrel": 250.0, "Meal Strike": 0.0}), 250.0)
        )
        conn.commit()
        conn.close()

        # Select Chatrel in treeview
        target_iid = None
        for item in self.app.tree_heads.get_children():
            if self.app.tree_heads.item(item, "values")[1] == "Chatrel":
                target_iid = item
                break
        self.assertIsNotNone(target_iid, "Chatrel must exist in treeview")
        self.app.tree_heads.selection_set(target_iid)

        with patch.object(Rangtsok_app.messagebox, "showerror") as mock_err, \
             patch.object(Rangtsok_app.messagebox, "askyesno") as mock_ask:
            self.app.delete_account_head()

            # Verify deletion blocked with error dialog
            mock_err.assert_called_once()
            self.assertEqual(mock_err.call_args[0][0], "Deletion Blocked")
            # askyesno should never be called
            mock_ask.assert_not_called()

        # Verify Chatrel remains intact everywhere
        configured_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        self.assertIn("Chatrel", configured_heads)
        self.assertIn("Chatrel", self.app.head_entries)
        self.assertIn("Chatrel", list(self.app.flt_head["values"]))

    def test_delete_head_purges_orphan_keys_from_database(self):
        """d) Deleting an unused or zero-only head purges orphan keys from transactions.account_data."""
        # Add head "Unused Head"
        head_name = "Unused Head"
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "0.0")
        self.app.add_account_head()

        # Insert transactions with 0.0 or empty values for this head
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions 
            (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("REC002", "GB5678", "Dorjee", "India", "Delhi", "INR", "2026-06-01", "2026-06-01",
             json.dumps({"Chatrel": 150.0, head_name: 0.0}), 150.0)
        )
        cursor.execute(
            """
            INSERT INTO transactions 
            (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("REC003", "GB9999", "Sonam", "India", "Delhi", "INR", "2026-06-02", "2026-06-02",
             json.dumps({"Chatrel": 150.0, head_name: ""}), 150.0)
        )
        conn.commit()
        conn.close()

        # Select Unused Head
        target_iid = None
        for item in self.app.tree_heads.get_children():
            if self.app.tree_heads.item(item, "values")[1] == head_name:
                target_iid = item
                break
        self.assertIsNotNone(target_iid)
        self.app.tree_heads.selection_set(target_iid)

        # Delete with confirmation
        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):
            self.app.delete_account_head()

        # Inspect database records
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, account_data FROM transactions")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 2)
        for tx_id, acc_data_str in rows:
            acc_data = json.loads(acc_data_str)
            self.assertNotIn(head_name, acc_data, f"Transaction {tx_id} must not contain orphan key '{head_name}'")
            self.assertEqual(acc_data.get("Chatrel"), 150.0, "Chatrel value must be preserved")

    def test_delete_head_no_selection_shows_warning(self):
        """Deleting when nothing is selected shows a warning and does not crash."""
        self.app.tree_heads.selection_remove(self.app.tree_heads.selection())
        with patch.object(Rangtsok_app.messagebox, "showwarning") as mock_warn:
            self.app.delete_account_head()
            mock_warn.assert_called_once()
            self.assertEqual(mock_warn.call_args[0][0], "No Selection")

    def test_delete_date_head_active_blocked_and_empty_purged(self):
        """Date-type account head: blocked if date string is non-empty, allowed and purged if empty."""
        date_head = "Special Event Date"
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, date_head)
        self.app.cmb_new_type.set("Date")
        self.app.on_head_type_change()
        self.app.add_account_head()

        # Insert transaction with active date
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions 
            (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("REC004", "GB1111", "Kelsang", "India", "Delhi", "INR", "2026-06-03", "2026-06-03",
             json.dumps({"Chatrel": 150.0, date_head: "01-05-2026"}), 150.0)
        )
        conn.commit()
        conn.close()

        # Select date_head
        target_iid = None
        for item in self.app.tree_heads.get_children():
            if self.app.tree_heads.item(item, "values")[1] == date_head:
                target_iid = item
                break
        self.app.tree_heads.selection_set(target_iid)

        # Attempt deletion -> should be blocked
        with patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:
            self.app.delete_account_head()
            mock_err.assert_called_once()

        # Now clear the date in the transaction record
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE transactions SET account_data=? WHERE receipt_no=?",
            (json.dumps({"Chatrel": 150.0, date_head: ""}), "REC004")
        )
        conn.commit()
        conn.close()

        # Attempt deletion again -> should succeed and purge key
        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):
            self.app.delete_account_head()

        # Verify purged
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT account_data FROM transactions WHERE receipt_no=?", ("REC004",))
        acc_data = json.loads(cursor.fetchone()[0])
        conn.close()

        self.assertNotIn(date_head, acc_data)


if __name__ == "__main__":
    unittest.main()
