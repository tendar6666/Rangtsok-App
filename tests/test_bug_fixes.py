import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
import sqlite3
import shutil
import tempfile
import datetime
import math
import tkinter as tk
import ttkbootstrap as tb
import pandas as pd
import numpy as np

# Ensure workspace root is in path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import Rangtsok_app


class BaseBugFixTest(unittest.TestCase):
    """Base class setting up an isolated temporary database, settings, and headless Tkinter root."""

    @classmethod
    def setUpClass(cls):
        cls.root = tb.Window(themename="cosmo")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_settings_path = os.path.join(self.temp_dir, "settings.json")
        self.test_db_path = os.path.join(self.temp_dir, "paljor_contribution.db")

        orig_settings_path = os.path.join(WORKSPACE_ROOT, "settings.json")
        if os.path.exists(orig_settings_path):
            shutil.copy(orig_settings_path, self.test_settings_path)
        else:
            with open(self.test_settings_path, "w", encoding="utf-8") as f:
                json.dump(Rangtsok_app.DEFAULT_SETTINGS, f, indent=4)

        self.orig_settings_file = Rangtsok_app.SETTINGS_FILE
        self.orig_db_file = Rangtsok_app.DB_FILE
        Rangtsok_app.SETTINGS_FILE = self.test_settings_path
        Rangtsok_app.DB_FILE = self.test_db_path

        Rangtsok_app.init_db()
        self.app = Rangtsok_app.ContributionApp(self.root)

    def tearDown(self):
        Rangtsok_app.SETTINGS_FILE = self.orig_settings_file
        Rangtsok_app.DB_FILE = self.orig_db_file
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _insert_transaction(self, receipt="100000", gb="IN001", name="Test User",
                            country="India", place="Dharamsala", currency="INR (₹)",
                            tx_date="2026-05-01", entry_date="2026-05-01",
                            acc_data=None, total=150.0):
        if acc_data is None:
            acc_data = {"Chatrel": 150.0}
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (receipt, gb, name, country, place, currency, tx_date, entry_date, json.dumps(acc_data), total)
        )
        conn.commit()
        conn.close()


class TestB1DateFilterCrash(BaseBugFixTest):
    """B1: Verify Date filter does not crash in run_report and filters correctly."""

    def test_b1_date_filter_does_not_crash_on_date_head(self):
        """Selecting a Date-type account head in report filter should not raise TypeError."""
        # Add a date head to settings if not present
        heads = self.app.settings.get("account_heads", [])
        if not any(h["head"] == "Chatrel Start Date" for h in heads):
            heads.append({"head": "Chatrel Start Date", "type": "Date", "default": "01-04-2026"})
            self.app.settings["account_heads"] = heads
            Rangtsok_app.save_settings(self.app.settings)

        # Seed 2 transactions: one with a date string, one with empty string
        acc1 = {"Chatrel": 150.0, "Chatrel Start Date": "01-04-2026"}
        acc2 = {"Chatrel": 150.0, "Chatrel Start Date": ""}
        self._insert_transaction(receipt="100001", gb="IN001", name="Tenzin", acc_data=acc1, total=150.0)
        self._insert_transaction(receipt="100002", gb="IN002", name="Sonam", acc_data=acc2, total=150.0)

        # Set date filter to Date head
        self.app.flt_from_date.set_date(datetime.datetime(2026, 1, 1))
        self.app.flt_to_date.set_date(datetime.datetime(2026, 12, 31))
        self.app.flt_country.set("ALL")
        self.app.flt_place.set("ALL")
        self.app.flt_currency.set("ALL")
        self.app.flt_name.delete(0, tk.END)
        self.app.flt_gb.delete(0, tk.END)
        self.app.flt_head.set("Chatrel Start Date")

        # Running report must NOT raise TypeError: '<=' not supported between instances of 'str' and 'int'
        try:
            self.app.run_report()
        except TypeError as e:
            self.fail(f"run_report() crashed with TypeError when filtering by Date head: {e}")

        # The DataFrame should contain only the row with the valid date string
        self.assertFalse(self.app.current_report_df.empty, "Report DF should not be empty")
        self.assertEqual(len(self.app.current_report_df), 1, "Only row with non-empty date should be returned")
        self.assertEqual(self.app.current_report_df.iloc[0]["Receipt"], "100001")

    def test_b1_amount_filter_still_excludes_zero_and_negative(self):
        """Selecting an Amount-type head in report filter should include only amounts > 0."""
        acc_pos = {"Chatrel": 150.0}
        acc_zero = {"Chatrel": 0.0}
        self._insert_transaction(receipt="200001", gb="IN001", name="Tenzin", acc_data=acc_pos, total=150.0)
        self._insert_transaction(receipt="200002", gb="IN002", name="Sonam", acc_data=acc_zero, total=0.0)

        self.app.flt_from_date.set_date(datetime.datetime(2026, 1, 1))
        self.app.flt_to_date.set_date(datetime.datetime(2026, 12, 31))
        self.app.flt_country.set("ALL")
        self.app.flt_place.set("ALL")
        self.app.flt_currency.set("ALL")
        self.app.flt_name.delete(0, tk.END)
        self.app.flt_gb.delete(0, tk.END)
        self.app.flt_head.set("Chatrel")

        self.app.run_report()
        self.assertEqual(len(self.app.current_report_df), 1)
        self.assertEqual(self.app.current_report_df.iloc[0]["Receipt"], "200001")


