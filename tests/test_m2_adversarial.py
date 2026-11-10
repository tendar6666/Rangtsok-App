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


class BaseAdversarialM2Test(unittest.TestCase):
    """Isolated environment for M2 adversarial testing."""

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

    def _insert_tx(self, receipt="100000", gb="GB01", name="Adversarial User",
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


class TestAdversarialB1DateFiltering(BaseAdversarialM2Test):
    """Adversarial stress-testing of B1: Date-type account head filtering."""

    def test_b1_date_filter_fuzzing_values(self):
        """Test date filter against missing key, whitespace, invalid dates, None, booleans, and valid dates."""
        heads = self.app.settings.get("account_heads", [])
        if not any(h["head"] == "Custom Date" for h in heads):
            heads.append({"head": "Custom Date", "type": "Date", "default": ""})
            self.app.settings["account_heads"] = heads
            Rangtsok_app.save_settings(self.app.settings)

        # Diverse test payloads for 'Custom Date'
        cases = [
            ("REC01", {"Chatrel": 100.0, "Custom Date": "01-04-2026"}, True),     # Valid DD-MM-YYYY
            ("REC02", {"Chatrel": 100.0, "Custom Date": "2026-04-01"}, True),     # Valid ISO
            ("REC03", {"Chatrel": 100.0, "Custom Date": "not-a-date"}, True),     # Non-empty arbitrary string
            ("REC04", {"Chatrel": 100.0, "Custom Date": ""}, False),              # Empty string -> excluded
            ("REC05", {"Chatrel": 100.0, "Custom Date": "   "}, False),           # Whitespace string -> excluded
            ("REC06", {"Chatrel": 100.0, "Custom Date": None}, False),            # None -> excluded
            ("REC07", {"Chatrel": 100.0}, False),                                 # Missing key -> excluded
            ("REC08", {"Chatrel": 100.0, "Custom Date": 0}, False),               # Numeric zero -> excluded
            ("REC09", {"Chatrel": 100.0, "Custom Date": 123}, True),              # Numeric positive -> included
            ("REC10", {"Chatrel": 100.0, "Custom Date": False}, False),           # Boolean False -> excluded
        ]

        for rec, data, _ in cases:
            self._insert_tx(receipt=rec, acc_data=data)

        self.app.flt_from_date.set_date(datetime.datetime(2026, 1, 1))
        self.app.flt_to_date.set_date(datetime.datetime(2026, 12, 31))
        self.app.flt_country.set("ALL")
        self.app.flt_place.set("ALL")
        self.app.flt_currency.set("ALL")
        self.app.flt_name.delete(0, tk.END)
        self.app.flt_gb.delete(0, tk.END)
        self.app.flt_head.set("Custom Date")

        # Must execute cleanly without unhandled exception
        try:
            self.app.run_report()
        except Exception as e:
            self.fail(f"run_report() crashed during adversarial date filter fuzzing: {e}")

        included_receipts = set(self.app.current_report_df["Receipt"].tolist())
        expected_included = {rec for rec, _, inc in cases if inc}
        expected_excluded = {rec for rec, _, inc in cases if not inc}

        self.assertEqual(included_receipts, expected_included,
                         f"Mismatch in date filter results. Included: {included_receipts}, Expected: {expected_included}")
        for excluded_rec in expected_excluded:
            self.assertNotIn(excluded_rec, included_receipts)


class TestAdversarialB2CoordinatesAndDoubleClicks(BaseAdversarialM2Test):
    """Adversarial stress-testing of B2: Event coordinate handling and region identification."""

    def setUp(self):
        super().setUp()
        self._insert_tx(receipt="R101", name="Adversarial Subject", total=100.0)
        self.app.run_report()

    def test_b2_event_with_negative_and_out_of_bounds_coords(self):
        """Passing negative or absurdly large coordinates must not crash double click handler."""
        for x, y in [(-100, -100), (99999, 99999), (0, 0), (10, 10)]:
            fake_event = MagicMock()
            fake_event.x = x
            fake_event.y = y
            try:
                self.app.on_report_double_click(fake_event)
            except Exception as e:
                self.fail(f"on_report_double_click crashed with coords ({x}, {y}): {e}")

    def test_b2_event_none_or_missing_attributes(self):
        """Passing None or an event object without x,y coordinates must exit gracefully."""
        try:
            self.app.on_report_double_click(None)
            self.app.on_report_double_click(object())
        except Exception as e:
            self.fail(f"on_report_double_click crashed on missing event coordinates: {e}")

    def test_b2_auto_resize_invalid_column_indices(self):
        """_rep_tree_auto_resize_column handles non-integer or out-of-range columns without error."""
        fake_event = MagicMock()
        fake_event.x = 50
        fake_event.y = 10

        # Region is separator but column identify returns invalid tokens
        for mock_col in ["#999", "#-1", "#abc", ""]:
            with patch.object(self.app.rep_tree, "identify_region", return_value="separator"), \
                 patch.object(self.app.rep_tree, "identify_column", return_value=mock_col):
                try:
                    self.app._rep_tree_auto_resize_column(fake_event)
                except Exception as e:
                    self.fail(f"_rep_tree_auto_resize_column crashed for mock_col='{mock_col}': {e}")


class TestAdversarialB3ReceiptAutoIncrement(BaseAdversarialM2Test):
    """Adversarial stress-testing of B3: auto_set_next_receipt."""

    def test_b3_extreme_receipt_formats(self):
        """Verify behavior across huge numbers, complex separators, alphabetic strings, and whitespace."""
        test_cases = [
            # (previous_receipt_in_db, expected_next_receipt)
            ("REC/2026/000999", "REC/2026/001000"),
            ("PAL-999-001", "PAL-999-002"),
            ("A/B/C-00000", "A/B/C-00001"),
            ("000000", "000001"),
            ("099", "100"),
            ("VOUCH999", "VOUCH1000"),
            ("ALPHANUMERIC", "ALPHANUMERIC_1"),
            ("NO-DIGIT-HERE", "NO-DIGIT-HERE_1"),
            ("   ", "100000"),
            ("", "100000"),
            ("99999999999999999999", "100000000000000000000"),
            ("INV_2026_9999", "INV_2026_10000"),
        ]

        for prev, expected in test_cases:
            conn = sqlite3.connect(self.test_db_path)
            cur = conn.cursor()
            cur.execute("DELETE FROM transactions")
            cur.execute(
                "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, '', '', '', '', '', '', '', '{}', 0)",
                (prev,)
            )
            conn.commit()
            conn.close()

            self.app.current_edit_id = None
            self.app.auto_set_next_receipt()
            actual = self.app.ent_receipt.get()
            self.assertEqual(actual, expected, f"Failed for prev='{prev}'. Got '{actual}', expected '{expected}'")

    def test_b3_empty_table_in_db(self):
        """When transactions table is completely empty, default to '100000'."""
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM transactions")
        conn.commit()
        conn.close()

        self.app.current_edit_id = None
        self.app.auto_set_next_receipt()
        self.assertEqual(self.app.ent_receipt.get(), "100000")


class TestAdversarialB4GBCleansing(BaseAdversarialM2Test):
    """Adversarial stress-testing of B4: cleanse_gb_database."""

    def test_b4_deduplication_multi_duplicates_and_whitespace(self):
        """Deduplicating 4 variants of same GB with varying whitespace, casing, and lengths."""
        variants = [
            ("in-007", "Short Name"),
            ("  IN 007  ", "Medium Length Name"),
            ("IN#007", "Longest Comprehensive Contributor Name"),
            ("in/007", "T. Short"),
        ]
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM gb_database")
        for gb, name in variants:
            cur.execute("INSERT INTO gb_database (gb_number, name) VALUES (?, ?)", (gb, name))
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

        self.assertEqual(len(rows), 1, "Should merge all 4 variants into 1 record")
        self.assertEqual(rows[0][0], "in007")
        self.assertEqual(rows[0][1], "Longest Comprehensive Contributor Name")

    def test_b4_order_independence_for_longest_name(self):
        """Longest name should win regardless of whether it is inserted first, middle, or last."""
        # Test case: longest is first
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM gb_database")
        cur.execute("INSERT INTO gb_database (gb_number, name) VALUES ('gb-100', 'Longest Name Here')")
        cur.execute("INSERT INTO gb_database (gb_number, name) VALUES ('GB 100', 'Short')")
        conn.commit()
        conn.close()

        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):
            self.app.cleanse_gb_database()

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT gb_number, name FROM gb_database WHERE gb_number='gb100'")
        row = cur.fetchone()
        conn.close()
        self.assertEqual(row[1], "Longest Name Here")


