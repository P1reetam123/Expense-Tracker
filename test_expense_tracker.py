"""Unit tests for integer-paise currency, SQLite CRUD, carryforward, allowances, and CSV."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import calculations as calc
import database as db
from models import (
    BudgetStatus,
    CarryforwardMode,
    ValidationError,
    format_inr,
    parse_rupees_to_paise,
)


class ExpenseTrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = Path(self.temp_dir.name) / "test_expenses.db"
        db.init_db(self.test_db)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_exact_paise_parsing_and_formatting(self) -> None:
        # 19.99 * 100 in float is 1998.9999999999998; Decimal must produce 1999.
        self.assertEqual(parse_rupees_to_paise("19.99"), 1999)
        self.assertEqual(parse_rupees_to_paise("₹1,23,456.78"), 12345678)
        self.assertEqual(format_inr(12345678), "₹1,23,456.78")
        self.assertEqual(format_inr(-50050), "-₹500.50")
        self.assertEqual(format_inr(25000, show_sign=True), "+₹250.00")

        for bad in ("", "0", "-10", "12.345", "abc", "nan", "inf"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    parse_rupees_to_paise(bad)

    def test_crud_discounts_and_custom_categories(self) -> None:
        exp_id = db.add_expense(
            40000,
            "Food & Canteen",
            "Dinner",
            "2026-11-10",
            discount_paise=10000,
            payment_mode="UPI",
            db_path=self.test_db,
        )
        fetched = db.get_expense_by_id(exp_id, self.test_db)
        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertEqual(fetched.amount_paise, 40000)
        self.assertEqual(fetched.discount_paise, 10000)
        self.assertEqual(fetched.payment_mode, "UPI")

        self.assertTrue(db.add_category("Gym & Fitness", self.test_db))
        self.assertFalse(db.add_category("gym & fitness", self.test_db))
        self.assertIn("Gym & Fitness", db.get_categories(self.test_db))

        db.update_expense(
            exp_id, 35000, "Gym & Fitness", "Membership", "2026-11-11", db_path=self.test_db
        )
        self.assertTrue(db.rename_category("Gym & Fitness", "Fitness Club", self.test_db))
        self.assertEqual(db.get_expense_by_id(exp_id, self.test_db).category, "Fitness Club")  # type: ignore[union-attr]
        db.delete_category("Fitness Club", self.test_db)
        self.assertEqual(db.get_expense_by_id(exp_id, self.test_db).category, "Other")  # type: ignore[union-attr]

    def test_carryforward_modes_and_adjustments(self) -> None:
        # Oct budget: 5000, spent: 4200 => +800 surplus
        # Nov budget: 5000 + 1000 allowance, spent: 7200 => deficit in Nov
        db.set_budget("2026-10", 500000, self.test_db)
        db.add_expense(420000, "Food & Canteen", "Oct food", "2026-10-05", db_path=self.test_db)

        db.set_budget("2026-11", 500000, self.test_db)
        db.add_adjustment("2026-11", 100000, "Stipend bonus", "2026-11-02", self.test_db)
        db.add_expense(720000, "Hostel & Rent", "Rent", "2026-11-05", db_path=self.test_db)

        db.set_budget("2026-12", 500000, self.test_db)

        expenses = db.get_all_expenses(db_path=self.test_db)
        budgets = db.get_all_budgets(self.test_db)
        adjustments = db.get_adjustments(db_path=self.test_db)

        # BOTH mode: Nov gets +800 => effective 6800, spent 7200 => Dec gets -400 => effective 4600
        nov_both = calc.compute_spending_summary(
            selected_month="2026-11",
            all_expenses=expenses,
            budgets_by_month=budgets,
            all_adjustments=adjustments,
            carryforward_mode=CarryforwardMode.BOTH,
        )
        self.assertEqual(nov_both.carryforward_in_paise, 80000)
        self.assertEqual(nov_both.effective_budget_paise, 680000)
        self.assertEqual(nov_both.budget_status, BudgetStatus.EXCEEDED)
        self.assertEqual(nov_both.exceeded_by_paise, 40000)

        dec_both = calc.compute_spending_summary(
            selected_month="2026-12",
            all_expenses=expenses,
            budgets_by_month=budgets,
            all_adjustments=adjustments,
            carryforward_mode=CarryforwardMode.BOTH,
        )
        self.assertEqual(dec_both.carryforward_in_paise, -40000)
        self.assertEqual(dec_both.effective_budget_paise, 460000)

        # DEFICIT_ONLY: Oct surplus is NOT carried to Nov, so Nov effective is 6000, Dec carry is -1200
        dec_def = calc.compute_spending_summary(
            selected_month="2026-12",
            all_expenses=expenses,
            budgets_by_month=budgets,
            all_adjustments=adjustments,
            carryforward_mode=CarryforwardMode.DEFICIT_ONLY,
        )
        self.assertEqual(dec_def.carryforward_in_paise, -120000)
        self.assertEqual(dec_def.effective_budget_paise, 380000)

        # ALL mode: Base = 15000, Adj = 1000 => Effective = 16000 (carryforwards cancel out)
        all_sum = calc.compute_spending_summary(
            selected_month="All",
            all_expenses=expenses,
            budgets_by_month=budgets,
            all_adjustments=adjustments,
            carryforward_mode=CarryforwardMode.BOTH,
        )
        self.assertEqual(all_sum.effective_budget_paise, 1600000)
        self.assertEqual(all_sum.total_spent_paise, 1140000)
        self.assertEqual(all_sum.budget_status, BudgetStatus.HEALTHY)
        
        db.add_expense(10000, "Other", "Unbudgeted month item", "2027-01-05", db_path=self.test_db)
        all_with_unbudgeted = calc.compute_spending_summary(
            selected_month="All",
            all_expenses=db.get_all_expenses(db_path=self.test_db),
            budgets_by_month=budgets,
            all_adjustments=adjustments,
            carryforward_mode=CarryforwardMode.BOTH,
        )
        self.assertEqual(all_with_unbudgeted.unbudgeted_months, ("2027-01",))
        self.assertIn("2027-01", all_with_unbudgeted.warning_message)

    def test_exact_ninety_percent_caution_threshold(self) -> None:
        db.set_budget("2026-11", 500000, self.test_db)
        db.add_expense(450000, "Food & Canteen", "90% exact", "2026-11-10", db_path=self.test_db)
        summary = calc.compute_spending_summary(
            selected_month="2026-11",
            all_expenses=db.get_all_expenses(db_path=self.test_db),
            budgets_by_month=db.get_all_budgets(self.test_db),
            all_adjustments=(),
            carryforward_mode=CarryforwardMode.OFF,
        )
        self.assertEqual(summary.budget_status, BudgetStatus.CAUTION)
        self.assertEqual(summary.percentage_used, 90.0)

    def test_csv_export_and_bulk_import_with_duplicates(self) -> None:
        db.add_expense(15000, "Food & Canteen", "Campus lunch", "2026-11-18", db_path=self.test_db)
        csv_path = Path(self.temp_dir.name) / "bulk.csv"
        csv_path.write_text(
            "date,category,payment_mode,description,amount,discount\n"
            "2026-11-18,Food & Canteen,UPI,Campus lunch,150.00,0\n"
            "2026-11-19,Unknown Cat,Cash,Snacks,80.50,10.00\n"
            "bad-date,Other,UPI,Broken,100,0\n",
            encoding="utf-8",
        )

        preview = calc.build_import_preview(
            csv_path,
            db.get_categories(self.test_db),
            db.get_existing_expense_counts(self.test_db),
        )
        self.assertEqual(len(preview.duplicate_rows), 1)
        self.assertEqual(len(preview.new_valid_rows), 1)
        self.assertEqual(len(preview.error_rows), 1)
        self.assertEqual(preview.new_valid_rows[0].category, "Other")
        self.assertEqual(preview.new_valid_rows[0].amount_paise, 8050)
        self.assertEqual(preview.new_valid_rows[0].discount_paise, 1000)

        inserted = db.add_expenses_batch(
            [
                (r.amount_paise, r.discount_paise, r.category, r.payment_mode, r.description, r.date)
                for r in preview.new_valid_rows
            ],
            self.test_db,
        )
        self.assertEqual(inserted, 1)

        out_csv = Path(self.temp_dir.name) / "exported.csv"
        exported_count = calc.export_expenses_to_csv(db.get_all_expenses(db_path=self.test_db), out_csv)
        self.assertEqual(exported_count, 2)
        self.assertTrue(out_csv.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)