class TestB2RepTreeDoubleClickHandler(BaseBugFixTest):
    """B2: Verify unified <Double-1> handling distinguishes separator vs cell/tree double clicks."""

    def test_b2_separator_double_click_calls_auto_resize(self):
        """Double clicking separator region triggers column auto-resizing without opening record edit."""
        self._insert_transaction(receipt="300001", gb="IN001", name="Longer Contributor Name", total=150.0)
        self.app.run_report()

        fake_event = MagicMock()
        fake_event.x = 50
        fake_event.y = 10

        with patch.object(self.app.rep_tree, "identify_region", return_value="separator"), \
             patch.object(self.app, "_rep_tree_auto_resize_column") as mock_resize, \
             patch.object(self.app, "load_entry_for_edit") as mock_edit:

            self.app.on_report_double_click(fake_event)
            mock_resize.assert_called_once_with(fake_event)
            mock_edit.assert_not_called()

    def test_b2_heading_double_click_calls_auto_resize(self):
        """Double clicking heading region triggers column auto-resizing."""
        self._insert_transaction(receipt="300002", gb="IN002", name="Contributor", total=150.0)
        self.app.run_report()

        fake_event = MagicMock()
        fake_event.x = 50
        fake_event.y = 10

        with patch.object(self.app.rep_tree, "identify_region", return_value="heading"), \
             patch.object(self.app, "_rep_tree_auto_resize_column") as mock_resize, \
             patch.object(self.app, "load_entry_for_edit") as mock_edit:

            self.app.on_report_double_click(fake_event)
            mock_resize.assert_called_once_with(fake_event)
            mock_edit.assert_not_called()

    def test_b2_cell_double_click_loads_record_for_edit(self):
        """Double clicking a data cell triggers load_entry_for_edit."""
        self._insert_transaction(receipt="300003", gb="IN003", name="Contributor Cell", total=150.0)
        self.app.run_report()

        # Select the first row
        children = self.app.rep_tree.get_children()
        self.assertTrue(len(children) > 0)
        first_row_iid = children[0]
        self.app.rep_tree.selection_set(first_row_iid)

        fake_event = MagicMock()
        fake_event.x = 50
        fake_event.y = 35

        with patch.object(self.app.rep_tree, "identify_region", return_value="cell"), \
             patch.object(self.app, "_rep_tree_auto_resize_column") as mock_resize, \
             patch.object(self.app, "load_entry_for_edit") as mock_edit:

            self.app.on_report_double_click(fake_event)
            mock_resize.assert_not_called()
            mock_edit.assert_called_once()

    def test_b2_total_row_double_click_does_not_load_for_edit(self):
        """Double clicking the summary TOTAL row does not invoke load_entry_for_edit."""
        self._insert_transaction(receipt="300004", gb="IN004", name="User Total Test", total=150.0)
        self.app.run_report()

        if self.app.rep_tree.exists("total"):
            self.app.rep_tree.selection_set("total")
            fake_event = MagicMock()
            fake_event.x = 50
            fake_event.y = 60

            with patch.object(self.app.rep_tree, "identify_region", return_value="cell"), \
                 patch.object(self.app, "load_entry_for_edit") as mock_edit:

                self.app.on_report_double_click(fake_event)
                mock_edit.assert_not_called()


