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


class TestAdversarialAccountHeadDeletion(unittest.TestCase):
    """Adversarial stress-testing of database integrity and edge cases during Account Head Deletion."""

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
        target_iid = None
        for item in self.app.tree_heads.get_children():
            if self.app.tree_heads.item(item, "values")[1] == head_name:
                target_iid = item
                break
        self.assertIsNotNone(target_iid, f"Head '{head_name}' should exist in treeview")
        self.app.tree_heads.selection_set(target_iid)
        return target_iid

    def test_orphan_purge_preserves_valid_json_and_total_amount_under_stress(self):
        """Stress Test 1: Purging orphan keys across 200 transactions preserves JSON validity,
        row count, and exact total_amount for all rows."""
        head_name = "PurgeMeStress"
        # Add head to app
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "0.0")
        self.app.add_account_head()

        # Seed 200 diverse transactions
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        expected_records = {}

        for i in range(1, 201):
            receipt_no = f"REC-STRESS-{i:04d}"
            chatrel_val = 100.0 + (i * 5.0)
            meal_val = 20.0 if i % 2 == 0 else 0.0
            # Some transactions have target head as 0.0, some as int 0, some omitted
            if i % 3 == 0:
                acc_data = {"Chatrel": chatrel_val, "Meal Strike": meal_val, head_name: 0.0}
            elif i % 3 == 1:
                acc_data = {"Chatrel": chatrel_val, "Meal Strike": meal_val, head_name: 0}
            else:
                acc_data = {"Chatrel": chatrel_val, "Meal Strike": meal_val}

            total = chatrel_val + meal_val
            cursor.execute(
                """
                INSERT INTO transactions 
                (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (receipt_no, f"GB{i:05d}", f"Person {i}", "India", "Dharamshala", "INR",
                 "2026-05-01", "2026-05-01", json.dumps(acc_data), total)
            )
            expected_records[receipt_no] = {
                "expected_total": total,
                "expected_chatrel": chatrel_val,
                "expected_meal": meal_val
            }
        conn.commit()
        conn.close()

        # Select and delete the head
        self._select_head_in_tree(head_name)
        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):
            self.app.delete_account_head()

        # Empirical database verification
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT receipt_no, account_data, total_amount FROM transactions")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 200, "All 200 transactions must remain intact in the database")

        for r_no, acc_str, tot in rows:
            exp = expected_records[r_no]
            # total_amount MUST be completely untouched
            self.assertEqual(tot, exp["expected_total"], f"total_amount corrupted on receipt {r_no}")

            # account_data MUST be valid JSON
            try:
                acc_dict = json.loads(acc_str)
            except Exception as e:
                self.fail(f"account_data on receipt {r_no} corrupted into invalid JSON: {acc_str} ({e})")

            # target head MUST be purged
            self.assertNotIn(head_name, acc_dict, f"Target head '{head_name}' was not purged from {r_no}")

            # other heads MUST be preserved exactly
            self.assertEqual(acc_dict.get("Chatrel"), exp["expected_chatrel"], f"Chatrel corrupted on {r_no}")
            self.assertEqual(acc_dict.get("Meal Strike"), exp["expected_meal"], f"Meal Strike corrupted on {r_no}")

    def test_account_data_with_malformed_json_and_nulls_handled_gracefully(self):
        """Stress Test 2: Deleting an account head when the database contains malformed JSON,
        SQL NULLs, JSON nulls, and non-dict JSON handles gracefully without crashing or corrupting."""
        head_name = "RobustHead"
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "0.0")
        self.app.add_account_head()

        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()

        # 1. Normal row with 0.0
        cursor.execute(
            "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("REC-NORM", "GB001", "Normal", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", json.dumps({"Chatrel": 100.0, head_name: 0.0}), 100.0)
        )
        # 2. Row with unexpected JSON null for target head: {"RobustHead": null, "Chatrel": 200.0}
        cursor.execute(
            "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("REC-NULLVAL", "GB002", "NullVal", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", json.dumps({"Chatrel": 200.0, head_name: None}), 200.0)
        )
        # 3. Row with SQL NULL in account_data (bypass NOT NULL via ALTER/raw insert if possible, or dummy string)
        # In SQLite, if column is NOT NULL, insert None raises IntegrityError unless column allows NULL. Let's test if schema allows NULL or insert empty string
        try:
            cursor.execute(
                "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("REC-SQLNULL", "GB003", "SqlNull", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", None, 0.0)
            )
        except sqlite3.IntegrityError:
            # Table has NOT NULL constraint; test empty string instead
            cursor.execute(
                "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("REC-SQLNULL", "GB003", "SqlNull", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", "", 0.0)
            )
        # 4. Row with malformed corrupted JSON text: "{not valid json at all!"
        cursor.execute(
            "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("REC-MALFORMED", "GB004", "Malformed", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", "{not valid json at all!", 50.0)
        )
        # 5. Row with JSON array string: "[1, 2, 3]"
        cursor.execute(
            "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("REC-ARRAY", "GB005", "Array", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", "[1, 2, 3]", 0.0)
        )
        # 6. Row with literal "null" JSON string
        cursor.execute(
            "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("REC-LITNULL", "GB006", "LitNull", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", "null", 0.0)
        )
        conn.commit()
        conn.close()

        # Delete head
        self._select_head_in_tree(head_name)
        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"):
            # This MUST NOT crash
            try:
                self.app.delete_account_head()
            except Exception as e:
                self.fail(f"delete_account_head crashed when encountering malformed JSON/nulls: {e}")

        # Check DB state
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT receipt_no, account_data, total_amount FROM transactions")
        rows = dict((r[0], (r[1], r[2])) for r in cursor.fetchall())
        conn.close()

        self.assertEqual(len(rows), 6, "All 6 transactions must remain intact")

        # 1. Normal row: purged, total intact
        norm_data, norm_tot = rows["REC-NORM"]
        self.assertEqual(norm_tot, 100.0)
        self.assertNotIn(head_name, json.loads(norm_data))
        self.assertEqual(json.loads(norm_data).get("Chatrel"), 100.0)

        # 2. JSON null value row: purged, valid JSON, total intact
        nullval_data, nullval_tot = rows["REC-NULLVAL"]
        self.assertEqual(nullval_tot, 200.0)
        self.assertNotIn(head_name, json.loads(nullval_data))
        self.assertEqual(json.loads(nullval_data).get("Chatrel"), 200.0)

        # 3. Empty/NULL row: untouched
        sqlnull_data, sqlnull_tot = rows["REC-SQLNULL"]
        self.assertIn(sqlnull_data, ("", None))
        self.assertEqual(sqlnull_tot, 0.0)

        # 4. Malformed row: untouched, not crashed
        mal_data, mal_tot = rows["REC-MALFORMED"]
        self.assertEqual(mal_data, "{not valid json at all!")
        self.assertEqual(mal_tot, 50.0)

        # 5. Array row: untouched
        arr_data, arr_tot = rows["REC-ARRAY"]
        self.assertEqual(arr_data, "[1, 2, 3]")

        # 6. Literal "null" row: untouched
        lit_data, lit_tot = rows["REC-LITNULL"]
        self.assertEqual(lit_data, "null")

    def test_mixed_zero_and_empty_values_treated_as_inactive(self):
        """Stress Test 3: Multiple transactions exist, some with 0.0, some with 0, some with '',
        some with whitespace '   '. All must be recognized as inactive and purged cleanly."""
        head_name = "ZeroMixedHead"
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "0.0")
        self.app.add_account_head()

        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        test_cases = [
            ("REC-Z1", 0.0, 100.0),
            ("REC-Z2", 0, 200.0),
            ("REC-Z3", "", 300.0),
            ("REC-Z4", "   ", 400.0),
        ]
        for r_no, val, tot in test_cases:
            acc_data = {"Chatrel": tot, head_name: val}
            cursor.execute(
                """
                INSERT INTO transactions 
                (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (r_no, f"GB_{r_no}", "Name", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", json.dumps(acc_data), tot)
            )
        conn.commit()
        conn.close()

        self._select_head_in_tree(head_name)
        with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
             patch.object(Rangtsok_app.messagebox, "showinfo"), \
             patch.object(Rangtsok_app.messagebox, "showerror") as mock_err:
            self.app.delete_account_head()
            mock_err.assert_not_called()

        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT receipt_no, account_data, total_amount FROM transactions")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 4)
        for r_no, acc_str, tot in rows:
            acc_dict = json.loads(acc_str)
            self.assertNotIn(head_name, acc_dict, f"Head '{head_name}' should have been purged from {r_no}")
            self.assertEqual(acc_dict.get("Chatrel"), tot)

    def test_active_contributions_never_corrupted_or_deleted(self):
        """Stress Test 4: Transactions with active contributions (> 0 or non-empty date)
        are NEVER deleted, modified, or corrupted when deletion is attempted."""
        head_name = "ActiveCriticalHead"
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "100.0")
        self.app.add_account_head()

        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        # Row 1: Active amount
        acc1 = {"Chatrel": 200.0, head_name: 75.50}
        cursor.execute(
            "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("REC-ACT1", "GB001", "User1", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", json.dumps(acc1), 275.50)
        )
        # Row 2: Inactive 0.0
        acc2 = {"Chatrel": 150.0, head_name: 0.0}
        cursor.execute(
            "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("REC-ACT2", "GB002", "User2", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", json.dumps(acc2), 150.0)
        )
        conn.commit()
        conn.close()

        self._select_head_in_tree(head_name)
        with patch.object(Rangtsok_app.messagebox, "showerror") as mock_err, \
             patch.object(Rangtsok_app.messagebox, "askyesno") as mock_ask:
            self.app.delete_account_head()
            mock_err.assert_called_once()
            mock_ask.assert_not_called()

        # Re-check database byte-for-byte
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT receipt_no, account_data, total_amount FROM transactions ORDER BY receipt_no")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 2)
        # Row 1 MUST still contain ActiveCriticalHead: 75.50
        r1_acc = json.loads(rows[0][1])
        self.assertEqual(r1_acc.get(head_name), 75.50)
        self.assertEqual(rows[0][2], 275.50)

        # Row 2 MUST NOT have been purged prematurely either because deletion was blocked!
        r2_acc = json.loads(rows[1][1])
        self.assertEqual(r2_acc.get(head_name), 0.0, "Inactive row must NOT be purged when deletion was blocked")

        # Head MUST still exist in settings and UI
        configured_heads = [h["head"] for h in self.app.settings.get("account_heads", [])]
        self.assertIn(head_name, configured_heads)

    def test_negative_amount_edge_case(self):
        """Stress Test 5: Verify behavior when an account head has a negative value (e.g. refund/adjustment -50.0)."""
        head_name = "RefundHead"
        self.app.ent_new_head.delete(0, tk.END)
        self.app.ent_new_head.insert(0, head_name)
        self.app.cmb_new_type.set("Amount")
        self.app.on_head_type_change()
        self.app.ent_new_def.delete(0, tk.END)
        self.app.ent_new_def.insert(0, "0.0")
        self.app.add_account_head()

        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        acc = {"Chatrel": 200.0, head_name: -50.0}
        cursor.execute(
            "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("REC-NEG", "GB001", "UserNeg", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", json.dumps(acc), 150.0)
        )
        conn.commit()
        conn.close()

        self._select_head_in_tree(head_name)
        # We record whether the current implementation blocks or allows deletion of a negative amount
        blocked = False
        with patch.object(Rangtsok_app.messagebox, "showerror") as mock_err, \
             patch.object(Rangtsok_app.messagebox, "askyesno", return_value=False):
            self.app.delete_account_head()
            if mock_err.called:
                blocked = True

        # Let's inspect the finding:
        # If blocked is False, it means `val > 0` allowed negative numbers to be treated as inactive!
        # We log this empirically in the test
        print(f"\n[EMPIRICAL FINDING] Negative amount (-50.0) blocked by delete_account_head: {blocked}")

    def test_special_tibetan_and_injection_characters(self):
        """Stress Test 6: Tibetan unicode characters and quotes/SQL characters in head names."""
        special_heads = [
            "དམིགས་བསལ་ཞལ་འདེབས།",  # Tibetan Special Donation
            'Special "Quotes" & \\Backslash',
            "Taxes'); DROP TABLE transactions; --"
        ]

        for s_head in special_heads:
            self.app.ent_new_head.delete(0, tk.END)
            self.app.ent_new_head.insert(0, s_head)
            self.app.cmb_new_type.set("Amount")
            self.app.on_head_type_change()
            self.app.ent_new_def.delete(0, tk.END)
            self.app.ent_new_def.insert(0, "0.0")
            self.app.add_account_head()

            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            acc = {"Chatrel": 100.0, s_head: 0.0}
            cursor.execute(
                "INSERT INTO transactions (receipt_no, gb_number, name, country, place, currency, tx_date, entry_date, account_data, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"REC-SPEC-{hash(s_head)}", "GB999", "SpecialUser", "India", "Delhi", "INR", "2026-05-01", "2026-05-01", json.dumps(acc), 100.0)
            )
            conn.commit()
            conn.close()

            self._select_head_in_tree(s_head)
            with patch.object(Rangtsok_app.messagebox, "askyesno", return_value=True), \
                 patch.object(Rangtsok_app.messagebox, "showinfo"):
                self.app.delete_account_head()

            # Verify table still exists and key is purged
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT account_data, total_amount FROM transactions WHERE receipt_no=?", (f"REC-SPEC-{hash(s_head)}",))
            row = cursor.fetchone()
            conn.close()

            self.assertIsNotNone(row, "Transaction must exist (transactions table was not dropped)")
            acc_data = json.loads(row[0])
            self.assertNotIn(s_head, acc_data, f"Key '{s_head}' must be purged")
            self.assertEqual(row[1], 100.0, "total_amount must remain untouched")


if __name__ == "__main__":
    unittest.main()
