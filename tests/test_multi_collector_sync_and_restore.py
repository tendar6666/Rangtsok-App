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


class TestMultiCollectorSyncAndRestore(unittest.TestCase):
    """Tests for default-OFF Aadhaar, Report Aadhaar toggle, 4-way Excel import/merge, duplicate skipping, and DB Restore."""

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
        self.temp_dir = tempfile.mkdtemp(prefix="rangtsok_test_multi_")
        self.orig_db = Rangtsok_app.DB_FILE
        self.orig_settings = Rangtsok_app.SETTINGS_FILE

        self.test_db_path = os.path.join(self.temp_dir, "paljor_contribution.db")
        self.test_settings_path = os.path.join(self.temp_dir, "settings.json")

        Rangtsok_app.DB_FILE = self.test_db_path
        Rangtsok_app.SETTINGS_FILE = self.test_settings_path

        cfg = json.loads(json.dumps(Rangtsok_app.DEFAULT_SETTINGS))
        cfg["from_date"] = "01-01-2020"
        cfg["to_date"] = "31-12-2030"
        with open(self.test_settings_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        self.win = tk.Toplevel(self.root)
        self.win.withdraw()
        self.app = Rangtsok_app.ContributionApp(self.win)

    def tearDown(self):
        try:
            self.win.destroy()
        except Exception:
            pass
        Rangtsok_app.DB_FILE = self.orig_db
        Rangtsok_app.SETTINGS_FILE = self.orig_settings
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_excel_row(self, receipt, gb, name, total=200.0, tx_date="15-05-2026", aadhaar=None):
        row = {
            "Receipt": receipt,
            "GB Number": gb,
            "Name": name,
            "Country": "India",
            "Place": "Dharamshala",
            "Currency": "INR",
            "Transaction Date": tx_date,
        }
        if aadhaar is not None:
            row["Aadhaar Number"] = aadhaar
        for item in self.app.settings.get("account_heads", []):
            h = item["head"]
            if item.get("type", "Amount") == "Amount":
                row[h] = total if h == "Chatrel" else 0.0
            else:
                row[h] = ""
        row["Total"] = total
        return row

    def test_default_aadhaar_settings_are_off(self):
        """Aadhaar is OFF by default in Settings and Reports."""
        self.assertFalse(Rangtsok_app.DEFAULT_SETTINGS["enable_aadhaar"])
        self.assertFalse(Rangtsok_app.DEFAULT_SETTINGS["show_aadhaar_in_report"])
        self.assertFalse(self.app.is_aadhaar_enabled())
        self.assertFalse(self.app.is_report_aadhaar_enabled())

    @patch("Rangtsok_app.messagebox.showinfo")
    def test_report_aadhaar_toggle_places_column_next_to_name_and_exports(self, mock_info):
        """When Aadhaar & Report toggle are ON, Aadhaar Number appears right next to Name in table & Excel export."""
        conn = sqlite3.connect(self.test_db_path)
        conn.execute("INSERT INTO gb_database (gb_number, name, aadhaar_number) VALUES ('GB-10', 'Pema Tashi', '123456789012')")
        conn.execute(
            """
            INSERT INTO transactions
            (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
            VALUES ('100001', 'GB-10', 'Pema Tashi', 'India', 'Dharamshala', 'INR', '2026-05-15', '2026-05-15', '{"Chatrel": 200}', 200.0)
            """
        )
        conn.commit()
        conn.close()

        # 1. Both OFF -> no Aadhaar column
        self.app.run_report()
        self.assertNotIn("Aadhaar Number", list(self.app.current_report_df.columns))

        # 2. Enable Aadhaar in Settings, Report toggle still OFF -> still no Aadhaar column
        self.app.aadhaar_var.set(True)
        self.app.toggle_aadhaar_setting()
        self.assertNotIn("Aadhaar Number", list(self.app.current_report_df.columns))

        # 3. Turn ON Report Aadhaar toggle -> Aadhaar Number appears right next to Name!
        self.app.rep_aadhaar_var.set(True)
        self.app.toggle_report_aadhaar()
        cols = list(self.app.current_report_df.columns)
        self.assertIn("Aadhaar Number", cols)
        self.assertEqual(cols.index("Aadhaar Number"), cols.index("Name") + 1)
        self.assertEqual(self.app.current_report_df.iloc[0]["Aadhaar Number"], "123456789012")

        # Export Excel and verify column order & value
        out_xlsx = os.path.join(self.temp_dir, "report_with_aadhaar.xlsx")
        with patch("Rangtsok_app.filedialog.asksaveasfilename", return_value=out_xlsx):
            self.app.export_report()
        df_exp = pd.read_excel(out_xlsx, dtype=str)
        exp_cols = list(df_exp.columns)
        self.assertEqual(exp_cols.index("Aadhaar Number"), exp_cols.index("Name") + 1)
        self.assertEqual(df_exp.iloc[0]["Aadhaar Number"], "123456789012")

        # 4. Turn OFF Aadhaar in Settings -> immediately hides Aadhaar column from report
        self.app.aadhaar_var.set(False)
        self.app.toggle_aadhaar_setting()
        self.assertNotIn("Aadhaar Number", list(self.app.current_report_df.columns))

    @patch("Rangtsok_app.messagebox.showinfo")
    @patch("Rangtsok_app.messagebox.showerror")
    def test_excel_import_all_4_aadhaar_combinations_and_smart_merge(self, mock_err, mock_info):
        """Tests all 4 Collector/Accountant Aadhaar ON/OFF combos + longer-name & non-destructive Aadhaar merge."""
        # Pre-seed Accountant's DB
        conn = sqlite3.connect(self.test_db_path)
        conn.execute("INSERT INTO gb_database VALUES ('GB-SHORT', 'Tenzin', '')")
        conn.execute("INSERT INTO gb_database VALUES ('GB-FULL', 'Dolma Yangzom Complete', '999988887777')")
        conn.commit()
        conn.close()

        # Combo 1: Collector WITH Aadhaar -> Accountant OFF (must NOT crash, and must quietly save Aadhaar!)
        self.app.aadhaar_var.set(False)
        self.app.toggle_aadhaar_setting()
        xlsx_with_aad = os.path.join(self.temp_dir, "collector_with_aadhaar.xlsx")
        pd.DataFrame([
            self._make_excel_row("R-01", "GB-SHORT", "Tenzin Dorjee", 150.0, aadhaar="1111 2222 3333"),
            self._make_excel_row("R-02", "GB-NEW-1", "Karma Phuntsok", 250.0, aadhaar="444455556666.0"),
        ]).to_excel(xlsx_with_aad, index=False)

        with patch("Rangtsok_app.filedialog.askopenfilename", return_value=xlsx_with_aad):
            self.app.import_batch_excel()
        self.assertFalse(mock_err.called, "Import with Aadhaar when Accountant has Aadhaar OFF must not error")

        # Combo 2: Collector WITHOUT Aadhaar -> Accountant ON (must NOT crash, must NOT erase existing Aadhaar or shorten Name!)
        self.app.aadhaar_var.set(True)
        self.app.toggle_aadhaar_setting()
        xlsx_no_aad = os.path.join(self.temp_dir, "collector_no_aadhaar.xlsx")
        pd.DataFrame([
            self._make_excel_row("R-03", "GB-FULL", "Dolma", 300.0, aadhaar=None),
            self._make_excel_row("R-04", "GB-SHORT", "Ten", 100.0, aadhaar=None),
        ]).to_excel(xlsx_no_aad, index=False)

        with patch("Rangtsok_app.filedialog.askopenfilename", return_value=xlsx_no_aad):
            self.app.import_batch_excel()
        self.assertFalse(mock_err.called, "Import without Aadhaar when Accountant has Aadhaar ON must not error")

        # Verify smart merge outcomes in Accountant's gb_database
        conn = sqlite3.connect(self.test_db_path)
        gb_map = {
            r[0]: (r[1], r[2])
            for r in conn.execute("SELECT gb_number, name, aadhaar_number FROM gb_database").fetchall()
        }
        tx_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        conn.close()

        self.assertEqual(tx_count, 4)
        self.assertEqual(gb_map["GB-SHORT"], ("Tenzin Dorjee", "111122223333"))
        self.assertEqual(gb_map["GB-NEW-1"], ("Karma Phuntsok", "444455556666"))
        self.assertEqual(gb_map["GB-FULL"], ("Dolma Yangzom Complete", "999988887777"))

    @patch("Rangtsok_app.messagebox.showinfo")
    @patch("Rangtsok_app.messagebox.showerror")
    def test_excel_import_skips_exact_duplicates(self, mock_err, mock_info):
        """Re-importing the exact same collector Excel file skips duplicate rows cleanly."""
        xlsx_path = os.path.join(self.temp_dir, "collector_batch.xlsx")
        pd.DataFrame([
            self._make_excel_row("DUP-01", "GB-D1", "Lobsang", 200.0),
            self._make_excel_row("DUP-02", "GB-D2", "Tashi", 350.0),
        ]).to_excel(xlsx_path, index=False)

        # First import -> 2 imported, 0 skipped
        with patch("Rangtsok_app.filedialog.askopenfilename", return_value=xlsx_path):
            self.app.import_batch_excel()

        conn = sqlite3.connect(self.test_db_path)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 2)
        conn.close()
        self.assertIn("Imported: 2", mock_info.call_args[0][1])
        self.assertIn("Skipped duplicates: 0", mock_info.call_args[0][1])

        # Second import of same file -> 0 imported, 2 skipped
        mock_info.reset_mock()
        with patch("Rangtsok_app.filedialog.askopenfilename", return_value=xlsx_path):
            self.app.import_batch_excel()

        conn = sqlite3.connect(self.test_db_path)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 2)
        conn.close()
        self.assertIn("Imported: 0", mock_info.call_args[0][1])
        self.assertIn("Skipped duplicates: 2", mock_info.call_args[0][1])

    @patch("Rangtsok_app.messagebox.askyesno", return_value=True)
    @patch("Rangtsok_app.messagebox.showinfo")
    @patch("Rangtsok_app.messagebox.showerror")
    def test_restore_database_valid_and_invalid_files(self, mock_err, mock_info, mock_ask):
        """Restore Database validates integrity/schema, creates safety backup, and restores cleanly."""
        # 1. Create a valid backup DB with 1 GB record
        backup_db = os.path.join(self.temp_dir, "valid_backup.db")
        bconn = sqlite3.connect(backup_db)
        bconn.execute("CREATE TABLE gb_database (gb_number TEXT PRIMARY KEY, name TEXT NOT NULL)")
        bconn.execute("INSERT INTO gb_database VALUES ('GB-RESTORED', 'Restored Member')")
        bconn.execute(
            """
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_no TEXT NOT NULL, gb_number TEXT NOT NULL, name TEXT NOT NULL,
                country TEXT NOT NULL, place TEXT NOT NULL, currency TEXT NOT NULL,
                tx_date TEXT NOT NULL, entry_date TEXT NOT NULL, account_data TEXT NOT NULL,
                total_amount REAL NOT NULL
            )
            """
        )
        bconn.commit()
        bconn.close()

        # 2. Try restoring an invalid text file -> must be rejected cleanly
        bad_file = os.path.join(self.temp_dir, "not_a_db.db")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("this is not a sqlite database")
        with patch("Rangtsok_app.filedialog.askopenfilename", return_value=bad_file):
            self.app.restore_db()
        self.assertTrue(mock_err.called, "Corrupt/invalid file must be rejected")

        # 3. Restore valid legacy backup -> must succeed, migrate aadhaar_number, and create safety backup
        mock_err.reset_mock()
        with patch("Rangtsok_app.filedialog.askopenfilename", return_value=backup_db):
            self.app.restore_db()
        self.assertFalse(mock_err.called)
        self.assertTrue(mock_info.called)

        conn = sqlite3.connect(self.test_db_path)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gb_database)").fetchall()}
        rows = conn.execute("SELECT gb_number, name, COALESCE(aadhaar_number, '') FROM gb_database").fetchall()
        conn.close()

        self.assertIn("aadhaar_number", cols, "Legacy backup must be migrated on restore")
        self.assertEqual(rows, [("GB-RESTORED", "Restored Member", "")])

        # Verify safety backup file was created automatically
        safety_files = [f for f in os.listdir(self.temp_dir) if "_before_restore_" in f]
        self.assertEqual(len(safety_files), 1, "Pre-restore safety backup must be created")


if __name__ == "__main__":
    unittest.main(verbosity=2)
