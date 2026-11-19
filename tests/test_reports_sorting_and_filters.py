import datetime
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
import tkinter as tk
import ttkbootstrap as tb

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Rangtsok_app


class TestReportsSortingAndFilters(unittest.TestCase):
    """Tests for 2-zone Reports & Filters UI, Receipt filter, Sort By/Order, and Header-click sorting."""

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
        self.temp_dir = tempfile.mkdtemp(prefix="rangtsok_test_rep_sort_")
        self.orig_db = Rangtsok_app.DB_FILE
        self.orig_settings = Rangtsok_app.SETTINGS_FILE

        self.test_db_path = os.path.join(self.temp_dir, "test.db")
        self.test_settings_path = os.path.join(self.temp_dir, "settings.json")

        Rangtsok_app.DB_FILE = self.test_db_path
        Rangtsok_app.SETTINGS_FILE = self.test_settings_path

        default_settings = json.loads(json.dumps(Rangtsok_app.DEFAULT_SETTINGS))
        default_settings["from_date"] = "01-01-2025"
        default_settings["to_date"] = "31-12-2027"
        with open(self.test_settings_path, "w", encoding="utf-8") as f:
            json.dump(default_settings, f)

        self.win = tk.Toplevel(self.root)
        self.win.withdraw()
        self.app = Rangtsok_app.ContributionApp(self.win)

        # Seed diverse transactions including a backdated entry inserted last
        conn = sqlite3.connect(self.test_db_path)
        rows = [
            ("100", "GB-01", "Tenzin", "India", "Dharamshala", "INR", "2026-05-10", "2026-05-10", '{"Chatrel": 200}', 200.0),
            ("9", "GB-02", "Dolma", "India", "Dharamshala", "INR", "2026-03-15", "2026-05-11", '{"Chatrel": 500}', 500.0),
            ("20", "GB-03", "Karma", "India", "Delhi", "INR", "2026-08-01", "2026-05-12", '{"Chatrel": 100}', 100.0),
            ("1000", "GB-04", "Sonam", "India", "Dharamshala", "INR", "2025-10-09", "2026-05-13", '{"Chatrel": 350}', 350.0),
        ]
        conn.executemany(
            """
            INSERT INTO transactions
            (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        try:
            self.win.destroy()
        except Exception:
            pass
        Rangtsok_app.DB_FILE = self.orig_db
        Rangtsok_app.SETTINGS_FILE = self.orig_settings
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_sort_is_entry_order_ascending(self):
        """Default sort is Entry Order (ID) Ascending — backdated latest entry stays last."""
        self.assertEqual(self.app.flt_sort_by.get(), "Entry Order (ID)")
        self.assertIn("Ascending", self.app.flt_sort_order.get())
        self.app.run_report()
        receipts = list(self.app.current_report_df["Receipt"])
        self.assertEqual(receipts, ["100", "9", "20", "1000"])
        self.assertEqual(self.app.current_report_raw_ids, [1, 2, 3, 4])

    def test_sort_by_entry_order_descending(self):
        """Entry Order (ID) Descending puts latest entered record first even when backdated."""
        self.app.flt_sort_by.set("Entry Order (ID)")
        self.app.flt_sort_order.set("Descending (Newest / Highest First)")
        self.app.run_report()
        receipts = list(self.app.current_report_df["Receipt"])
        self.assertEqual(receipts, ["1000", "20", "9", "100"])
        self.assertEqual(self.app.current_report_raw_ids, [4, 3, 2, 1])

    def test_sort_by_receipt_number_natural_order(self):
        """Receipt Number sorts naturally (9 < 20 < 100 < 1000), not alphabetically."""
        self.app.flt_sort_by.set("Receipt Number")
        self.app.flt_sort_order.set("Ascending (Oldest / Lowest First)")
        self.app.run_report()
        self.assertEqual(list(self.app.current_report_df["Receipt"]), ["9", "20", "100", "1000"])

        self.app.flt_sort_order.set("Descending (Newest / Highest First)")
        self.app._on_sort_control_change()
        self.assertEqual(list(self.app.current_report_df["Receipt"]), ["1000", "100", "20", "9"])

    def test_sort_by_transaction_date_chronological(self):
        """Transaction Date sorts chronologically by year-month-day, not string DD-MM-YYYY."""
        self.app.flt_sort_by.set("Transaction Date")
        self.app.flt_sort_order.set("Ascending (Oldest / Lowest First)")
        self.app.run_report()
        dates = list(self.app.current_report_df["Transaction Date"])
        self.assertEqual(dates, ["09-10-2025", "15-03-2026", "10-05-2026", "01-08-2026"])

        self.app.flt_sort_order.set("Descending (Newest / Highest First)")
        self.app._on_sort_control_change()
        dates_desc = list(self.app.current_report_df["Transaction Date"])
        self.assertEqual(dates_desc, ["01-08-2026", "10-05-2026", "15-03-2026", "09-10-2025"])

    def test_sort_by_total_amount(self):
        """Total Amount sorts numerically Asc and Desc."""
        self.app.flt_sort_by.set("Total Amount")
        self.app.flt_sort_order.set("Ascending (Oldest / Lowest First)")
        self.app.run_report()
        self.assertEqual(list(self.app.current_report_df["Total"]), [100.0, 200.0, 350.0, 500.0])

        self.app.flt_sort_order.set("Descending (Newest / Highest First)")
        self.app._on_sort_control_change()
        self.assertEqual(list(self.app.current_report_df["Total"]), [500.0, 350.0, 200.0, 100.0])

    def test_click_column_header_toggles_sort_and_keeps_total_pinned(self):
        """Clicking a column header toggles Asc/Desc, keeps TOTAL pinned last, and syncs raw IDs."""
        self.app.run_report()

        # First click on Name -> Ascending
        self.app.sort_report_by_column("Name")
        self.assertEqual(list(self.app.current_report_df["Name"]), ["Dolma", "Karma", "Sonam", "Tenzin"])
        self.assertIn("▲", self.app.rep_tree.heading("Name", "text"))
        children = self.app.rep_tree.get_children()
        self.assertEqual(children[-1], "total", "TOTAL row must stay pinned at the bottom")

        # Verify double-click on first row opens Dolma (id=2), proving raw_ids stay synced
        self.app.rep_tree.selection_set("0")
        self.app.on_report_double_click()
        self.assertEqual(self.app.ent_name.get(), "Dolma")
        self.assertEqual(self.app.current_edit_id, 2)

        # Second click on Name -> Descending
        self.app.sort_report_by_column("Name")
        self.assertEqual(list(self.app.current_report_df["Name"]), ["Tenzin", "Sonam", "Karma", "Dolma"])
        self.assertIn("▼", self.app.rep_tree.heading("Name", "text"))
        self.assertEqual(self.app.rep_tree.get_children()[-1], "total")

    def test_receipt_number_filter_and_reset(self):
        """Receipt No filter narrows results and Reset restores all defaults."""
        self.app.flt_receipt.insert(0, "1000")
        self.app.run_report()
        self.assertEqual(len(self.app.current_report_df), 1)
        self.assertEqual(self.app.current_report_df.iloc[0]["Name"], "Sonam")

        self.app.reset_report_filters()
        self.assertEqual(self.app.flt_receipt.get(), "")
        self.assertEqual(len(self.app.current_report_df), 4)
        self.assertEqual(self.app.flt_sort_by.get(), "Entry Order (ID)")

    @patch("Rangtsok_app.messagebox.showinfo")
    def test_export_excel_preserves_sort_order(self, mock_info):
        """Export Excel writes rows in the exact active sort order with TOTAL at the bottom."""
        self.app.flt_sort_by.set("Receipt Number")
        self.app.flt_sort_order.set("Descending (Newest / Highest First)")
        self.app.run_report()

        out_xlsx = os.path.join(self.temp_dir, "sorted_export.xlsx")
        with patch("Rangtsok_app.filedialog.asksaveasfilename", return_value=out_xlsx):
            self.app.export_report()

        df_out = pd.read_excel(out_xlsx)
        receipts_out = [str(x) for x in df_out["Receipt"].tolist()]
        self.assertEqual(receipts_out, ["1000", "100", "20", "9", "TOTAL"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