class TestB3ReceiptAutoIncrement(BaseBugFixTest):
    """B3: Verify receipt auto-increment preserves leading zeros and compound prefixes."""

    def test_b3_sequential_standard_increment(self):
        """Standard 6-digit numeric increment: 100000 -> 100001."""
        self._insert_transaction(receipt="100000")
        self.app.auto_set_next_receipt()
        self.assertEqual(self.app.ent_receipt.get(), "100001")

    def test_b3_zero_padding_preservation(self):
        """Leading zeros must not be stripped: 000100 -> 000101, 000005 -> 000006."""
        self._insert_transaction(receipt="000100")
        self.app.auto_set_next_receipt()
        self.assertEqual(self.app.ent_receipt.get(), "000101")

        self._insert_transaction(receipt="000005")
        self.app.auto_set_next_receipt()
        self.assertEqual(self.app.ent_receipt.get(), "000006")

    def test_b3_compound_format_preservation(self):
        """Compound strings with prefixes and hyphens: REC-2026-001 -> REC-2026-002."""
        self._insert_transaction(receipt="REC-2026-001")
        self.app.auto_set_next_receipt()
        self.assertEqual(self.app.ent_receipt.get(), "REC-2026-002")

    def test_b3_compound_prefix_voucher_overflow(self):
        """Compound strings across digit boundaries: VOUCH-999 -> VOUCH-1000."""
        self._insert_transaction(receipt="VOUCH-999")
        self.app.auto_set_next_receipt()
        self.assertEqual(self.app.ent_receipt.get(), "VOUCH-1000")

    def test_b3_non_digit_fallback(self):
        """Receipt with no trailing digits appends _1."""
        self._insert_transaction(receipt="VOUCHER")
        self.app.auto_set_next_receipt()
        self.assertEqual(self.app.ent_receipt.get(), "VOUCHER_1")

    def test_b3_empty_table_default(self):
        """When transactions table is empty, receipt defaults to 100000."""
        self.app.auto_set_next_receipt()
        self.assertEqual(self.app.ent_receipt.get(), "100000")


class TestB4GBCleansingLongestName(BaseBugFixTest):
    """B4: Verify GB database cleansing retains the longest contributor name."""

    def test_b4_cleansing_keeps_longest_name_when_first(self):
        """When longer name is first, it is retained after cleansing."""
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO gb_database (gb_number, name) VALUES (?, ?)", ("in-001", "Tenzin Wangyal"))
        cur.execute("INSERT INTO gb_database (gb_number, name) VALUES (?, ?)", ("IN001", "T. Wangyal"))
        conn.commit()
        conn.close()

        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):
            self.app.cleanse_gb_database()

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT gb_number, name FROM gb_database")
        rows = cur.fetchall()
        conn.close()

        self.assertEqual(len(rows), 1, "Duplicate GB should be merged to exactly one record")
        self.assertEqual(rows[0][0], "in001")
        self.assertEqual(rows[0][1], "Tenzin Wangyal")

    def test_b4_cleansing_keeps_longest_name_when_last(self):
        """When longer name appears after a shorter one, the longer name replaces the shorter one."""
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO gb_database (gb_number, name) VALUES (?, ?)", ("in-002", "T. Wangyal"))
        cur.execute("INSERT INTO gb_database (gb_number, name) VALUES (?, ?)", ("IN002", "Tenzin Wangyal Proper Name"))
        conn.commit()
        conn.close()

        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):
            self.app.cleanse_gb_database()

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT gb_number, name FROM gb_database")
        rows = cur.fetchall()
        conn.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "in002")
        self.assertEqual(rows[0][1], "Tenzin Wangyal Proper Name")


