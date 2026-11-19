import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk
import ttkbootstrap as tb

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Rangtsok_app


class TestRecentEntriesAndAadhaar(unittest.TestCase):
    """Comprehensive tests for Recent Entries panel, Aadhaar Number feature, and Auto-Lookup/Update."""

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
        self.temp_dir = tempfile.mkdtemp(prefix="rangtsok_test_recent_aadhaar_")
        self.orig_db = Rangtsok_app.DB_FILE
        self.orig_settings = Rangtsok_app.SETTINGS_FILE

        self.test_db_path = os.path.join(self.temp_dir, "test.db")
        self.test_settings_path = os.path.join(self.temp_dir, "settings.json")

        Rangtsok_app.DB_FILE = self.test_db_path
        Rangtsok_app.SETTINGS_FILE = self.test_settings_path

        default_settings = json.loads(json.dumps(Rangtsok_app.DEFAULT_SETTINGS))
        default_settings["from_date"] = "01-01-2026"
        default_settings["to_date"] = "31-12-2026"
        default_settings["enable_aadhaar"] = True
        with open(self.test_settings_path, "w", encoding="utf-8") as f:
            json.dump(default_settings, f)

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

    def test_schema_migration_adds_aadhaar_column(self):
        """Legacy gb_database without aadhaar_number migrates cleanly without data loss."""
        legacy_db = os.path.join(self.temp_dir, "legacy.db")
        conn = sqlite3.connect(legacy_db)
        cur = conn.cursor()
        cur.execute("CREATE TABLE gb_database (gb_number TEXT PRIMARY KEY, name TEXT NOT NULL)")
        cur.execute("INSERT INTO gb_database (gb_number, name) VALUES ('GB-OLD-1', 'Tenzin Legacy')")
        conn.commit()
        conn.close()

        prev_db = Rangtsok_app.DB_FILE
        try:
            Rangtsok_app.DB_FILE = legacy_db
            Rangtsok_app.init_db()
            conn = sqlite3.connect(legacy_db)
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(gb_database)")
            cols = {r[1] for r in cur.fetchall()}
            self.assertIn("aadhaar_number", cols)
            cur.execute("SELECT gb_number, name, COALESCE(aadhaar_number, '') FROM gb_database")
            row = cur.fetchone()
            conn.close()
            self.assertEqual(row, ("GB-OLD-1", "Tenzin Legacy", ""))
        finally:
            Rangtsok_app.DB_FILE = prev_db

    def test_clean_aadhaar_sanitization(self):
        """clean_aadhaar normalizes Excel floats, spaces, hyphens, and NaN/None."""
        self.assertEqual(Rangtsok_app.clean_aadhaar(None), "")
        self.assertEqual(Rangtsok_app.clean_aadhaar(float("nan")), "")
        self.assertEqual(Rangtsok_app.clean_aadhaar("  "), "")
        self.assertEqual(Rangtsok_app.clean_aadhaar("123456789012.0"), "123456789012")
        self.assertEqual(Rangtsok_app.clean_aadhaar("1234 5678 9012"), "123456789012")
        self.assertEqual(Rangtsok_app.clean_aadhaar("1234-5678-9012"), "123456789012")
        self.assertEqual(Rangtsok_app.clean_aadhaar("987654321098"), "987654321098")

    def test_aadhaar_toggle_visibility_entry_and_db(self):
        """Toggling Enable Aadhaar Number updates settings, Entry Form widgets, and GB DB displaycolumns."""
        # Initially enabled
        self.assertTrue(self.app.is_aadhaar_enabled())
        self.assertEqual(tuple(self.app.db_tree["displaycolumns"]), ("gb", "name", "aadhaar"))
        self.assertTrue(bool(self.app.ent_aadhaar.grid_info()))

        # Turn OFF
        self.app.aadhaar_var.set(False)
        self.app.toggle_aadhaar_setting()
        self.assertFalse(self.app.is_aadhaar_enabled())
        self.assertEqual(tuple(self.app.db_tree["displaycolumns"]), ("gb", "name"))
        self.assertEqual(self.app.ent_aadhaar.grid_info(), {})

        # Verify persisted in settings.json
        with open(self.test_settings_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        self.assertFalse(saved["enable_aadhaar"])

        # Turn ON
        self.app.aadhaar_var.set(True)
        self.app.toggle_aadhaar_setting()
        self.assertTrue(self.app.is_aadhaar_enabled())
        self.assertEqual(tuple(self.app.db_tree["displaycolumns"]), ("gb", "name", "aadhaar"))
        self.assertTrue(bool(self.app.ent_aadhaar.grid_info()))

    def test_auto_lookup_populates_name_and_aadhaar(self):
        """lookup_gb populates both Full Name and Aadhaar Number case-insensitively."""
        conn = sqlite3.connect(self.test_db_path)
        conn.execute(
            "INSERT INTO gb_database (gb_number, name, aadhaar_number) VALUES (?, ?, ?)",
            ("GB-9001", "Pema Choden", "112233445566"),
        )
        conn.commit()
        conn.close()

        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "gb-9001")
        self.app.lookup_gb()

        self.assertEqual(self.app.ent_name.get(), "Pema Choden")
        self.assertEqual(self.app.ent_aadhaar.get(), "112233445566")
        self.assertIn("Found", self.app.lbl_gb_status.cget("text"))

    @patch("Rangtsok_app.messagebox.showinfo")
    def test_save_entry_auto_upserts_name_and_aadhaar(self, mock_info):
        """Saving an entry automatically inserts new GB holders and updates existing Name/Aadhaar."""
        self.app.ent_receipt.delete(0, tk.END)
        self.app.ent_receipt.insert(0, "200001")
        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "GB-AUTO-1")
        self.app.ent_name.delete(0, tk.END)
        self.app.ent_name.insert(0, "Lobsang Dorje")
        self.app.ent_aadhaar.delete(0, tk.END)
        self.app.ent_aadhaar.insert(0, "2233 4455 6677")
        self.app.ent_tx_date.delete(0, tk.END)
        self.app.ent_tx_date.insert(0, "15-05-2026")

        self.app.save_entry()

        conn = sqlite3.connect(self.test_db_path)
        row = conn.execute(
            "SELECT gb_number, name, aadhaar_number FROM gb_database WHERE gb_number='GB-AUTO-1'"
        ).fetchone()
        conn.close()
        self.assertEqual(row, ("GB-AUTO-1", "Lobsang Dorje", "223344556677"))

        # Now save a second entry for the same GB with updated Name & Aadhaar
        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "gb-auto-1")
        self.app.lookup_gb()
        self.app.ent_name.delete(0, tk.END)
        self.app.ent_name.insert(0, "Lobsang Dorje Updated")
        self.app.ent_aadhaar.delete(0, tk.END)
        self.app.ent_aadhaar.insert(0, "998877665544")
        self.app.ent_tx_date.delete(0, tk.END)
        self.app.ent_tx_date.insert(0, "16-05-2026")

        self.app.save_entry()

        conn = sqlite3.connect(self.test_db_path)
        rows = conn.execute("SELECT gb_number, name, aadhaar_number FROM gb_database").fetchall()
        conn.close()
        self.assertEqual(len(rows), 1, "Case-insensitive upsert must not create duplicate GB records")
        self.assertEqual(rows[0], ("GB-AUTO-1", "Lobsang Dorje Updated", "998877665544"))

    @patch("Rangtsok_app.messagebox.showinfo")
    def test_save_entry_with_aadhaar_disabled_preserves_existing_aadhaar(self, mock_info):
        """Disabling Aadhaar in settings must never erase already-stored Aadhaar numbers on Save."""
        conn = sqlite3.connect(self.test_db_path)
        conn.execute(
            "INSERT INTO gb_database (gb_number, name, aadhaar_number) VALUES (?, ?, ?)",
            ("GB-KEEP-1", "Dolma Yangzom", "445566778899"),
        )
        conn.commit()
        conn.close()

        # Disable Aadhaar
        self.app.aadhaar_var.set(False)
        self.app.toggle_aadhaar_setting()

        self.app.ent_receipt.delete(0, tk.END)
        self.app.ent_receipt.insert(0, "300001")
        self.app.ent_gb.delete(0, tk.END)
        self.app.ent_gb.insert(0, "GB-KEEP-1")
        self.app.ent_name.delete(0, tk.END)
        self.app.ent_name.insert(0, "Dolma Yangzom New")
        self.app.ent_aadhaar.delete(0, tk.END)
        self.app.ent_tx_date.delete(0, tk.END)
        self.app.ent_tx_date.insert(0, "15-05-2026")

        self.app.save_entry()

        conn = sqlite3.connect(self.test_db_path)
        row = conn.execute(
            "SELECT name, aadhaar_number FROM gb_database WHERE gb_number='GB-KEEP-1'"
        ).fetchone()
        conn.close()
        self.assertEqual(row, ("Dolma Yangzom New", "445566778899"))

    @patch("Rangtsok_app.messagebox.showinfo")
    def test_clipboard_import_2_col_and_3_col_with_header(self, mock_info):
        """Clipboard import supports 2-col and 3-col Excel pastes, skips headers, and preserves existing Aadhaar."""
        paste_3col = (
            "GB Number\tFull Name\tAadhaar Number\n"
            "GB-CLIP-1\tTashi Wangdu\t1234 5678 9012\n"
            "GB-CLIP-2\tDechen Lhamo\t987654321098.0\n"
            "GB-CLIP-3\tSonam Phuntsok\n"
        )
        with patch.object(self.app.root, "clipboard_get", return_value=paste_3col):
            self.app.import_from_clipboard()

        conn = sqlite3.connect(self.test_db_path)
        data = {
            r[0]: (r[1], r[2])
            for r in conn.execute("SELECT gb_number, name, aadhaar_number FROM gb_database").fetchall()
        }
        conn.close()

        self.assertEqual(len(data), 3)
        self.assertEqual(data["GB-CLIP-1"], ("Tashi Wangdu", "123456789012"))
        self.assertEqual(data["GB-CLIP-2"], ("Dechen Lhamo", "987654321098"))
        self.assertEqual(data["GB-CLIP-3"], ("Sonam Phuntsok", ""))

        # Now paste 2-column update for GB-CLIP-1 -> should update name but preserve Aadhaar
        paste_2col = "GB-CLIP-1\tTashi Wangdu Updated\n"
        with patch.object(self.app.root, "clipboard_get", return_value=paste_2col):
            self.app.import_from_clipboard()

        conn = sqlite3.connect(self.test_db_path)
        row = conn.execute(
            "SELECT name, aadhaar_number FROM gb_database WHERE gb_number='GB-CLIP-1'"
        ).fetchone()
        conn.close()
        self.assertEqual(row, ("Tashi Wangdu Updated", "123456789012"))

    @patch("Rangtsok_app.messagebox.askyesno", return_value=True)
    @patch("Rangtsok_app.messagebox.showinfo")
    def test_cleanse_gb_database_preserves_aadhaar(self, mock_info, mock_ask):
        """cleanse_gb_database merges duplicate GB records while preserving non-empty Aadhaar numbers."""
        conn = sqlite3.connect(self.test_db_path)
        conn.execute("INSERT INTO gb_database VALUES ('GB-100', 'Tenzin', '')")
        conn.execute("INSERT INTO gb_database VALUES ('gb 100', 'Tenzin Norbu', '556677889900')")
        conn.commit()
        conn.close()

        self.app.cleanse_gb_database()

        conn = sqlite3.connect(self.test_db_path)
        rows = conn.execute("SELECT gb_number, name, aadhaar_number FROM gb_database").fetchall()
        conn.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], ("gb100", "Tenzin Norbu", "556677889900"))

    def test_recent_entries_shows_latest_10_in_reverse_order(self):
        """Recent Entries displays at most 10 entries, newest first, with Receipt, GB, Name, and Total Amount."""
        conn = sqlite3.connect(self.test_db_path)
        for i in range(1, 16):
            conn.execute(
                """
                INSERT INTO transactions
                (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
                VALUES (?, ?, ?, 'India', 'Dharamshala', 'INR', '2026-05-10', '2026-05-10', '{}', ?)
                """,
                (f"1000{i:02d}", f"GB-{i:03d}", f"Member {i}", float(i * 100)),
            )
        conn.commit()
        conn.close()

        self.app.refresh_recent_entries()
        children = self.app.recent_tree.get_children()
        self.assertEqual(len(children), 10)

        first_vals = self.app.recent_tree.item(children[0], "values")
        last_vals = self.app.recent_tree.item(children[-1], "values")
        self.assertEqual(first_vals, ("100015", "GB-015", "Member 15", "1,500.00 INR"))
        self.assertEqual(last_vals, ("100006", "GB-006", "Member 6", "600.00 INR"))

    def test_recent_entries_double_click_loads_entry_for_edit(self):
        """Double-clicking a row in Recent Entries loads the record + Aadhaar into the Entry Form."""
        conn = sqlite3.connect(self.test_db_path)
        conn.execute(
            "INSERT INTO gb_database (gb_number, name, aadhaar_number) VALUES (?, ?, ?)",
            ("GB-EDIT-1", "Karma Rigzin", "778899001122"),
        )
        conn.execute(
            """
            INSERT INTO transactions
            (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
            VALUES ('500001', 'GB-EDIT-1', 'Karma Rigzin', 'India', 'Dharamshala', 'INR', '2026-05-10', '2026-05-10', '{"Chatrel": 300}', 300.0)
            """
        )
        conn.commit()
        conn.close()

        self.app.refresh_recent_entries()
        first_item = self.app.recent_tree.get_children()[0]
        self.app.recent_tree.selection_set(first_item)
        self.app.on_recent_double_click()

        self.assertIsNotNone(self.app.current_edit_id)
        self.assertEqual(self.app.ent_receipt.get(), "500001")
        self.assertEqual(self.app.ent_gb.get(), "GB-EDIT-1")
        self.assertEqual(self.app.ent_name.get(), "Karma Rigzin")
        self.assertEqual(self.app.ent_aadhaar.get(), "778899001122")

    @patch("Rangtsok_app.messagebox.showinfo")
    def test_gb_database_sort_and_search(self, mock_info):
        """GB Database supports Recently Added, Name A-Z/Z-A, GB Number natural sort, and live search."""
        paste_data = (
            "GB-100\tTenzin\t111122223333\n"
            "GB-9\tDolma\t444455556666\n"
            "GB-20\tKarma\t777788889999\n"
        )
        with patch.object(self.app.root, "clipboard_get", return_value=paste_data):
            self.app.import_from_clipboard()

        # Default: Recently Added (Newest First) -> Karma (last inserted) at top
        names_recent = [self.app.db_tree.item(i, "values")[1] for i in self.app.db_tree.get_children()]
        self.assertEqual(names_recent, ["Karma", "Dolma", "Tenzin"])

        # Name (A -> Z)
        self.app.cmb_db_sort.set("Name (A → Z)")
        self.app.refresh_db_table()
        names_az = [self.app.db_tree.item(i, "values")[1] for i in self.app.db_tree.get_children()]
        self.assertEqual(names_az, ["Dolma", "Karma", "Tenzin"])

        # GB Number (A -> Z) natural order: GB-9, GB-20, GB-100
        self.app.cmb_db_sort.set("GB Number (A → Z)")
        self.app.refresh_db_table()
        gbs_nat = [self.app.db_tree.item(i, "values")[0] for i in self.app.db_tree.get_children()]
        self.assertEqual(gbs_nat, ["GB-9", "GB-20", "GB-100"])

        # Live search by Aadhaar
        self.app.ent_db_search.insert(0, "444455")
        self.app.refresh_db_table()
        matched = [self.app.db_tree.item(i, "values")[1] for i in self.app.db_tree.get_children()]
        self.assertEqual(matched, ["Dolma"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
