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

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import Rangtsok_app


class TestMilestone1Adversarial(unittest.TestCase):
    """Adversarial challenge test suite for Milestone 1 Account Head Deletion.
    
    Stress tests boundary conditions, rapid concurrency-like addition/deletion,
    special characters, unicode, quotes, braces, spaces, numeric prefixes,
    transaction edge cases (empty, zero, null, negative, corrupted JSON),
    and UI/database synchronization invariants.
    """

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

    def _select_head_in_tree(self, head_name):
        for item in self.app.tree_heads.get_children():
            values = self.app.tree_heads.item(item, "values")
            if str(values[1]) == str(head_name):
                self.app.tree_heads.selection_set(item)
                return item
        return None

    # =========================================================================
    # SUITE 1: RAPID BURST ADDITION AND DELETION
    # =========================================================================

    def test_rapid_burst_addition_and_reverse_deletion(self):
        """Stress: Rapidly add 30 diverse account heads, verify 100% UI/settings parity,
        then delete them all in reverse order verifying zero state drift."""
        initial_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        initial_count = len(initial_heads)

        burst_heads = [f"Burst Head #{i:03d}" for i in range(1, 31)]

        # Rapid addition
        for i, h_name in enumerate(burst_heads):
            h_type = "Amount" if i % 2 == 0 else "Date"
            h_def = str(i * 10) if h_type == "Amount" else "01-01-2026"
            self.app.ent_new_head.delete(0, tk.END)
            self.app.ent_new_head.insert(0, h_name)
            self.app.cmb_new_type.set(h_type)
            self.app.on_head_type_change()
            self.app.ent_new_def.delete(0, tk.END)
            self.app.ent_new_def.insert(0, h_def)
            self.app.add_account_head()

        # Check state after burst addition
        curr_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        self.assertEqual(len(curr_heads), initial_count + 30)
        self.assertEqual(len(self.app.tree_heads.get_children()), initial_count + 30)
        self.assertEqual(len(self.app.head_entries), initial_count + 30)
        self.assertEqual(len(self.app.flt_head["values"]), initial_count + 30 + 1)

        # Rapid reverse deletion
        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):
            for h_name in reversed(burst_heads):
                target_iid = self._select_head_in_tree(h_name)
                self.assertIsNotNone(target_iid, f"Head '{h_name}' must be selectable in treeview")
                self.app.delete_account_head()

                # Verify immediate removal across all 4 surfaces after each deletion
                s_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
                self.assertNotIn(h_name, s_heads)
                self.assertNotIn(h_name, self.app.head_entries)
                self.assertNotIn(h_name, list(self.app.flt_head["values"]))

        # Final verification: exactly back to initial count
        final_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        self.assertEqual(len(final_heads), initial_count)
        self.assertEqual(len(self.app.tree_heads.get_children()), initial_count)
        self.assertEqual(len(self.app.head_entries), initial_count)

    # =========================================================================
    # SUITE 2: SPECIAL CHARACTERS, QUOTES, UNICODE, EMOJIS, NUMERICS
    # =========================================================================

    def test_special_characters_quotes_and_unicode_lifecycle(self):
        """Stress: Add and delete account heads with single quotes, double quotes,
        Tibetan script, emojis, brackets, math operators, SQL injection strings, and numeric prefixes."""
        adversarial_names = [
            "Donation's Fund",
            'Relief "A" Emergency',
            "དྭང་བླངས་དམག་དེབ།",
            "བོད་ཀྱི་དུས་ཆེན། 2026",
            "💰 Gold Reserve 🎗️",
            "[COVID-19] (Relief) {Special}",
            "12345678",
            "2026 Emergency Fund",
            "Fund+Plus -Minus *Star =Equal /Slash %Percent",
            "SQL' OR '1'='1; --",
            "Head With   Multiple   Spaces",
            "Special!@#$^&_Char"
        ]

        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):
            for adv_name in adversarial_names:
                # 1. Add head
                self.app.ent_new_head.delete(0, tk.END)
                self.app.ent_new_head.insert(0, adv_name)
                self.app.cmb_new_type.set("Amount")
                self.app.on_head_type_change()
                self.app.ent_new_def.delete(0, tk.END)
                self.app.ent_new_def.insert(0, "75")
                self.app.add_account_head()

                # Verify addition
                s_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
                self.assertIn(adv_name, s_heads, f"Failed to add '{adv_name}' to settings")
                self.assertIn(adv_name, self.app.head_entries, f"Failed to create widget for '{adv_name}'")
                self.assertIn(adv_name, list(self.app.flt_head["values"]))

                # 2. Select in treeview
                target_iid = self._select_head_in_tree(adv_name)
                self.assertIsNotNone(target_iid, f"Could not find '{adv_name}' in treeview")

                # 3. Delete head
                self.app.delete_account_head()

                # 4. Verify clean deletion
                s_heads_after = [h["head"] for h in self.app.settings.get("account_heads", [])]
                self.assertNotIn(adv_name, s_heads_after, f"Failed to delete '{adv_name}' from settings")
                self.assertNotIn(adv_name, self.app.head_entries)
                self.assertNotIn(adv_name, list(self.app.flt_head["values"]))

    # =========================================================================
    # SUITE 3: TRANSACTION MATRIX (EMPTY, ZERO, NULL, NEGATIVE, ACTIVE)
    # =========================================================================

    def test_transaction_matrix_edge_cases(self):
        """Stress: Test deletion behavior against various account_data payloads:
        - 0 (int) -> purge & delete
        - 0.0 (float) -> purge & delete
        - '' (empty string) -> purge & delete
        - '   ' (whitespace) -> purge & delete
        - None -> purge & delete
        - Active positive amount -> block
        - Active date string -> block
        """
        test_cases = [
            ("Head_IntZero", 0, True),
            ("Head_FloatZero", 0.0, True),
            ("Head_EmptyStr", "", True),
            ("Head_BlankStr", "   ", True),
            ("Head_NullVal", None, True),
            ("Head_ActiveLow", 0.01, False),
            ("Head_ActiveNormal", 500.0, False),
            ("Head_ActiveDate", "15-08-2026", False),
        ]

        for head_name, val, should_allow in test_cases:
            # Add the head
            h_type = "Date" if "Date" in head_name else "Amount"
            self.app.ent_new_head.delete(0, tk.END)
            self.app.ent_new_head.insert(0, head_name)
            self.app.cmb_new_type.set(h_type)
            self.app.on_head_type_change()
            self.app.add_account_head()

            # Insert transaction
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO transactions 
                (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"REC_{head_name}", "GB9999", "Matrix Person", "India", "Dharamshala", "INR", "2026-05-01", "2026-05-01",
                 json.dumps({"Chatrel": 100.0, head_name: val}), 100.0)
            )
            conn.commit()
            conn.close()

            # Select head
            target_iid = self._select_head_in_tree(head_name)
            self.assertIsNotNone(target_iid)

            if should_allow:
                with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
                     patch.object(Rangtsok_app.messagebox, "showinfo"):
                    self.app.delete_account_head()

                # Verify deleted from settings
                s_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
                self.assertNotIn(head_name, s_heads)

                # Verify orphan key purged from DB
                conn = sqlite3.connect(self.test_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT account_data FROM transactions WHERE receipt_no=?", (f"REC_{head_name}",))
                row = cursor.fetchone()
                conn.close()
                self.assertIsNotNone(row)
                acc_data = json.loads(row[0])
                self.assertNotIn(head_name, acc_data, f"Orphan key '{head_name}' should have been purged")
                self.assertEqual(acc_data.get("Chatrel"), 100.0)
            else:
                with patch.object(Rangtsok_app.messagebox, "showerror") as mock_err, \
                     patch.object(Rangtsok_app.messagebox, "askyesno") as mock_ask:
                    self.app.delete_account_head()
                    mock_err.assert_called_once()
                    mock_ask.assert_not_called()

                # Verify NOT deleted
                s_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
                self.assertIn(head_name, s_heads)

                # Clean up for next iterations
                conn = sqlite3.connect(self.test_db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transactions WHERE receipt_no=?", (f"REC_{head_name}",))
                conn.commit()
                conn.close()

                # Now delete without error
                with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
                     patch.object(Rangtsok_app.messagebox, "showinfo"):
                    self.app.delete_account_head()

    def test_corrupted_json_in_database_does_not_crash_deletion(self):
        """Stress: Corrupted non-JSON strings in transactions.account_data must be handled gracefully without crash."""
        head_name = "Graceful Head"
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.add_account_head()

        # Insert a malformed row in transactions
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions 
            (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("REC_CORRUPT", "GB0000", "Corrupt Data", "India", "Dharamshala", "INR", "2026-05-01", "2026-05-01",
             "NOT_VALID_JSON{{{", 0.0)
        )
        conn.commit()
        conn.close()

        # Select and delete
        target_iid = self._select_head_in_tree(head_name)
        self.assertIsNotNone(target_iid)

        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):
            # Should not raise exception
            try:
                self.app.delete_account_head()
            except Exception as e:
                self.fail(f"delete_account_head crashed on corrupted database row: {e}")

        # Head was deleted
        s_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        self.assertNotIn(head_name, s_heads)

    # =========================================================================
    # SUITE 4: RE-BIRTH & CASE SENSITIVITY
    # =========================================================================

    def test_rebirth_and_type_switch_lifecycle(self):
        """Stress: Add head as Amount -> delete -> re-add as Date with same name.
        Verify entry form reflects DateEntry without type conflicts."""
        head_name = "Dynamic Switch Head"

        # 1. Add as Amount
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "150")
        self.app.add_account_head()

        self.assertEqual(self.app.head_entries[head_name][2], "Amount")

        # 2. Delete
        target_iid = self._select_head_in_tree(head_name)
        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):
            self.app.delete_account_head()

        self.assertNotIn(head_name, self.app.head_entries)

        # 3. Re-add as Date
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Date")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "10-10-2026")
        self.app.add_account_head()

        self.assertIn(head_name, self.app.head_entries)
        self.assertEqual(self.app.head_entries[head_name][2], "Date")

    # =========================================================================
    # SUITE 5: CANCEL CONFIRMATION PRESERVES STATE
    # =========================================================================

    def test_cancel_deletion_leaves_state_completely_unmodified(self):
        """Verify user clicking 'No' in confirmation dialog leaves settings, UI, and DB untouched."""
        head_name = "Preserved Head"
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "300")
        self.app.add_account_head()

        target_iid = self._select_head_in_tree(head_name)
        self.assertIsNotNone(target_iid)

        # Mock user clicks 'No'
        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=False) as mock_ask, \
             patch.object(Rangtsok_app.messagebox, "showinfo") as mock_info:
            self.app.delete_account_head()
            mock_ask.assert_called_once()
            mock_info.assert_not_called()

        # Check preserved everywhere
        s_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        self.assertIn(head_name, s_heads)
        self.assertIn(head_name, self.app.head_entries)
        self.assertIn(head_name, list(self.app.flt_head["values"]))
        tree_items = [self.app.tree_heads.item(i, "values")[1] for i in self.app.tree_heads.get_children()]
        self.assertIn(head_name, tree_items)


if __name__ == "__main__":
    unittest.main()