class TestB5CurrencySafety(BaseBugFixTest):
    """B5: Verify currency extraction is safe against empty strings, whitespace, and deleted settings."""

    def test_b5_get_safe_currency_symbol_variants(self):
        """get_safe_currency_symbol returns valid strings for all inputs."""
        # Standard currency string
        self.assertEqual(self.app.get_safe_currency_symbol("INR (₹)"), "INR")
        self.assertEqual(self.app.get_safe_currency_symbol("USD ($)"), "USD")
        self.assertEqual(self.app.get_safe_currency_symbol("₹"), "₹")

        # Empty / whitespace inputs fall back to setting or default ₹
        self.app.settings["currency"] = "USD ($)"
        self.assertEqual(self.app.get_safe_currency_symbol(""), "USD")
        self.assertEqual(self.app.get_safe_currency_symbol("   "), "USD")
        self.assertEqual(self.app.get_safe_currency_symbol(None), "USD")

        # Missing or empty setting falls back to ₹
        self.app.settings["currency"] = ""
        self.assertEqual(self.app.get_safe_currency_symbol(""), "₹")
        self.assertEqual(self.app.get_safe_currency_symbol(None), "₹")

    def test_b5_on_entry_currency_change_with_empty_combobox(self):
        """on_entry_currency_change does not raise IndexError when combobox is empty."""
        self.app.cmb_entry_currency.set("")
        try:
            self.app.on_entry_currency_change()
        except IndexError as e:
            self.fail(f"on_entry_currency_change raised IndexError on empty currency: {e}")

    def test_b5_run_report_with_empty_currency_setting(self):
        """run_report footer updates cleanly when settings['currency'] is empty."""
        self.app.settings["currency"] = ""
        self._insert_transaction(receipt="500001", total=100.0)
        try:
            self.app.run_report()
        except IndexError as e:
            self.fail(f"run_report raised IndexError with empty currency setting: {e}")


class TestB6ExcelImportDateAndNaNSafety(BaseBugFixTest):
    """B6: Verify Excel import date tolerance (ISO format) and NaN sanitization."""

    def test_b6_parse_ui_date_formats(self):
        """parse_ui_date parses DD-MM-YYYY, ISO YYYY-MM-DD, slashes, and timestamps."""
        # DD-MM-YYYY
        self.assertEqual(Rangtsok_app.parse_ui_date("15-05-2026"), "2026-05-15")
        # ISO YYYY-MM-DD
        self.assertEqual(Rangtsok_app.parse_ui_date("2026-05-15"), "2026-05-15")
        # Slashes
        self.assertEqual(Rangtsok_app.parse_ui_date("15/05/2026"), "2026-05-15")
        self.assertEqual(Rangtsok_app.parse_ui_date("2026/05/15"), "2026-05-15")
        # Datetime object
        dt = datetime.datetime(2026, 5, 15, 14, 30)
        self.assertEqual(Rangtsok_app.parse_ui_date(dt), "2026-05-15")
        # Timestamp
        ts = pd.Timestamp("2026-05-15")
        self.assertEqual(Rangtsok_app.parse_ui_date(ts), "2026-05-15")
        # Invalids / NaNs return None
        self.assertIsNone(Rangtsok_app.parse_ui_date(None))
        self.assertIsNone(Rangtsok_app.parse_ui_date(""))
        self.assertIsNone(Rangtsok_app.parse_ui_date("nan"))
        self.assertIsNone(Rangtsok_app.parse_ui_date(np.nan))
        self.assertIsNone(Rangtsok_app.parse_ui_date("invalid_date_string"))

    def test_b6_excel_import_with_iso_dates_and_nans(self):
        """import_batch_excel successfully imports rows with ISO dates and converts NaNs to 0.0."""
        heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        data = {
            "Receipt": ["600001", "600002"],
            "GB Number": ["IN601", "IN602"],
            "Name": ["Tenzin Iso", "Sonam Nan"],
            "Country": ["India", "India"],
            "Place": ["Dharamsala", "Dharamsala"],
            "Currency": ["INR (₹)", "INR (₹)"],
            "Transaction Date": ["2026-05-15", "16-05-2026"],  # Row 1 is ISO, Row 2 is DD-MM-YYYY
        }
        for h in heads:
            # Place NaN in optional heads for row 2
            data[h] = [100.0, np.nan]
        data["Total"] = [100.0, np.nan]

        df = pd.DataFrame(data)
        excel_path = os.path.join(self.temp_dir, "test_import.xlsx")
        df.to_excel(excel_path, index=False)

        with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

            self.app.import_batch_excel()
            self.assertFalse(mock_err.called, f"import_batch_excel showed error dialog: {mock_err.call_args}")
            self.assertTrue(mock_info.called, "Import success dialog should be shown")

        # Inspect database transactions
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT receipt_no, tx_date, account_data, total_amount FROM transactions ORDER BY id ASC")
        rows = cur.fetchall()
        conn.close()

        self.assertEqual(len(rows), 2)
        # Check Row 1 (ISO date)
        self.assertEqual(rows[0][0], "600001")
        self.assertEqual(rows[0][1], "2026-05-15")

        # Check Row 2 (NaN values sanitized)
        self.assertEqual(rows[1][0], "600002")
        acc2_data = json.loads(rows[1][2])
        for h, val in acc2_data.items():
            self.assertFalse(math.isnan(val) if isinstance(val, float) else False, f"Account head {h} contains NaN!")
            if isinstance(val, (int, float)):
                self.assertEqual(val, 0.0, f"Expected 0.0 for NaN head {h}")
        self.assertFalse(math.isnan(rows[1][3]), "Total amount in DB should not be NaN")


