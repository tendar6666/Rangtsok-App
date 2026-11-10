"""Adversarial stress and edge-case challenge suite for Excel Data Import (FEAT-10 / B6)
and SQLite Database Bulk Ingestion Integrity.

Tests cover:
1. Mixed date format acceptance (ISO YYYY-MM-DD, DD-MM-YYYY, slashes, pd.Timestamp, datetime).
2. Clean rejection of sheets with invalid date strings (non-existent dates, malformed formats).
3. Clean rejection of sheets with empty date cells (None, np.nan, empty string).
4. Date-type account heads (ISO conversion to UI DD-MM-YYYY, empty/NaN handling, invalid strings).
5. Numerical amounts sanitization (NaN/None to 0.0, Inf/-Inf to 0.0, non-numeric garbage to 0.0).
6. Negative financial amounts preservation (adjustments, refunds) in account_data and total.
7. Total amount calculation robustness (missing total, NaN total, Inf total, garbage total).
8. RFC 8259 JSON validity verification on transactions.account_data (no NaN/Infinity tokens).
9. Bulk ingestion stress test with a heterogeneous 100-row batch.
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
import math
import tkinter as tk
import ttkbootstrap as tb
import pandas as pd
import numpy as np

# Ensure workspace root is in python path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import Rangtsok_app


class BaseExcelImportAdversarialTest(unittest.TestCase):
    """Isolated environment for Excel import stress testing."""

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

    def _create_excel_file(self, rows_data, filename="adversarial_import.xlsx"):
        """Utility to write a list of dicts to an Excel workbook matching settings heads."""
        df = pd.DataFrame(rows_data)
        file_path = os.path.join(self.temp_dir, filename)
        df.to_excel(file_path, index=False)
        return file_path

    def _get_base_row(self, receipt="900001", gb="GB-9001", name="Adversarial User",
                       country="India", place="Dharamsala", currency="INR (₹)",
                       tx_date="2026-05-15"):
        """Constructs a basic valid dictionary matching expected Excel template."""
        row = {
            "Receipt": receipt,
            "GB Number": gb,
            "Name": name,
            "Country": country,
            "Place": place,
            "Currency": currency,
            "Transaction Date": tx_date,
        }
        for head in self.app.settings.get("account_heads", []):
            h_name = head["head"]
            h_type = head.get("type", "Amount")
            row[h_name] = 100.0 if h_type == "Amount" else "01-04-2026"
        row["Total"] = 100.0
        return row


class TestExcelDateAdversarial(BaseExcelImportAdversarialTest):
    """Stress testing date parsing, tolerance, and rejection during Excel ingestion."""

    def test_mixed_valid_date_formats_ingested_cleanly(self):
        """Mixed valid ISO dates (YYYY-MM-DD), standard dates (DD-MM-YYYY),
        slashes (DD/MM/YYYY and YYYY/MM/DD), pd.Timestamp, and datetime objects
        must all import successfully and normalize to YYYY-MM-DD in SQLite.
        """
        rows = [
            self._get_base_row(receipt="910001", tx_date="2026-05-15"),                     # ISO YYYY-MM-DD
            self._get_base_row(receipt="910002", tx_date="15-05-2026"),                     # DD-MM-YYYY
            self._get_base_row(receipt="910003", tx_date="15/05/2026"),                     # DD/MM/YYYY
            self._get_base_row(receipt="910004", tx_date="2026/05/15"),                     # YYYY/MM/DD
            self._get_base_row(receipt="910005", tx_date=pd.Timestamp("2026-05-15")),       # pd.Timestamp
            self._get_base_row(receipt="910006", tx_date=datetime.datetime(2026, 5, 15, 10, 30)), # datetime
            self._get_base_row(receipt="910007", tx_date=datetime.date(2026, 5, 15)),       # date
        ]
        excel_path = self._create_excel_file(rows, "mixed_valid_dates.xlsx")

        with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

            self.app.import_batch_excel()
            self.assertFalse(mock_err.called, f"Unexpected error dialog: {mock_err.call_args}")
            self.assertTrue(mock_info.called, "Import success dialog should be shown")

        # Verify all 7 records in SQLite with normalized tx_date = 2026-05-15
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT receipt_no, tx_date FROM transactions ORDER BY receipt_no ASC")
        db_rows = cur.fetchall()
        conn.close()

        self.assertEqual(len(db_rows), 7)
        for r_no, tx_d in db_rows:
            self.assertEqual(tx_d, "2026-05-15", f"Receipt {r_no} date was not normalized to ISO YYYY-MM-DD")

    def test_invalid_date_strings_rejected_with_zero_ingestion(self):
        """Sheets with invalid date strings (non-existent days, invalid months,
        non-date text) must be strictly rejected with an informative error dialog,
        and ZERO rows should be committed to the database.
        """
        adversarial_invalid_dates = [
            "not-a-real-date",
            "32-01-2026",      # Invalid day
            "15-13-2026",      # Invalid month
            "2026-02-31",      # Invalid leap/month day
            "2026-99-99",      # Out of bounds
            "99/99/9999",      # Out of bounds slash
        ]

        for bad_date in adversarial_invalid_dates:
            with self.subTest(bad_date=bad_date):
                rows = [
                    self._get_base_row(receipt="920001", tx_date="2026-05-15"),  # Valid row
                    self._get_base_row(receipt="920002", tx_date=bad_date),      # Invalid row
                ]
                excel_path = self._create_excel_file(rows, f"invalid_date_{bad_date.replace('/', '_')}.xlsx")

                with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
                     patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
                     patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

                    self.app.import_batch_excel()
                    self.assertTrue(mock_err.called, f"Expected Date Format Error for invalid date '{bad_date}'")
                    err_args = mock_err.call_args[0]
                    self.assertIn("Date Format Error", err_args[0])
                    self.assertFalse(mock_info.called, "Import success should NOT be called on invalid dates")

                # Verify atomicity: 0 rows inserted into DB
                conn = sqlite3.connect(self.test_db_path)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM transactions")
                count = cur.fetchone()[0]
                conn.close()
                self.assertEqual(count, 0, f"Database contaminated after rejected import for '{bad_date}'")

    def test_empty_and_nan_date_cells_rejected_cleanly(self):
        """Empty date cells (None, np.nan, '', '   ') in Transaction Date must be
        identified as missing/invalid and rejected before inserting any records.
        """
        empty_date_variants = [None, np.nan, "", "   ", "nan", "NaT"]

        for empty_val in empty_date_variants:
            with self.subTest(empty_val=str(empty_val)):
                rows = [
                    self._get_base_row(receipt="930001", tx_date=empty_val),
                ]
                excel_path = self._create_excel_file(rows, "empty_date.xlsx")

                with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
                     patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
                     patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

                    self.app.import_batch_excel()
                    self.assertTrue(mock_err.called, f"Expected rejection for empty date {empty_val}")
                    self.assertFalse(mock_info.called)

                # Database must remain untouched
                conn = sqlite3.connect(self.test_db_path)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM transactions")
                count = cur.fetchone()[0]
                conn.close()
                self.assertEqual(count, 0)

    def test_excel_trailing_total_row_skipped_without_triggering_date_error(self):
        """Exported sheets often end with a summary row where Receipt='TOTAL' and
        Transaction Date is empty or string 'TOTAL'. Ingestion must skip this row
        cleanly without raising a Date Format Error.
        """
        rows = [
            self._get_base_row(receipt="940001", tx_date="2026-05-15"),
            self._get_base_row(receipt="940002", tx_date="16-05-2026"),
            # Trailing summary row
            {
                "Receipt": "TOTAL",
                "GB Number": "",
                "Name": "",
                "Country": "",
                "Place": "",
                "Currency": "",
                "Transaction Date": "",  # Empty date in summary row
                "Chatrel": 200.0,
                "Total": 200.0,
            }
        ]
        # Fill all configured heads for total row
        for h in self.app.settings.get("account_heads", []):
            if h["head"] not in rows[2]:
                rows[2][h["head"]] = ""

        excel_path = self._create_excel_file(rows, "total_row_import.xlsx")

        with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

            self.app.import_batch_excel()
            self.assertFalse(mock_err.called, f"Total row caused error: {mock_err.call_args}")
            self.assertTrue(mock_info.called)

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT receipt_no FROM transactions ORDER BY receipt_no ASC")
        db_receipts = [r[0] for r in cur.fetchall()]
        conn.close()

        self.assertEqual(db_receipts, ["940001", "940002"])


class TestExcelAmountsAndInfinityAdversarial(BaseExcelImportAdversarialTest):
    """Stress testing numerical edge cases: NaN, infinity, negative values, and non-numeric garbage."""

    def test_missing_nan_and_none_amounts_converted_to_zero(self):
        """Missing or NaN numerical amounts in account heads must be safely converted
        to 0.0 float in account_data JSON, preventing non-standard JSON in SQLite.
        """
        row1 = self._get_base_row(receipt="950001")
        row1["Chatrel"] = np.nan
        row1["Donation"] = None
        row1["Total"] = np.nan

        excel_path = self._create_excel_file([row1], "nan_amounts.xlsx")

        with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

            self.app.import_batch_excel()
            self.assertFalse(mock_err.called, f"Import error: {mock_err.call_args}")
            self.assertTrue(mock_info.called)

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT account_data, total_amount FROM transactions WHERE receipt_no='950001'")
        acc_json_str, total_val = cur.fetchone()
        conn.close()

        # Strict JSON parse
        acc_dict = json.loads(acc_json_str)
        self.assertEqual(acc_dict.get("Chatrel"), 0.0)
        self.assertEqual(acc_dict.get("Donation"), 0.0)
        self.assertFalse(math.isnan(total_val))
        self.assertFalse(math.isinf(total_val))
        # Total should equal sum of numeric heads
        expected_total = sum(v for v in acc_dict.values() if isinstance(v, (int, float)))
        self.assertEqual(total_val, expected_total)

    def test_infinity_values_strictly_sanitized_to_zero(self):
        """Infinities (float('inf'), float('-inf'), or string 'inf' / 'Infinity')
        must be intercepted and converted to 0.0, because SQLite/RFC-8259 JSON cannot store Inf.
        """
        row1 = self._get_base_row(receipt="960001")
        row1["Chatrel"] = float("inf")
        row1["Donation"] = float("-inf")
        row1["Total"] = float("inf")

        row2 = self._get_base_row(receipt="960002")
        row2["Chatrel"] = "Infinity"
        row2["Donation"] = "-Infinity"
        row2["Total"] = "inf"

        excel_path = self._create_excel_file([row1, row2], "infinity_amounts.xlsx")

        with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

            self.app.import_batch_excel()
            self.assertFalse(mock_err.called, f"Import error: {mock_err.call_args}")
            self.assertTrue(mock_info.called)

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT receipt_no, account_data, total_amount FROM transactions ORDER BY receipt_no ASC")
        rows = cur.fetchall()
        conn.close()

        self.assertEqual(len(rows), 2)
        for r_no, acc_str, tot in rows:
            # Check raw string does NOT contain Infinity tokens
            self.assertNotIn("Infinity", acc_str, f"Row {r_no} contains 'Infinity' in raw JSON!")
            self.assertNotIn("NaN", acc_str, f"Row {r_no} contains 'NaN' in raw JSON!")

            acc = json.loads(acc_str)
            self.assertEqual(acc.get("Chatrel"), 0.0, f"Row {r_no} Chatrel was not sanitized from inf to 0.0")
            self.assertEqual(acc.get("Donation"), 0.0, f"Row {r_no} Donation was not sanitized from -inf to 0.0")
            self.assertFalse(math.isinf(tot), f"Row {r_no} total_amount is infinite!")
            self.assertFalse(math.isnan(tot), f"Row {r_no} total_amount is NaN!")

    def test_negative_values_preserved_accurately(self):
        """Negative financial adjustments/refunds (e.g. -50.0, -125.50) must NOT
        be wiped to 0.0; they must be accurately preserved in account_data and total.
        """
        row1 = self._get_base_row(receipt="970001")
        row1["Chatrel"] = 200.0
        row1["Donation"] = -50.0   # Negative adjustment / refund
        row1["Total"] = 150.0

        excel_path = self._create_excel_file([row1], "negative_amounts.xlsx")

        with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

            self.app.import_batch_excel()
            self.assertFalse(mock_err.called)
            self.assertTrue(mock_info.called)

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT account_data, total_amount FROM transactions WHERE receipt_no='970001'")
        acc_str, tot = cur.fetchone()
        conn.close()

        acc = json.loads(acc_str)
        self.assertEqual(acc.get("Chatrel"), 200.0)
        self.assertEqual(acc.get("Donation"), -50.0, "Negative amount was wiped or modified!")
        self.assertEqual(tot, 150.0, "Total amount mismatch for negative adjustment")

    def test_non_numeric_garbage_in_amount_columns_defaulted_to_zero(self):
        """Strings like 'N/A', 'pending', '###', '$250', 'None' placed in Amount columns
        must be safely handled and defaulted to 0.0 without throwing ValueError.
        """
        row1 = self._get_base_row(receipt="980001")
        row1["Chatrel"] = "N/A"
        row1["Donation"] = "$250"
        row1["Total"] = "BAD_TOTAL"

        excel_path = self._create_excel_file([row1], "garbage_amounts.xlsx")

        with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

            self.app.import_batch_excel()
            self.assertFalse(mock_err.called, f"Non-numeric garbage crashed import: {mock_err.call_args}")
            self.assertTrue(mock_info.called)

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT account_data, total_amount FROM transactions WHERE receipt_no='980001'")
        acc_str, tot = cur.fetchone()
        conn.close()

        acc = json.loads(acc_str)
        self.assertEqual(acc.get("Chatrel"), 0.0)
        self.assertEqual(acc.get("Donation"), 0.0)
        # Total was 'BAD_TOTAL', so fallback to sum of numeric heads
        expected_total = sum(v for v in acc.values() if isinstance(v, (int, float)))
        self.assertEqual(tot, expected_total)


class TestDateAccountHeadsAdversarial(BaseExcelImportAdversarialTest):
    """Stress testing Date-type account heads within account_data."""

    def test_date_account_heads_iso_conversion_and_nan_handling(self):
        """Date-type heads (e.g. 'Arear Start Date', 'Arrear End Date'):
        - ISO string '2026-04-01' -> formatted to UI format '01-04-2026'
        - Standard '01-04-2026' -> retained as '01-04-2026'
        - Datetime object -> formatted to '01-04-2026'
        - NaN / None / 'nan' / 'nat' -> empty string ''
        """
        date_heads = [h["head"] for h in self.app.settings.get("account_heads", []) if h.get("type") == "Date"]
        self.assertTrue(len(date_heads) >= 1, "At least one Date-type head should exist in settings")

        d_head = date_heads[0]

        row1 = self._get_base_row(receipt="990001")
        row1[d_head] = "2026-04-01"  # ISO

        row2 = self._get_base_row(receipt="990002")
        row2[d_head] = "01-04-2026"  # Standard

        row3 = self._get_base_row(receipt="990003")
        row3[d_head] = np.nan        # NaN

        row4 = self._get_base_row(receipt="990004")
        row4[d_head] = pd.Timestamp("2026-04-01") # Timestamp

        excel_path = self._create_excel_file([row1, row2, row3, row4], "date_heads_import.xlsx")

        with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

            self.app.import_batch_excel()
            self.assertFalse(mock_err.called)
            self.assertTrue(mock_info.called)

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT receipt_no, account_data FROM transactions ORDER BY receipt_no ASC")
        rows = cur.fetchall()
        conn.close()

        self.assertEqual(len(rows), 4)
        acc1 = json.loads(rows[0][1])
        acc2 = json.loads(rows[1][1])
        acc3 = json.loads(rows[2][1])
        acc4 = json.loads(rows[3][1])

        # Row 1: ISO converted to DD-MM-YYYY
        self.assertEqual(acc1.get(d_head), "01-04-2026")
        # Row 2: Standard DD-MM-YYYY retained
        self.assertEqual(acc2.get(d_head), "01-04-2026")
        # Row 3: NaN converted to empty string
        self.assertEqual(acc3.get(d_head), "")
        # Row 4: Timestamp formatted to DD-MM-YYYY
        self.assertEqual(acc4.get(d_head), "01-04-2026")


class TestDatabaseIntegrityAndBulkIngestionStress(BaseExcelImportAdversarialTest):
    """Stress testing SQLite database integrity, RFC 8259 compliance, and 100-row bulk ingestion."""

    def test_database_strictly_valid_rfc8259_json_no_tokens(self):
        """Every imported row in the transactions table must contain strictly valid
        RFC 8259 JSON. SQLite json_valid() must evaluate to true, and raw strings
        must never contain 'NaN' or 'Infinity'.
        """
        rows = []
        for i in range(1, 26):
            r = self._get_base_row(receipt=f"800{i:03d}")
            # Inject various tricky values across rows
            if i % 5 == 0:
                r["Chatrel"] = np.nan
            elif i % 5 == 1:
                r["Chatrel"] = float("inf")
            elif i % 5 == 2:
                r["Chatrel"] = -75.0
            elif i % 5 == 3:
                r["Chatrel"] = "junk_data"
            else:
                r["Chatrel"] = 150.0

            r["Total"] = np.nan  # Let calculation take over
            rows.append(r)

        excel_path = self._create_excel_file(rows, "json_integrity_batch.xlsx")

        with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
             patch.object(Rangtsok_app.messagebox, "showinfo"), \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

            self.app.import_batch_excel()
            self.assertFalse(mock_err.called)

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, receipt_no, account_data, total_amount FROM transactions")
        db_records = cur.fetchall()

        # Check SQLite built-in json_valid if supported
        try:
            cur.execute("SELECT COUNT(*) FROM transactions WHERE json_valid(account_data) = 0")
            invalid_json_count = cur.fetchone()[0]
            self.assertEqual(invalid_json_count, 0, f"Found {invalid_json_count} rows with invalid SQLite JSON!")
        except sqlite3.OperationalError:
            # Older SQLite without json1 extension compiled
            pass

        conn.close()

        self.assertEqual(len(db_records), 25)
        for tx_id, r_no, acc_str, tot in db_records:
            # 1. No invalid tokens in raw serialized string
            self.assertNotIn("NaN", acc_str, f"Row {r_no} raw JSON contains 'NaN'")
            self.assertNotIn("Infinity", acc_str, f"Row {r_no} raw JSON contains 'Infinity'")
            self.assertNotIn("-Infinity", acc_str, f"Row {r_no} raw JSON contains '-Infinity'")

            # 2. Strict python JSON parse
            parsed = json.loads(acc_str)
            self.assertIsInstance(parsed, dict)

            # 3. Total amount is finite
            self.assertFalse(math.isnan(tot), f"Row {r_no} total is NaN")
            self.assertFalse(math.isinf(tot), f"Row {r_no} total is Infinite")

            # 4. Total matches sum of numeric heads
            calc_sum = sum(v for v in parsed.values() if isinstance(v, (int, float)))
            self.assertAlmostEqual(tot, calc_sum, places=2)

    def test_bulk_100_row_heterogeneous_stress_ingestion(self):
        """Stress ingestion of a 100-row heterogeneous spreadsheet combining:
        - ISO dates, standard dates, slash dates
        - Negative adjustment rows
        - NaN and missing amount cells
        - Non-numeric garbage text
        - Infinity values
        - Clean total row skipping
        Verifies complete database consistency, correct total_amount, and gb_database population.
        """
        rows = []
        for i in range(1, 101):
            date_variant = "2026-05-15" if i % 3 == 0 else ("15-05-2026" if i % 3 == 1 else "15/05/2026")
            r = self._get_base_row(
                receipt=f"BULK_{i:04d}",
                gb=f"GB-{i:04d}",
                name=f"Bulk Member {i}",
                tx_date=date_variant
            )

            # Permute head values
            if i % 10 == 0:
                r["Chatrel"] = -100.0  # Negative refund
            elif i % 10 == 1:
                r["Chatrel"] = np.nan
            elif i % 10 == 2:
                r["Chatrel"] = float("inf")
            elif i % 10 == 3:
                r["Chatrel"] = "NotANumber"
            elif i % 10 == 4:
                r["Chatrel"] = 0.0
            else:
                r["Chatrel"] = float(i * 10)

            r["Total"] = np.nan  # Force automatic recalculation
            rows.append(r)

        # Append summary total row
        total_row = {
            "Receipt": "TOTAL",
            "GB Number": "",
            "Name": "",
            "Country": "",
            "Place": "",
            "Currency": "",
            "Transaction Date": "",
            "Chatrel": 50000.0,
            "Total": 50000.0,
        }
        for h in self.app.settings.get("account_heads", []):
            if h["head"] not in total_row:
                total_row[h["head"]] = ""
        rows.append(total_row)

        excel_path = self._create_excel_file(rows, "bulk_100_stress.xlsx")

        with patch.object(Rangtsok_app.filedialog, "askopenfilename", return_value=excel_path), \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info, \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:

            self.app.import_batch_excel()
            self.assertFalse(mock_err.called, f"Bulk import failed with error: {mock_err.call_args}")
            self.assertTrue(mock_info.called)

        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()

        # 1. Exactly 100 transactions inserted (summary row skipped)
        cur.execute("SELECT COUNT(*) FROM transactions")
        tx_count = cur.fetchone()[0]
        self.assertEqual(tx_count, 100, f"Expected 100 transactions, found {tx_count}")

        # 2. Exactly 100 GB database records populated
        cur.execute("SELECT COUNT(*) FROM gb_database")
        gb_count = cur.fetchone()[0]
        self.assertEqual(gb_count, 100, f"Expected 100 GB records, found {gb_count}")

        # 3. All transaction JSONs and totals are valid and match
        cur.execute("SELECT receipt_no, account_data, total_amount FROM transactions")
        all_txs = cur.fetchall()
        conn.close()

        for r_no, acc_str, tot in all_txs:
            parsed = json.loads(acc_str)
            calc_sum = sum(v for v in parsed.values() if isinstance(v, (int, float)))
            self.assertAlmostEqual(tot, calc_sum, places=2, msg=f"Total mismatch for {r_no}")
            self.assertFalse(math.isnan(tot))
            self.assertFalse(math.isinf(tot))


if __name__ == "__main__":
    unittest.main(verbosity=2)