class TestAdversarialB5CurrencySafety(BaseAdversarialM2Test):
    """Adversarial stress-testing of B5: currency extraction robustness."""

    def test_b5_all_currency_edge_cases(self):
        """Symbols without spaces, multiple spaces, tabs, unicode, and None."""
        test_inputs = [
            ("INR (₹)", "INR"),
            ("USD ($)", "USD"),
            ("₹", "₹"),
            ("$", "$"),
            ("€", "€"),
            ("   CHF   (Fr)  ", "CHF"),
            ("\tCAD\t($)\t", "CAD"),
        ]
        for inp, expected in test_inputs:
            res = self.app.get_safe_currency_symbol(inp)
            self.assertEqual(res, expected, f"Failed for input '{inp}'. Got '{res}', expected '{expected}'")

    def test_b5_fallback_when_input_and_settings_are_empty(self):
        """When input is empty and settings['currency'] is empty/whitespace/None, fallback to '₹'."""
        for setting_curr in ["", "   ", None]:
            self.app.settings["currency"] = setting_curr
            for inp in ["", "   ", None]:
                res = self.app.get_safe_currency_symbol(inp)
                self.assertEqual(res, "₹", f"Failed fallback with setting={setting_curr!r}, inp={inp!r}")


class TestAdversarialB6ExcelImportRobustness(BaseAdversarialM2Test):
    """Adversarial stress-testing of B6: Excel import with malformed dates and NaN edge cases."""

    def test_b6_date_parser_adversarial_inputs(self):
        """parse_ui_date rejects truly malformed inputs and cleanly handles valid datetime formats."""
        # Valid cases
        self.assertEqual(Rangtsok_app.parse_ui_date("31-12-2025"), "2025-12-31")
        self.assertEqual(Rangtsok_app.parse_ui_date("2025-12-31"), "2025-12-31")
        self.assertEqual(Rangtsok_app.parse_ui_date("2025/12/31"), "2025-12-31")
        self.assertEqual(Rangtsok_app.parse_ui_date("31/12/2025"), "2025-12-31")
        self.assertEqual(Rangtsok_app.parse_ui_date("2025-12-31 23:59:59"), "2025-12-31")

        # Invalid cases should return None, not crash
        invalid_cases = [
            "", "   ", None, "nan", "NaN", "NaT", "none", "None",
            "32-13-2026", "99-99-9999", "random-text", 123456, True, False, []
        ]
        for inv in invalid_cases:
            try:
                res = Rangtsok_app.parse_ui_date(inv)
                self.assertIsNone(res, f"Expected None for invalid date {inv!r}, got {res!r}")
            except Exception as e:
                self.fail(f"parse_ui_date crashed on input {inv!r}: {e}")

    def test_b6_excel_import_all_nan_row(self):
        """Row where all numeric amount heads are NaN does not corrupt database."""
        heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        data = {
            "Receipt": ["900001"],
            "GB Number": ["IN901"],
            "Name": ["Adversarial NaN User"],
            "Country": ["India"],
            "Place": ["Dharamsala"],
            "Currency": ["INR (₹)"],
            "Transaction Date": ["2026-06-01"],
        }
        for h in heads:
            data[h] = [np.nan]
        data["Total"] = [np.nan]

        df = pd.DataFrame(data)
        excel_path = os.path.join(self.temp_dir, "nan_test.xlsx")
        df.to_excel(excel_path, index=False)

        with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

            self.app.import_batch_excel()
            self.assertFalse(mock_err.called, f"Error occurred: {mock_err.call_args}")
            self.assertTrue(mock_info.called)

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT account_data, total_amount FROM transactions WHERE receipt_no = '900001'")
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        acc_dict = json.loads(row[0])
        for k, v in acc_dict.items():
            self.assertFalse(math.isnan(v) if isinstance(v, float) else False)
        self.assertEqual(row[1], 0.0)


if __name__ == "__main__":
    unittest.main()