class TestAdvisoryHardeningNegativeAdjustment(BaseBugFixTest):
    """Advisory Hardening: Verify delete_account_head protects negative adjustment/refund records."""

    def test_advisory_negative_amount_head_deletion_blocked(self):
        """Account head with negative amount (-50.0) is recognized as active usage and blocked."""
        # Add head to settings
        head_name = "Refund Adjustment"
        heads = self.app.settings.get("account_heads", [])
        heads.append({"head": head_name, "type": "Amount", "default": 0.0})
        self.app.settings["account_heads"] = heads
        Rangtsok_app.save_settings(self.app.settings)
        self.app.refresh_settings_heads_list()

        # Seed transaction with negative contribution
        self._insert_transaction(
            receipt="700001",
            acc_data={"Chatrel": 200.0, head_name: -50.0},
            total=150.0
        )

        # Select the head in treeview
        for item in self.app.tree_heads.get_children():
            vals = self.app.tree_heads.item(item, "values")
            if vals and len(vals) > 1 and vals[1] == head_name:
                self.app.tree_heads.selection_set(item)
                break

        # Attempt deletion
        with patch.object(Rangtsok_app.messagebox, "showerror") as mock_err, \
             patch.object(Rangtsok_app.messagebox, "askyesno") as mock_ask:

            self.app.delete_account_head()
            self.assertTrue(mock_err.called, "Deletion must be blocked for negative contribution")
            self.assertFalse(mock_ask.called, "Confirmation should not be shown when blocked")

        # Verify head is still in settings
        curr_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        self.assertIn(head_name, curr_heads)

    def test_advisory_zero_amount_head_deletion_allowed(self):
        """Account head with only 0.0 transactions can be deleted safely."""
        head_name = "Unused Dormant Head"
        heads = self.app.settings.get("account_heads", [])
        heads.append({"head": head_name, "type": "Amount", "default": 0.0})
        self.app.settings["account_heads"] = heads
        Rangtsok_app.save_settings(self.app.settings)
        self.app.refresh_settings_heads_list()

        # Seed transaction with 0.0
        self._insert_transaction(
            receipt="700002",
            acc_data={"Chatrel": 200.0, head_name: 0.0},
            total=200.0
        )

        for item in self.app.tree_heads.get_children():
            vals = self.app.tree_heads.item(item, "values")
            if vals and len(vals) > 1 and vals[1] == head_name:
                self.app.tree_heads.selection_set(item)
                break

        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):

            self.app.delete_account_head()

        curr_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        self.assertNotIn(head_name, curr_heads)


if __name__ == "__main__":
    unittest.main()
